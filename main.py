from keep_alive import keep_alive
from bot import run_bot
import asyncio

if __name__ == "__main__":
    keep_alive()
    asyncio.run(run_bot())
