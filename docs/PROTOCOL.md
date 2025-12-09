# Kano Frozen 2 BLE Protocol

This document details the Bluetooth Low Energy (BLE) protocol used by the Kano Frozen 2 Coding Kit (Motion Sensor).

## Connection Details

- **Device Name Prefix**: `Kano-`
- **Advertisement**: The device advertises its services and can be discovered by name or Service UUIDs.

## Services & Characteristics

### 1. IO Service
**UUID**: `11a70300-f691-4b93-a6f4-0968f5b648f8`

Handles output (LEDs) and device configuration.

| Feature | UUID | R/W | Description |
| :--- | :--- | :--- | :--- |
| **LEDs** | `...0301...` | Write | Control the 9 RGB LEDs. |
| Keep Alive | `...0302...` | Write | *Purpose unclear, possibly keep-alive.* |
| Battery | `...0303...` | Read | *Likely battery level.* |
| **Brightness** | `...0304...` | Write | Global current limit/brightness control. |

*(Base UUID for Characteristics is same as Service, only the short ID changes: `11a703xx-f691-4b93-a6f4-0968f5b648f8`)*

### 2. Sensor Service
**UUID**: `11a70200-f691-4b93-a6f4-0968f5b648f8`

Handles input from the IR proximity sensors.

| Feature | UUID | R/W | Description |
| :--- | :--- | :--- | :--- |
| **Sensor Data** | `...0201...` | Notify | Stream of raw proximity values. |

---

## Data Formats

### LED Control (`0301`)
To update the LEDs, write **19 bytes** to the characteristic.

- **Byte 0**: `0x01` (Header)
- **Bytes 1-18**: 9 x **RGB565** color values (2 bytes per LED).

#### LED Index Mapping
| Index | Position |
| :--- | :--- |
| 0 | North (Right) |
| 1 | East (Top) |
| 2 | East (Bottom) |
| 3 | South (Right) |
| 4 | South (Left) |
| 5 | West (Bottom) |
| 6 | West (Top) |
| 7 | North (Left) |
| 8 | Center |

#### RGB565 Packing
Each color needs to be compressed from 24-bit RGB (8-8-8) to 16-bit RGB (5-6-5).

```javascript
// JS Example
r5 = (r >> 3) & 0x1F;
g6 = (g >> 2) & 0x3F;
b5 = (b >> 3) & 0x1F;
packed = (r5 << 11) | (g6 << 5) | b5;

byte1 = (packed >> 8) & 0xFF; // High byte
byte2 = packed & 0xFF;        // Low byte
```

### Brightness (`0304`)
Write **1 byte**.
- Range: `0` (Off) to `255` (Max Brightness).

### Sensor Data (`0201`)
Receive **4 bytes** via Notification.

- **Format**: `[North, East, South, West]`
- **Value**: Raw IR proximity reading.
  - `0`: Very Close (Strong reflection)
  - `255`: Far (No reflection)

*Note: Thresholds used in this library consider values > 220 as "inactive".*
