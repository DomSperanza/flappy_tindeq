#!/usr/bin/env python3

from tindeq_backend.tindeq import TindeqProgressor
import asyncio

async def example():
    class Wrapper:
        def log_force_sample(self, time, weight):
            print(f"{time}: {weight}")

    wrap = Wrapper()
    async with TindeqProgressor(wrap) as tindeq:
        await tindeq.get_batt()
        await asyncio.sleep(0.5)
        await tindeq.get_fw_info()
        await asyncio.sleep(0.5)
        await tindeq.get_err()
        await asyncio.sleep(0.5)
        await tindeq.clear_err()
        await asyncio.sleep(0.5)

        await tindeq.soft_tare()
        await asyncio.sleep(1)
        while True:
          try:
            await tindeq.start_logging_weight()
          except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
