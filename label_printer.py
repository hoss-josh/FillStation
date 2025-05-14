import os
import subprocess

def list_printers():
    try:
        output = subprocess.check_output(['lpstat', '-p'], text=True)
        printers = []
        for line in output.strip().split('\n'):
            if line.startswith('printer'):
                parts = line.split()
                if len(parts) >= 2:
                    printers.append(parts[1])
        return printers
    except subprocess.CalledProcessError:
        print("❌ Could not list printers. Is CUPS running?")
        return []

def select_printer(printers):
    dymo_printers = [p for p in printers if "DYMO" in p.upper()]
    if dymo_printers:
        print("🎯 Found DYMO printers:")
        for idx, printer in enumerate(dymo_printers):
            print(f"[{idx + 1}] {printer}")
    else:
        print("⚠ No DYMO printers found. Listing all available printers:")
        for idx, printer in enumerate(printers):
            print(f"[{idx + 1}] {printer}")

    choice = input("Select printer by number (default 1): ").strip()
    try:
        index = int(choice) - 1 if choice else 0
        return (dymo_printers or printers)[index]
    except (ValueError, IndexError):
        print("Invalid selection, using default printer.")
        return None

def print_label(filename, printer_name=None):
    if printer_name:
        command = f'lpr -P "{printer_name}" "{filename}"'
    else:
        command = f'lpr "{filename}"'

    print(f"🖨️ Sending label to printer: {printer_name or 'default'}")
    result = os.system(command)
    if result == 0:
        print("✅ Label sent to printer.")
    else:
        print("❌ Failed to send label to printer.")
