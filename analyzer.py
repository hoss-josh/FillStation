import asyncio
import json
import os
import re
import struct
from bleak import BleakClient, BleakScanner

# === Constants ===
ADDRESS_FILE = "data/device_address.txt"
CALIBRATION_FILE = "data/calibration.json"


# === Calibration data ===
calibration_point = {
    "sensor": None,
    "percentage": None
}

# === Device Selection ===
async def select_device():
    print("🔍 Scanning for BLE devices (5 seconds)...")
    devices = await BleakScanner.discover(timeout=5.0)
    dna_pattern = re.compile(r"^DNA\s+\d+$")

    filtered_devices = [
        d for d in devices if dna_pattern.match(d.name or "")
    ]

    if not filtered_devices:
        print("No 'DNA' devices found.")
        return None

    for i, d in enumerate(filtered_devices):
        print(f"[{i}] {d.name} ({d.address})")

    while True:
        choice = input(f"Select device [0-{len(filtered_devices)-1}]: ")
        if choice.isdigit() and 0 <= int(choice) < len(filtered_devices):
            address = filtered_devices[int(choice)].address
            save_device_address(address)
            print(f"✅ Selected {filtered_devices[int(choice)].name} ({address})")
            return address
        print("Invalid selection.")

def save_device_address(address):
    with open(ADDRESS_FILE, "w") as f:
        f.write(address)

def load_device_address():
    if os.path.exists(ADDRESS_FILE):
        with open(ADDRESS_FILE, "r") as f:
            return f.read().strip()
    return None

# === Calibration ===
def save_calibration():
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration_point, f)
    print("Calibration saved.")

def load_calibration():
    calibration_point = {
        "sensor": None,
        "percentage": None
    }
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "r") as f:
            data = json.load(f)
            if is_valid_sensor_value(data.get("sensor", 0)):
                calibration_point = data
                print(f"Calibration loaded: {calibration_point}")
            else:
                print("Invalid calibration data.")
    else:
        print("No calibration file found.")
    return calibration_point

def is_valid_sensor_value(val):
    return 500 < val < 50000

def estimate_oxygen(sensor_value, calibration_point):
    cal_sensor = calibration_point.get("sensor")
    cal_percentage = calibration_point.get("percentage")
    if not cal_sensor or not cal_percentage:
        return None
    return (sensor_value / cal_sensor) * cal_percentage

async def calibrate(client, characteristic, calibration_percentage):
    print(f"\nCalibrating to {calibration_percentage}% O₂...")
    try:
        value = await asyncio.wait_for(client.read_gatt_char(characteristic.uuid), timeout=5.0)
    except asyncio.TimeoutError:
        print("BLE read timed out.")
        return

    if len(value) != 8:
        print("Unexpected data length.")
        return

    values = struct.unpack("<4H", value)
    sensor = values[1]

    if not is_valid_sensor_value(sensor):
        print(f"Sensor value {sensor} out of expected range.")
        return

    calibration_point["sensor"] = sensor
    calibration_point["percentage"] = calibration_percentage
    save_calibration()
    print(f"✅ Calibrated at {sensor} for {calibration_percentage}% O₂.")


# === Real-time Reading ===
async def live_read(client, characteristic, calibration_point):
    print("\nStarting live readings. Highest of 3 consecutive readings will be used.")
    try:
        highest = 0
        for i in range(3):
            print(f"\nReading {i + 1} of 3...")
            value = await asyncio.wait_for(client.read_gatt_char(characteristic.uuid), timeout=5.0)
            if len(value) == 8:
                values = struct.unpack("<4H", value)
                sensor = values[1]
                o2_percent = estimate_oxygen(sensor, calibration_point)
                if o2_percent is not None:
                    print(f"O₂: {o2_percent:.1f}%")
                else:
                    print(f"O₂: (calibration needed)")
            else:
                print(f"Unexpected data: {value.hex()}")
            await asyncio.sleep(1)
            i += 1
            if o2_percent > highest:
                highest = o2_percent
        print("\nLive readings complete.")
        return round(highest, 1)
    except asyncio.CancelledError:
        print("\nLive readings stopped by user.")
    except asyncio.TimeoutError:
        print("\nBLE read timeout.")
