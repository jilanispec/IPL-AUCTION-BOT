from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio

from config import BOT_TOKEN

from bot.commands import router as commands_router
from bot.callbacks import router as callbacks_router

()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# Register routers AFTER creating Dispatcher
dp.include_router(commands_router)
dp.include_router(callbacks_router)


async def main():
    print("✅ Bot Started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())