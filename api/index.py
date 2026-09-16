#===== IMPORTS =====

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


#===== VERCEL WEBHOOK =====

async def process_update(update_data):

    await dp.feed_raw_update(
        bot,
        update_data
    )


#===== VERCEL ENTRY POINT =====

async def handler(request):

    if request.method != "POST":

        return {
            "statusCode": 200,
            "body": "IPL Auction Bot is running"
        }

    update_data = await request.json()

    await process_update(
        update_data
    )

    return {
        "statusCode": 200,
        "body": "OK"
    }
