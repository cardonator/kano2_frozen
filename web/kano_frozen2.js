class KanoFrozen2 {
    constructor() {
        this.device = null;
        this.server = null;
        this.charLeds = null;
        this.charBrightness = null;
        this.charSensor = null;
        this.isConnected = false;

        this.ledBuffer = new Array(9).fill([0, 0, 0]);
        this.listeners = {};

        // Constants
        this.SERVICE_UUID_IO = "11a70300-f691-4b93-a6f4-0968f5b648f8";
        this.CHAR_LEDS = "11a70301-f691-4b93-a6f4-0968f5b648f8";
        this.CHAR_BRIGHTNESS = "11a70304-f691-4b93-a6f4-0968f5b648f8";
        this.SERVICE_UUID_SENSOR = "11a70200-f691-4b93-a6f4-0968f5b648f8";
        this.CHAR_SENSOR = "11a70201-f691-4b93-a6f4-0968f5b648f8";

        // Gesture State
        this.lastHZone = null;
        this.lastHTime = 0;
        this.lastVZone = null;
        this.lastVTime = 0;
        this.SWIPE_TIMEOUT = 1000;
        this.ACT_THRESH = 30;
    }

    // --- EVENTS ---
    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }

    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }

    // --- CONNECTION ---
    async connect() {
        try {
            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ namePrefix: "Kano" }],
                optionalServices: [this.SERVICE_UUID_IO, this.SERVICE_UUID_SENSOR]
            });

            this.device.addEventListener('gattserverdisconnected', this.onDisconnect.bind(this));
            this.server = await this.device.gatt.connect();

            // Stability Delay
            await new Promise(resolve => setTimeout(resolve, 500));

            if (!this.server.connected) {
                throw new Error("GATT Server is disconnected. Cannot retrieve services.");
            }

            // IO Service
            const serviceIO = await this.server.getPrimaryService(this.SERVICE_UUID_IO);
            this.charLeds = await serviceIO.getCharacteristic(this.CHAR_LEDS);
            this.charBrightness = await serviceIO.getCharacteristic(this.CHAR_BRIGHTNESS);

            // Sensor Service
            const serviceSensor = await this.server.getPrimaryService(this.SERVICE_UUID_SENSOR);
            this.charSensor = await serviceSensor.getCharacteristic(this.CHAR_SENSOR);

            await this.charSensor.startNotifications();
            this.charSensor.addEventListener('characteristicvaluechanged', this.handleSensorData.bind(this));

            // Init HW Brightness
            await this.setBrightness(255);

            this.isConnected = true;
            this.emit('connect', this.device.name);

        } catch (error) {
            console.error(error);
            throw error; // Re-throw for UI to handle
        }
    }

    async disconnect() {
        if (this.device && this.device.gatt.connected) {
            await this.device.gatt.disconnect();
        }
    }

    onDisconnect() {
        this.isConnected = false;
        this.charLeds = null;
        this.charBrightness = null;
        this.charSensor = null;
        this.emit('disconnect');
    }

    // --- SENSOR & GESTURE ---
    handleSensorData(event) {
        const val = new Uint8Array(event.target.value.buffer);
        // val = [North, East, South, West] (0=Close, 255=Far)

        // Convert to Brightness (0-255)
        const b = [0, 0, 0, 0]; // N, E, S, W
        let maxB = 0;
        let activeZone = null;

        for (let i = 0; i < 4; i++) {
            if (val[i] < 220) {
                b[i] = 255 - val[i];
                if (b[i] < 0) b[i] = 0;
            }
            if (b[i] > maxB) {
                maxB = b[i];
                if (maxB > this.ACT_THRESH) activeZone = i;
            }
        }

        this.emit('sensor', { raw: val, brightness: b, maxBrightness: maxB });
        this.detectGesture(activeZone);
    }

    detectGesture(currentZone) {
        if (currentZone === null) return;

        const now = Date.now();
        let direction = null;
        const Z_NORTH = 0, Z_EAST = 1, Z_SOUTH = 2, Z_WEST = 3;

        // Horizontal
        if (currentZone === Z_EAST || currentZone === Z_WEST) {
            if (this.lastHZone !== null && this.lastHZone !== currentZone) {
                if ((now - this.lastHTime) < this.SWIPE_TIMEOUT) {
                    direction = (currentZone === Z_WEST) ? "LEFT" : "RIGHT";
                    this.lastHZone = null;
                }
            }
            if (!direction) { this.lastHZone = currentZone; this.lastHTime = now; }
        }

        // Vertical
        if (currentZone === Z_NORTH || currentZone === Z_SOUTH) {
            if (this.lastVZone !== null && this.lastVZone !== currentZone) {
                if ((now - this.lastVTime) < this.SWIPE_TIMEOUT) {
                    direction = (currentZone === Z_NORTH) ? "UP" : "DOWN";
                    this.lastVZone = null;
                }
            }
            if (!direction) { this.lastVZone = currentZone; this.lastVTime = now; }
        }

        if (direction) {
            this.emit('gesture', direction);
        }
    }

    // --- LED CONTROL ---
    async setBrightness(level) {
        if (!this.charBrightness || !this.isConnected) return;
        try {
            await this.charBrightness.writeValue(new Uint8Array([level]));
        } catch (e) {
            console.error("Brightness Error:", e);
        }
    }

    setLed(index, r, g, b) {
        if (index >= 0 && index < 9) {
            this.ledBuffer[index] = [r, g, b];
        }
    }

    setAllLeds(r, g, b) {
        this.ledBuffer.fill([r, g, b]);
    }

    clearLeds() {
        this.setAllLeds(0, 0, 0);
    }

    getLed(index) {
        return this.ledBuffer[index];
    }

    async sendLeds() {
        if (!this.charLeds || !this.isConnected) return;

        const payload = new Uint8Array(19);
        payload[0] = 0x01;

        let idx = 1;
        for (let i = 0; i < 9; i++) {
            const [r, g, b] = this.ledBuffer[i];
            const r5 = (r >> 3) & 0x1F;
            const g6 = (g >> 2) & 0x3F;
            const b5 = (b >> 3) & 0x1F;
            const packed = (r5 << 11) | (g6 << 5) | b5;

            payload[idx++] = (packed >> 8) & 0xFF;
            payload[idx++] = packed & 0xFF;
        }

        try {
            await this.charLeds.writeValue(payload);
        } catch (e) {
            // Ignore dropped packets
        }
    }
}
