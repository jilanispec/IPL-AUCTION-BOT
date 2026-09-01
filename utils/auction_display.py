from aiogram.types import FSInputFile

from utils.image_helper import prepare_player_image
from auction.manager import save_auction


async def send_auction_player(
    bot,
    chat_id,
    player,
    auction
):

    name = player.get(
        "name",
        "Unknown"
    )

    player_id = player.get(
        "id",
        "-"
    )

    country = player.get(
        "country",
        "Unknown"
    )

    overseas = player.get(
        "overseas",
        False
    )

    base_price = player.get(
        "base_price",
        0
    )

    if overseas:
        overseas_text = "🌍 Overseas"
    else:
        overseas_text = "🇮🇳 Indian"

    image_path = prepare_player_image(
        player.get("image"),
        name,
        country,
        base_price
    )

    caption = (
        "🏏 <b>IPL MEGA AUCTION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 <b>{name}</b>\n\n"

        f"🆔 ID : <code>{player_id}</code>\n"
        f"🌎 Nationality : <b>{country}</b>\n"
        f"{overseas_text}\n\n"

        f"💰 <b>Base Price : "
        f"₹{float(base_price):.2f} Cr</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Current Bid : "
        f"<b>₹{float(auction.get('current_bid', 0)):.2f} Cr</b>\n"

        "👥 Leading Team : "
        "<b>No Bids Yet</b>\n"

        f"⏳ Time Left : "
        f"<b>{auction.get('timer', 20)} sec</b>\n\n"

        "📢 <b>Managers can now bid.</b>"
    )

    if image_path:

        photo = FSInputFile(
            image_path
        )

        sent_message = await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption
        )

    else:

        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=caption
        )

    auction["auction_message_id"] = (
        sent_message.message_id
    )

    auction["auction_chat_id"] = chat_id

    save_auction(
        auction
    )

    return sent_message