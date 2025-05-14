import asyncio
import struct
import json
import os
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bleak import BleakClient, BleakScanner
from starlette.requests import Request

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Calibration and persistent variables
client: BleakClient = None
calibration_point = {"sensor": None, "percentage": None}
CALIBRATION_FILE = "calibration.json"
ANALYZER_SERVICE_UUID = "0bcb0001-0be0-4c5a-8f2b-ccb9e8cdbb1f"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

def is_valid_sensor_value(val):
    return 500 < val < 50000

def estimate_oxygen(sensor_value):
    cal_sensor = calibration_point.get("sensor")
    cal_percentage = calibration_point.get("percentage")
    if not cal_sensor or not cal_percentage:
        return None
    return (sensor_value / cal_sensor) * cal_percentage

def save_calibration():
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration_point, f)

def load_calibration():
    global calibration_point
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "r") as f:
            calibration_point = json.load(f)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan", response_class=HTMLResponse)
async def scan_devices(request: Request):
    devices = await BleakScanner.discover(timeout=5.0)
    dna_devices = [{"name": d.name, "address": d.address}
                   for d in devices if d.name and re.match(r"^DNA\s+\d+$", d.name)]
    return templates.TemplateResponse("devices.html", {"request": request, "devices": dna_devices})

@app.post("/connect/{address}")
async def connect_device(address: str):
    global client
    if client and client.is_connected:
        await client.disconnect()
    client = BleakClient(address)
    await client.connect()
    client.services
    return {"status": "connected", "address": address}

@app.post("/calibrate/{percentage}")
async def calibrate(percentage: float):
    if not client or not client.is_connected:
        return {"error": "Not connected"}
    service = client.services.get_service(ANALYZER_SERVICE_UUID)
    characteristic = service.characteristics[0]
    value = await client.read_gatt_char(characteristic.uuid)
    if len(value) != 8:
        return {"error": "Invalid data"}
    values = struct.unpack("<4H", value)
    sensor = values[1]
    if not is_valid_sensor_value(sensor):
        return {"error": f"Sensor value {sensor} out of range"}
    calibration_point["sensor"] = sensor
    calibration_point["percentage"] = percentage
    save_calibration()
    return {"status": "calibrated", "sensor": sensor, "percentage": percentage}

@app.get("/read-once")
async def read_once():
    if not client or not client.is_connected:
        return {"error": "Not connected"}
    service = client.services.get_service(ANALYZER_SERVICE_UUID)
    characteristic = service.characteristics[0]
    value = await client.read_gatt_char(characteristic.uuid)
    if len(value) != 8:
        return {"error": "Invalid data"}
    values = struct.unpack("<4H", value)
    sensor = values[1]
    o2 = estimate_oxygen(sensor)
    return {
        "raw": value.hex(),
        "sensor": sensor,
        "oxygen": f"{o2:.1f}%" if o2 is not None else "Calibration needed"
    }

@app.get("/battery")
async def battery_level():
    if not client or not client.is_connected:
        return {"error": "Not connected"}
    battery_service = client.services.get_service(BATTERY_SERVICE_UUID)
    battery_char = battery_service.get_characteristic(BATTERY_LEVEL_CHAR_UUID)
    battery_data = await client.read_gatt_char(battery_char.uuid)
    return {"battery": battery_data[0]}

@app.websocket("/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            reading = await read_once()
            await websocket.send_json(reading)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

load_calibration()
