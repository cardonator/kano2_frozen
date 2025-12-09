# Kano Frozen 2 Python Library

A Python library to control the Kano Frozen 2 Motion Sensor Kit using [Bleak](https://github.com/hbldh/bleak).

## Installation

You can install this library via pip:

```bash
pip install .
```

Or install the dependencies manually:

```bash
pip install bleak
```

## Usage

```python
import asyncio
from kano_frozen2 import KanoFrozen2

async def main():
    kano = KanoFrozen2()
    
    # Define a callback for gestures
    def on_swipe(direction):
        print(f"Swipe: {direction}")
        
    # Register callback
    kano.on_gesture(on_swipe)

    print("Searching for device...")
    await kano.connect()
    print("Connected!")
    
    # Set LEDs to Blue
    kano.set_all(0, 0, 255)
    await kano.update_leds()
    
    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await kano.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## API

### `connect()`
Scans for a device named "Kano-..." and connects to it.

### `disconnect()`
Disconnects from the device.

### `set_led(index, r, g, b)`
Set a specific LED index (0-8) in the internal buffer.
*   **Indices**: North(0, 7), East(1, 2), South(3, 4), West(5, 6), Center(8).

### `set_all(r, g, b)`
Set all LEDs in the buffer to the same color.

### `clear_leds()`
Set all LEDs in the buffer to (0,0,0).

### `get_led(index)`
Returns the current `(r, g, b)` tuple for the specified index.

### `update_leds()`
Sends the current buffer state to the device via Bluetooth.

### `set_brightness(level)`
Sets the global hardware brightness (0-255).

### `on_gesture(callback)`
Register a callback function for swipe gestures.
*   `callback(direction)` where direction is "UP", "DOWN", "LEFT", "RIGHT".

### `on_sensor_data(callback)`
Register a callback for raw sensor data.
*   `callback(values)` where values is `[North, East, South, West]`.
