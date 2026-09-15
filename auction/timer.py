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

from storage.json_manager import (
    load_json,
    save_json
)

from config import TOURNAMENTS_FILE


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

    #===== TOURNAMENT TIMER CHECK =====
    tournaments = load_json(TOURNAMENTS_FILE)

    if isinstance(tournaments, list):
        for tournament in tournaments:
            if (
                tournament.get("chat_id") == chat_id
                and tournament.get("status") == "AUCTION_RUNNING"
                and tournament.get("auction_setup", {}).get("status") == "RUNNING"
            ):
                await run_tournament_timer(bot, chat_id)
                return

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


#===== TOURNAMENT TIMER CARD =====

def build_tournament_timer_text(tournament):

    setup = tournament.get("auction_setup", {})
    player = setup.get("current_player") or {}

    name = (
        player.get("name")
        or player.get("display_name")
        or player.get("first_name")
        or player.get("player_name")
        or "Unknown Player"
    )

    country = player.get("country", "Unknown")
    role = player.get("role", "Unknown")
    timer = int(setup.get("timer", 0))
    bid = float(setup.get("current_bid_lakhs", setup.get("base_price", 0)))
    base = float(setup.get("base_price", 0))

    leading = setup.get("leading_team")
    if isinstance(leading, dict):
        code = leading.get("short_code") or leading.get("code") or leading.get("name") or "None"
        long_name = leading.get("name")
        leading_text = f"{code} — {long_name}" if long_name and str(long_name).upper() != str(code).upper() else str(code)
    else:
        leading_text = str(leading) if leading else "None"

    return (
        "🏆 <b>TOURNAMENT AUCTION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>{name}</b>\n"
        f"🌍 Country : <b>{country}</b>\n"
        f"🎯 Role : <b>{role}</b>\n\n"
        f"📦 Set : <b>{setup.get('selected_set', 1)}</b>\n\n"
        f"💰 Base Price : <b>₹{base:g} Lakhs</b>\n"
        f"💰 Current Bid : <b>₹{bid:g} Lakhs</b>\n\n"
        f"👑 Leading Team : <b>{leading_text}</b>\n"
        f"⏳ Time Left : <b>{timer} sec</b>\n\n"
        "📢 <b>BIDDING IS OPEN!</b>"
    )


async def update_tournament_timer_message(bot, tournament):

    setup = tournament.get("auction_setup", {})
    message_id = setup.get("auction_message_id")
    chat_id = tournament.get("chat_id")

    if not message_id or not chat_id:
        return

    text = build_tournament_timer_text(tournament)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            print("TOURNAMENT TIMER MESSAGE ERROR:", e)


async def run_tournament_timer(bot, chat_id):

    alerts_sent = alert_states.setdefault(chat_id, set())

    try:
        while True:
            await asyncio.sleep(1)

            tournaments = load_json(TOURNAMENTS_FILE)
            if not isinstance(tournaments, list):
                return

            tournament = None
            tournament_index = None

            for index, item in enumerate(tournaments):
                if (
                    item.get("chat_id") == chat_id
                    and item.get("status") == "AUCTION_RUNNING"
                    and item.get("auction_setup", {}).get("status") == "RUNNING"
                ):
                    tournament = item
                    tournament_index = index
                    break

            if tournament is None:
                return

            setup = tournament.get("auction_setup", {})
            timer = int(setup.get("timer", 20)) - 1
            if timer < 0:
                timer = 0

            setup["timer"] = timer
            tournament["auction_setup"] = setup
            tournaments[tournament_index] = tournament
            save_json(TOURNAMENTS_FILE, tournaments)

            #===== UPDATE TELEGRAM CARD ONLY AT 10 / 5 / 1 =====

            if timer in (10, 5, 1):

                await update_tournament_timer_message(
                    bot,
                    tournament
                )

                await send_timer_alert(
                    bot,
                    chat_id,
                    timer,
                    alerts_sent
                )

            if timer <= 0:
                await finish_tournament_player(bot, chat_id)
                return

    except asyncio.CancelledError:
        return
    except Exception as e:
        print("TOURNAMENT TIMER ERROR:", e)

