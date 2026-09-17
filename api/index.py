#===== IMPORTS =====

from http.server import BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN

from bot.commands import router as commands_router
from bot.callbacks import router as callbacks_router


#===== BOT =====

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)


#===== DISPATCHER =====

dp = Dispatcher()

dp.include_router(commands_router)
dp.include_router(callbacks_router)


#===== VERCEL HANDLER =====

class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain"
        )
        self.end_headers()

        self.wfile.write(
            b"IPL Auction Bot is running"
        )

    def do_POST(self):

        import asyncio
        import json

        content_length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )

        body = self.rfile.read(
            content_length
        )

        update_data = json.loads(
            body.decode("utf-8")
        )

        asyncio.run(
            dp.feed_raw_update(
                bot,
                update_data
            )
        )

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain"
        )
        self.end_headers()

        self.wfile.write(
            b"OK"
        )
