import os
import asyncio
import struct
from bleak import BleakClient
from gue_label import get_valid_initials, create_gue_label
from label_printer import list_printers, select_printer, print_label
from analyzer import load_device_address, load_calibration, select_device, live_read

async def analysis():
    # Placeholder for the analysis function
    # This function should contain the logic to interact with the analyzer
    # Load calibration data
    calibration = load_calibration()
    # Connect to the device
    address = load_device_address()
    if not address:
        address = await select_device()
        if not address:
            print("❌ No device selected.")
            return

    async with BleakClient(address) as client:
        ANALYZER_SERVICE_UUID = "0bcb0001-0be0-4c5a-8f2b-ccb9e8cdbb1f"
        analyzer_service = client.services.get_service(ANALYZER_SERVICE_UUID)
        characteristic = analyzer_service.characteristics[0]
        try:
            await client.connect()
            print(f"✅ Connected to {address}")
            result = await live_read(client, characteristic, calibration)
        except Exception as e:
            print(f"⚠ Connection error: {e}")
    return result

async def main():
    # Start by getting users initials
    initials = get_valid_initials()
    # Perform analysis
    percentage = await analysis()

    # Create the label file
    label_file = create_gue_label(percentage,initials)

    # Find printers and print label
    printers = list_printers()
    if printers:
        selected_printer = select_printer(printers)
        if os.path.exists(label_file):
            print_label(label_file, selected_printer)
        else:
            print(f"❌ File {label_file} does not exist.")
    else:
        print("❌ No printers found.")

if __name__ == "__main__":
    asyncio.run(main())