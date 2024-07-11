import asyncio
from bleak import BleakScanner

async def run():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Device found: {device.name}, {device.address}")

loop = asyncio.get_event_loop()
loop.run_until_complete(run())