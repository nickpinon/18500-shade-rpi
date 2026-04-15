# Raspberry Pi BLE Starter

This folder contains a starter Bluetooth Low Energy peripheral for the iPhone `Umbrella App`.

## BLE contract

The iPhone app looks for a BLE peripheral named `UmbrellaPi` with this custom service:

- Service UUID: `A4F1C6A0-7D5F-4E3D-8A91-102E88D13001`
- Command characteristic UUID: `A4F1C6A0-7D5F-4E3D-8A91-102E88D13002`
- Status characteristic UUID: `A4F1C6A0-7D5F-4E3D-8A91-102E88D13003`

The app writes JSON commands such as:

```json
{"type":"move","direction":"up"}
{"type":"stop"}
{"type":"mode","value":"Manual"}
```

The Pi returns JSON status shaped like:

```json
{"position":52,"mode":"Manual","moving":false,"connected":true}
```

## Files

- `ble_server.py`: starter BLE peripheral
- `requirements.txt`: Python dependency list

## Setup

1. Enable Bluetooth on the Raspberry Pi.
2. Install BlueZ and Python dependencies.
3. Create a virtual environment if you want isolation.
4. Install dependencies with `pip install -r requirements.txt`.
5. Run `python ble_server.py`.

## Notes

- This starter keeps umbrella state in memory so the iPhone app can connect and test BLE end to end.
- Replace the placeholder movement logic in `handle_command()` with your GPIO or motor controller code.
- If your Linux image has a different BlueZ setup, you may need to adjust permissions or install the library through apt instead of pip.
