from keep_alive import keep_alive
from bot import run_bot
import asyncio

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
