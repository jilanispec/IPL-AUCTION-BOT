#===== IMPORTS =====

import asyncio

from auction.manager import (
    get_auction,
    save_auction,
    start_auction,
    complete_sold_player,
)

from utils.auction_display import (
    send_auction_player
)


#===== ACTIVE TIMER TASKS =====

timer_tasks = {}

alert_states = {}


#===== START PLAYER TIMER =====

def start_player_timer(
    bot,
    chat_id
):

    old_task = timer_tasks.get(
        chat_id
    )

    if (
        old_task
        and not old_task.done()
    ):

        old_task.cancel()

    alert_states[chat_id] = set()

    task = asyncio.create_task(
        run_player_timer(
            bot,
            chat_id
        )
    )

    timer_tasks[chat_id] = task

    return task


#===== CANCEL PLAYER TIMER =====

def cancel_player_timer(
    chat_id
):

    task = timer_tasks.get(
        chat_id
    )

    if (
        task
        and not task.done()
    ):

        task.cancel()

    timer_tasks.pop(
        chat_id,
        None
    )

    alert_states.pop(
        chat_id,
        None
    )


#===== BUILD TIMER CAPTION =====

def build_timer_caption(
    auction
):

    player = auction.get(
        "current_player"
    )

    if not player:
        return None

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

    leading_team = auction.get(
        "leading_team"
    )

    if not leading_team:

        leading_team = "No Bids Yet"

    timer = auction.get(
        "timer",
        0
    )

    return (
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

        f"👥 Leading Team : "
        f"<b>{leading_team}</b>\n"

        f"⏳ Time Left : "
        f"<b>{timer} sec</b>\n\n"

        "📢 <b>Managers can now bid.</b>"
    )


#===== UPDATE TIMER MESSAGE =====

async def update_timer_message(
    bot,
    auction
):

    message_id = auction.get(
        "auction_message_id"
    )

    chat_id = auction.get(
        "auction_chat_id"
    )

    if not message_id:
        return

    if not chat_id:
        return

    caption = build_timer_caption(
        auction
    )

    if not caption:
        return

    try:

        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=caption
        )

    except Exception as e:

        error_text = str(e).lower()

        if (
            "message is not modified"
            in error_text
        ):

            return

        if (
            "message to edit not found"
            in error_text
        ):

            print(
                "TIMER MESSAGE NOT FOUND"
            )

            return

        print(
            "TIMER MESSAGE UPDATE ERROR:",
            e
        )


#===== SEND TIMER ALERT =====

async def send_timer_alert(
    bot,
    chat_id,
    seconds,
    alerts_sent
):

    if seconds in alerts_sent:

        return

    if seconds == 10:

        text = (
            "⏰ <b>10 seconds remaining!</b>"
        )

    elif seconds == 5:

        text = (
            "⚠️ <b>5 seconds remaining!</b>"
        )

    elif seconds == 1:

        text = (
            "🚨 <b>1 second remaining!</b>"
        )

    else:

        return

    alerts_sent.add(
        seconds
    )

    try:

        await bot.send_message(
            chat_id,
            text
        )

    except Exception as e:

        print(
            "TIMER ALERT ERROR:",
            e
        )


#===== PLAYER TIMER =====