# ====== FINISH TOURNAMENT PLAHER==

async def finish_tournament_player(bot, chat_id):

    tournaments = load_json(TOURNAMENTS_FILE)
    if not isinstance(tournaments, list):
        return

    tournament = None
    tournament_index = None

    for index, item in enumerate(tournaments):
        if (
            item.get("chat_id") == chat_id
            and item.get("status") == "AUCTION_RUNNING"
        ):
            tournament = item
            tournament_index = index
            break

    if tournament is None:
        return

    setup = tournament.get("auction_setup", {})
    player = setup.get("current_player") or {}
    
    #===== LOCK CURRENT PLAYER =====

    if setup.get("status") != "RUNNING":
        return

    setup["status"] = "PROCESSING"
    setup["timer"] = 0

    tournament["auction_setup"] = setup
    tournaments[tournament_index] = tournament

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    player_name = (
        player.get("name")
        or player.get("display_name")
        or player.get("first_name")
        or player.get("player_name")
        or "Unknown Player"
    )
    leading = setup.get("leading_team")
    bid = float(setup.get("current_bid_lakhs", setup.get("base_price", 0)))

    #===== SOLD / UNSOLD =====
    if leading:
        team = None
        for item in tournament.get("teams", []):
            code = item.get("short_code") or item.get("code") or item.get("name")
            if str(code).upper() == str(leading).upper():
                team = item
                break

        if team is not None:
            purse_lakhs = float(team.get("purse_lakhs", team.get("purse", 0)))
            team["purse_lakhs"] = max(0.0, purse_lakhs - bid)

            sold_player = dict(player)
            sold_player["name"] = (
                player.get("name")
                or player.get("display_name")
                or player.get("first_name")
                or player.get("player_name")
                or "Unknown Player"
            )
            sold_player["sold_price"] = bid / 100
            sold_player["sold_price_lakhs"] = bid
            team.setdefault("players", []).append(sold_player)

            display = team.get("name", str(leading))
            code = team.get("short_code", str(leading))
            display_team = f"{code} — {display}" if str(display).upper() != str(code).upper() else str(code)

            await bot.send_message(
                chat_id,
                "🔨 <b>SOLD!</b>\n\n"
                f"👤 <b>{player_name}</b>\n"
                f"🏏 Team : <b>{display_team}</b>\n"
                f"💰 Price : <b>₹{bid:g} Lakhs</b>"
            )
        else:
            await bot.send_message(
                chat_id,
                "❌ <b>UNSOLD!</b>\n\n"
                f"👤 <b>{player_name}</b>\n"
                "💰 Team could not be found."
            )
    else:
        await bot.send_message(
            chat_id,
            "❌ <b>UNSOLD!</b>\n\n"
            f"👤 <b>{player_name}</b>\n"
            "💰 No valid bids received."
        )

    #===== NEXT PLAYER =====
    players = setup.get("players") or []
    next_index = int(setup.get("current_player_index", 0)) + 1

    if next_index >= len(players):
        setup["status"] = "FINISHED"
        tournament["status"] = "AUCTION_FINISHED"
        setup["current_player"] = None
        setup["timer"] = 0
        tournament["auction_setup"] = setup
        tournaments[tournament_index] = tournament
        save_json(TOURNAMENTS_FILE, tournaments)

        await bot.send_message(
            chat_id,
            "🏁 <b>TOURNAMENT AUCTION FINISHED!</b>\n\n"
            "All players from the selected set have been processed."
        )
        return

    await asyncio.sleep(2)

    next_player = players[next_index]
    setup["current_player_index"] = next_index
    setup["current_player"] = next_player
    setup["current_bid_lakhs"] = float(setup.get("base_price", 0))
    setup["leading_team"] = None
    setup["leading_manager_id"] = None
    setup["timer"] = 20
    setup["status"] = "RUNNING"
    tournament["auction_setup"] = setup
    tournaments[tournament_index] = tournament
    save_json(TOURNAMENTS_FILE, tournaments)

    await update_tournament_timer_message(bot, tournament)
    start_player_timer(bot, chat_id)


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