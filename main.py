#===== IMPORTS =====

import asyncio

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


#===== REGISTER ROUTERS =====

dp.include_router(commands_router)
dp.include_router(callbacks_router)


#===== MAIN =====

async def main():

    print("✅ Bot Started")

    await dp.start_polling(
        bot
    )


#===== RUN =====

if __name__ == "__main__":

    asyncio.run(
        main()
    )