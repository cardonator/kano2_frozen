# Kano Frozen 2 Web Library

A JavaScript library to control the Kano Frozen 2 Motion Sensor Kit via Web Bluetooth.

## Installation

### NPM
```bash
npm install kano-frozen2-web
```

### Script Tag
Simply include `kano_frozen2.js` in your HTML file:
```html
<script src="kano_frozen2.js"></script>
```

## Usage

**Note:** Web Bluetooth requires the page to be served over **HTTPS** (or `localhost`).

```html
<script src="kano_frozen2.js"></script>
<script>
  const kano = new KanoFrozen2();

  // Connection must be triggered by a user gesture (e.g., button click)
  document.getElementById('connect').addEventListener('click', async () => {
      try {
          await kano.connect();
          console.log("Connected!");
      } catch (e) {
          console.error(e);
      }
  });

  // Listen for swiping gestures
  kano.on('gesture', (direction) => {
    // direction: 'UP', 'DOWN', 'LEFT', 'RIGHT'
    console.log("Swipe:", direction);
  });

  // Listen for raw sensor data
  kano.on('sensor', (data) => {
    // data.brightness: Array(4) [North, East, South, West] (0-255)
    // data.maxBrightness: The highest value among the 4 sensors
  });
</script>
```

## API

### `connect()`
Request the device via the browser picker and establish a connection. Must be called from a user gesture.

### `disconnect()`
Disconnect from the device.

### `setLed(index, r, g, b)`
Set the color of a specific LED (0-8).
*   **0, 7**: North
*   **1, 2**: East
*   **3, 4**: South
*   **5, 6**: West
*   **8**: Center

### `setAllLeds(r, g, b)`
Set all 9 LEDs to the same color.

### `clearLeds()`
Turn off all LEDs.

### `sendLeds()`
Send the current LED buffer to the device. You should call this after setting one or more LEDs to apply changes.
*Limited to ~40 updates per second for stability.*

### `setBrightness(level)`
Set the global hardware brightness limit (0-255).

### `on(event, callback)`
Subscribe to events.
*   `'connect'`: Device connected.
*   `'disconnect'`: Device disconnected.
*   `'sensor'`: New sensor data available.
*   `'gesture'`: Swipe gesture detected.
