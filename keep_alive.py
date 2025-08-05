from aiohttp import web
import asyncio
import logging

class KeepAlive:
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/", self.health_check)
        self.runner = None
        self.site = None

    async def health_check(self, request):
        return web.Response(text="Bot is alive!")

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logging.info(f"Keep-alive server running on port {self.port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
