import asyncio
import time
import struct
from bleak import BleakScanner, BleakClient

# ==============================================================================
# KANO FROZEN 2 CONSTANTS
# ==============================================================================
DEVICE_FILTER = "Kano"

# UUIDs
UUID_LEDS           = "11a70301-f691-4b93-a6f4-0968f5b648f8"
UUID_KEEP_ALIVE     = "11a70302-f691-4b93-a6f4-0968f5b648f8"
UUID_BATTERY        = "11a70303-f691-4b93-a6f4-0968f5b648f8"
UUID_BRIGHTNESS     = "11a70304-f691-4b93-a6f4-0968f5b648f8"
UUID_SENSOR_DATA    = "11a70201-f691-4b93-a6f4-0968f5b648f8"

# LED Indices
LED_CENTER = 8
LEDS_NORTH = [7, 0]
LEDS_EAST  = [1, 2]
LEDS_SOUTH = [3, 4]
LEDS_WEST  = [5, 6]

# Sensor Indices
SENSOR_NORTH = 0
SENSOR_EAST  = 1
SENSOR_SOUTH = 2
SENSOR_WEST  = 3

class KanoFrozen2:
    def __init__(self):
        self.client = None
        self.led_buffer = [(0, 0, 0)] * 9
        self._led_dirty = False
        self._callbacks_gesture = []
        self._callbacks_sensor = []
        
        # Gesture State
        self._last_h_zone = None
        self._last_h_time = 0
        self._last_v_zone = None
        self._last_v_time = 0
        
        # Config
        self.swipe_timeout = 1.0
        self.activation_threshold = 30

    async def connect(self):
        """Scans for and connects to the Kano Frozen 2 Sensor."""
        print("Scanning for Kano Frozen 2 Sensor...")
        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: d.name and DEVICE_FILTER in d.name
        )
        if not device:
            raise Exception("Device not found. Is it turned on?")

        print(f"Connecting to {device.name}...")
        self.client = BleakClient(device)
        await self.client.connect()
        
        # Windows BLE stack stabilization delay
        await asyncio.sleep(2.0)

        await self.client.start_notify(UUID_SENSOR_DATA, self._handle_sensor_data)
        
        # Initialize
        await self.set_brightness(255)
        print("Connected!")

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    def on_gesture(self, callback):
        """Register a function to be called on swipe detection: callback(direction_string)"""
        self._callbacks_gesture.append(callback)

    def on_sensor_data(self, callback):
        """Register a function to be called on raw data: callback(north, east, south, west)"""
        self._callbacks_sensor.append(callback)

    async def set_brightness(self, level):
        """Sets global hardware brightness (0-255)."""
        if not self.client: return
        try:
            await self.client.write_gatt_char(UUID_BRIGHTNESS, bytearray([level]))
        except Exception as e:
            print(f"Brightness Error: {e}")

    def set_led(self, index, r, g, b):
        """Sets a specific LED index (0-8) in the buffer."""
        if 0 <= index < 9:
            self.led_buffer[index] = (r, g, b)
            self._led_dirty = True

    def set_all(self, r, g, b):
        """Sets all LEDs to a color."""
        self.led_buffer = [(r, g, b)] * 9
        self._led_dirty = True

    def clear_leds(self):
        self.set_all(0, 0, 0)

    def get_led(self, index):
        """Returns the (r, g, b) tuple for the given index."""
        if 0 <= index < 9:
            return self.led_buffer[index]
        return (0, 0, 0)

    async def update_leds(self):
        """Flushes the LED buffer to the device if changed."""
        if not self._led_dirty or not self.client: return
        
        payload = bytearray([0x01])
        for r, g, b in self.led_buffer:
            # RGB565 Conversion
            r5 = (r >> 3) & 0x1F
            g6 = (g >> 2) & 0x3F
            b5 = (b >> 3) & 0x1F
            packed = (r5 << 11) | (g6 << 5) | b5
            payload.extend([(packed >> 8) & 0xFF, packed & 0xFF])
            
        try:
            await self.client.write_gatt_char(UUID_LEDS, payload)
            self._led_dirty = False
        except Exception as e:
            print(f"LED Write Error: {e}")

    def _detect_gesture(self, current_zone):
        now = time.time()
        direction = None

        if current_zone is None: return

        # Horizontal Logic (East/West)
        if current_zone in [SENSOR_EAST, SENSOR_WEST]:
            if self._last_h_zone is not None and self._last_h_zone != current_zone:
                if (now - self._last_h_time) < self.swipe_timeout:
                    direction = "LEFT" if current_zone == SENSOR_WEST else "RIGHT"
                    self._last_h_zone = None # Reset
            
            if not direction:
                self._last_h_zone = current_zone
                self._last_h_time = now

        # Vertical Logic (North/South)
        if current_zone in [SENSOR_NORTH, SENSOR_SOUTH]:
            if self._last_v_zone is not None and self._last_v_zone != current_zone:
                if (now - self._last_v_time) < self.swipe_timeout:
                    direction = "UP" if current_zone == SENSOR_NORTH else "DOWN"
                    self._last_v_zone = None

            if not direction:
                self._last_v_zone = current_zone
                self._last_v_time = now

        if direction:
            for cb in self._callbacks_gesture:
                cb(direction)

    def _handle_sensor_data(self, sender, data):
        raw = list(data)
        
        # 1. Convert Raw to Brightness (0-255)
        # 255 (Far) -> 0 (Close) conversion for easier logic
        b_vals = []
        max_b = 0
        active_zone = None

        for i, val in enumerate(raw):
            b = 0 if val > 220 else (255 - val)
            if b < 0: b = 0
            b_vals.append(b)
            
            if b > max_b:
                max_b = b
                if b > self.activation_threshold:
                    active_zone = i

        # Trigger Sensor Callbacks
        for cb in self._callbacks_sensor:
            cb(b_vals)

        # Trigger Gesture Logic
        self._detect_gesture(active_zone)


# ==============================================================================
# EXAMPLE USAGE (Run this file directly)
# ==============================================================================
async def main():
    kano = KanoFrozen2()
    
    # Callback: Print Gestures
    def on_swipe(direction):
        print(f" >>> SWIPE DETECTED: {direction} <<<")
        # Visual feedback
        asyncio.create_task(flash_center())

    # Callback: Force Field Visualization
    def on_sensor(vals):
        n, e, s, w = vals
        center = max(vals)
        
        # Clear
        kano.led_buffer = [(0,0,0)] * 9
        
        # Map Directions
        for i in LEDS_NORTH: kano.set_led(i, n, 0, 0)
        for i in LEDS_EAST:  kano.set_led(i, 0, e, 0)
        for i in LEDS_SOUTH: kano.set_led(i, 0, 0, s)
        for i in LEDS_WEST:  kano.set_led(i, w, w, 0)
        kano.set_led(LED_CENTER, center, center, center)

    async def flash_center():
        kano.set_led(LED_CENTER, 255, 255, 255)
        await kano.update_leds()
        await asyncio.sleep(0.2)
        
    kano.on_gesture(on_swipe)
    kano.on_sensor_data(on_sensor)

    try:
        await kano.connect()
        print("Library Demo Running. Press Ctrl+C to stop.")
        while True:
            await kano.update_leds()
            await asyncio.sleep(0.05)
    except Exception as e:
        print(e)
    finally:
        await kano.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass