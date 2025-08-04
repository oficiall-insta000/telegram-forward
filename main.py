from keep_alive import keep_alive
from bot import main
import asyncio

if __name__ == "__main__":
    keep_alive()
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