async def run_player_timer(
    bot,
    chat_id
):

    alerts_sent = alert_states.setdefault(
        chat_id,
        set()
    )

    timer_version = None

    try:

        while True:

            await asyncio.sleep(
                1
            )

            auction = get_auction(
                chat_id
            )

            if not auction:

                return

            if auction.get(
                "chat_id"
            ) != chat_id:

                return

            if auction.get(
                "status"
            ) != "RUNNING":

                return

            current_version = auction.get(
                "timer_version",
                0
            )

            if timer_version is None:

                timer_version = (
                    current_version
                )

            elif (
                current_version
                != timer_version
            ):

                timer_version = (
                    current_version
                )

                alerts_sent.clear()

                continue

            timer = auction.get(
                "timer",
                20
            )

            try:

                timer = int(
                    timer
                )

            except (
                TypeError,
                ValueError
            ):

                timer = 20

            timer -= 1

            if timer < 0:

                timer = 0

            auction["timer"] = (
                timer
            )

            save_auction(
                auction
            )

            #===== 10 SECOND ALERT =====

            if timer == 10:

                await send_timer_alert(
                    bot,
                    chat_id,
                    10,
                    alerts_sent
                )

                await update_timer_message(
                    bot,
                    auction
                )

            #===== 5 SECOND ALERT =====

            elif timer == 5:

                await send_timer_alert(
                    bot,
                    chat_id,
                    5,
                    alerts_sent
                )

                await update_timer_message(
                    bot,
                    auction
                )

            #===== 1 SECOND ALERT =====

            elif timer == 1:

                await send_timer_alert(
                    bot,
                    chat_id,
                    1,
                    alerts_sent
                )

                await update_timer_message(
                    bot,
                    auction
                )

            #===== TIMER FINISHED =====

            if timer <= 0:

                await finish_current_player(
                    bot,
                    chat_id
                )

                return

    except asyncio.CancelledError:

        return

    except Exception as e:

        print(
            "AUCTION TIMER ERROR:",
            e
        )

    finally:

        current_task = timer_tasks.get(
            chat_id
        )

        if (
            current_task
            and current_task.done()
        ):

            timer_tasks.pop(
                chat_id,
                None
            )


#===== FINISH CURRENT PLAYER =====

async def finish_current_player(
    bot,
    chat_id
):

    auction = get_auction(
        chat_id
    )

    if not auction:

        return

    if auction.get(
        "status"
    ) != "RUNNING":

        return

    current_player = auction.get(
        "current_player"
    )

    if not current_player:

        return

    leading_team = auction.get(
        "leading_team"
    )

    #===== SOLD =====

    if leading_team:

        sold_result = complete_sold_player(
            chat_id
        )

        if (
            isinstance(
                sold_result,
                dict
            )
            and sold_result.get(
                "success"
            )
        ):

            price = float(
                sold_result.get(
                    "price",
                    auction.get(
                        "current_bid",
                        0
                    )
                )
            )

            await bot.send_message(
                chat_id,
                "🔨 <b>SOLD!</b>\n\n"
                f"👤 {current_player.get('name', 'Unknown')}\n"
                f"🏏 Team: <b>{leading_team}</b>\n"
                f"💰 Price: "
                f"<b>₹{price:.2f} Cr</b>"
            )

        else:

            print(
                "SOLD ERROR:",
                sold_result
            )

            return

    #===== UNSOLD =====

    else:

        await bot.send_message(
            chat_id,
            "❌ <b>UNSOLD!</b>\n\n"
            f"👤 {current_player.get('name', 'Unknown')}\n"
            "💰 No valid bids received."
        )

    #===== WAIT BEFORE NEXT PLAYER =====

    await asyncio.sleep(
        2
    )

    auction = get_auction(
        chat_id
    )

    if not auction:

        return

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        return

    #===== CHECK PLAYERS LEFT =====

    players = auction.get(
        "players",
        []
    )

    if not players:

        auction["status"] = (
            "WAITING"
        )

        auction["current_player"] = None
        auction["current_bid"] = 0
        auction["leading_team"] = None
        auction["leading_manager_id"] = None
        auction["timer"] = 0

        auction["skip_votes"] = []
        auction["pending_bid"] = None

        save_auction(
            auction
        )

        await bot.send_message(
            chat_id,
            "🏁 <b>Player Set Finished!</b>\n\n"
            "All players from the loaded set "
            "have been processed."
        )

        return

    #===== PREPARE NEXT PLAYER =====

    auction["status"] = (
        "WAITING"
    )

    auction["current_player"] = None
    auction["current_bid"] = 0
    auction["leading_team"] = None
    auction["leading_manager_id"] = None
    auction["timer"] = 0

    auction["skip_votes"] = []
    auction["pending_bid"] = None

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    save_auction(
        auction
    )

    #===== START NEXT PLAYER =====

    player = start_auction(
        chat_id
    )

    if not isinstance(
        player,
        dict
    ):

        print(
            "NEXT PLAYER ERROR:",
            player
        )

        return

    auction = get_auction(
        chat_id
    )

    if not auction:

        return

    await send_auction_player(
        bot,
        chat_id,
        player,
        auction
    )

    start_player_timer(
        bot,
        chat_id
    )