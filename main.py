import asyncio
from keep_alive import keep_alive
from bot import run_bot

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(run_bot())
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            pass  # Ignore this error on shutdown
        else:
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.get_event_loop().run_until_complete(run_bot())
    except Exception as e:
        print(f"Fatal error: {e}")
