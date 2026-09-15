# ====== IMPORTS ======

import os
import json
import time

from aiogram import Router, F

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)

from config import (
    DATA_FOLDER,
    TOURNAMENTS_FILE,
    TOURSETS_FOLDER
)
from auction.manager import (
    create_auction,
    get_auction,
    save_auction,
    set_chat_context,
    save_restore_snapshot,
)

from aiogram.exceptions import TelegramBadRequest

from storage.json_manager import (
    load_json,
    save_json
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.commands import TournamentSetLimitState


from utils.helpers import is_admin, is_group

from bot.keyboards import (
    auction_keyboard,
    group_start_keyboard,
)

from auction.timer import start_player_timer


# ====== ROUTER ======

router = Router()

#===== SET BUTTON SLOWDOWN =====

SET_BUTTON_COOLDOWN = 3

_last_set_click = {}


def set_button_allowed(
    user_id: int
) -> bool:

    now = time.monotonic()

    last_click = _last_set_click.get(
        user_id,
        0
    )

    if now - last_click < SET_BUTTON_COOLDOWN:

        return False

    _last_set_click[user_id] = now

    return True
    
    

    
# ====== GROUP START → MEGA AUCTION ======

@router.callback_query(
    F.data == "start_mega_auction"
)
async def start_mega_auction(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🏏 <b>IPL MEGA AUCTION</b>\n\n"
        "Ready to start a Mega Auction?\n\n"
        "👑 Claim the host position below.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👑 Claim Host",
                        callback_data="claim_host:mega"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Back",
                        callback_data="group_start"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# ====== GROUP START → LEGENDS AUCTION ======

@router.callback_query(
    F.data == "start_legends_auction"
)
async def start_legends_auction(
    callback: CallbackQuery
):

    await callback.answer(
        "🦁 Legends Auction is under development.",
        show_alert=True
    )


# ====== GROUP START → BACK ======

@router.callback_query(
    F.data == "group_start"
)
async def group_start(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🏏 <b>IPL AUCTION</b>\n\n"
        "Start an Auction\n\n"
        "Choose an auction type below.",
        reply_markup=group_start_keyboard
    )

    await callback.answer()


# ====== CLAIM HOST ======

@router.callback_query(
    F.data == "claim_host:mega"
)
async def claim_host(
    callback: CallbackQuery
):

    chat_id = callback.message.chat.id
    user = callback.from_user

    set_chat_context(chat_id)

    auction = create_auction(
        chat_id=chat_id,
        host_id=user.id,
        host_username=user.username or user.first_name,
        auction_type="mega"
    )

    # =========================
    # ALREADY ACTIVE
    # =========================

    if auction == "already_exists":

        await callback.answer(
            "❌ An auction is already active in this group.",
            show_alert=True
        )

        return

    # =========================
    # HOST CLAIMED
    # =========================

    await callback.message.edit_text(
        "🏏 <b>IPL MEGA AUCTION</b>\n\n"
        "👑 <b>Host Claimed!</b>\n\n"
        f"🆔 Auction ID : "
        f"<code>{auction['auction_id']}</code>\n"
        f"👑 Host : <b>{user.first_name}</b>\n\n"
        "📌 Status : Waiting\n\n"
        "Host can now use:\n"
        "<code>/add_team TEAM PURSE @MANAGER</code>\n"
        "<code>/load_set SET_NAME</code>"
    )

    await callback.answer(
        "👑 You are now the auction host!"
    )



#===== CONFIRM END AUCTION =====

@router.callback_query(
    F.data == "confirm_end_auction"
)
async def confirm_end_auction(
    callback: CallbackQuery
):

    #===== GET GROUP =====

    chat_id = (
        callback.message.chat.id
    )

    set_chat_context(
        chat_id
    )

    auction = get_auction(
        chat_id
    )

    #===== NO AUCTION =====

    if not auction:

        await callback.answer(
            "❌ No active auction found.",
            show_alert=True
        )

        return

    #===== HOST / ADMIN CHECK =====

    member = await callback.message.chat.get_member(
        callback.from_user.id
    )

    if (
        callback.from_user.id
        != auction.get("host_id")
        and member.status not in [
            "creator",
            "administrator"
        ]
    ):

        await callback.answer(
            "❌ Only the auction host or a group admin can do this.",
            show_alert=True
        )

        return

    #===== ALREADY ENDED =====

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await callback.answer(
            "❌ This auction has already ended.",
            show_alert=True
        )

        return

    #===== SAVE FULL RESTORE SNAPSHOT FIRST =====

    restore_saved = save_restore_snapshot(
        auction
    )

    if not restore_saved:

        await callback.answer(
            "❌ Could not save restore data.",
            show_alert=True
        )

        return

    #===== END AUCTION =====

    auction["status"] = "ENDED"

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

    #===== EDIT END MESSAGE =====

    await callback.message.edit_text(
        "🏁 <b>Auction Ended</b>\n\n"
        f"🆔 Auction ID : "
        f"<code>{auction['auction_id']}</code>\n\n"
        "✅ This auction room is now closed.\n\n"
        "♻️ Restore available for <b>2 hours</b> "
        "using the Auction ID.\n\n"
        "You can create a new auction."
    )

    await callback.answer(
        "🏁 Auction ended."
    )

# ====== CANCEL END AUCTION ======

@router.callback_query(
    F.data == "cancel_end_auction"
)
async def cancel_end_auction(
    callback: CallbackQuery
):

    try:

        await callback.message.delete()

    except Exception as e:

        print(
            "CANCEL END MESSAGE ERROR:",
            e
        )

    await callback.answer(
        "❌ End auction cancelled."
    )


# ====== SETS HOME ======

@router.callback_query(
    F.data == "sets_home"
)
async def sets_home(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🏏 <b>IPL AUCTION</b>\n\n"
        "Browse Available Player Sets\n\n"
        "Select an auction type below.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📣 MEGA AUCTION",
                        callback_data="mega_auction"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🦁 LEGENDS AUCTION",
                        callback_data="legends_auction"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# ====== MEGA AUCTION SETS ======

@router.callback_query(
    F.data == "mega_auction"
)
async def mega_auction(
    callback: CallbackQuery
):

    buttons = [

        [
            InlineKeyboardButton(
                text="👑 Marquee",
                callback_data="set:marquee"
            )
        ],

        [
            InlineKeyboardButton(
                text="🎖️ Set 1",
                callback_data="set:set1"
            ),
            InlineKeyboardButton(
                text="🏅 Set 2",
                callback_data="set:set2"
            )
        ],

        [
            InlineKeyboardButton(
                text="🥇 Set 3",
                callback_data="set:set3"
            ),
            InlineKeyboardButton(
                text="🎗️ Set 4",
                callback_data="set:set4"
            )
        ],

        [
            InlineKeyboardButton(
                text="🏏 Batters",
                callback_data="set:batters"
            ),
            InlineKeyboardButton(
                text="🔥 All Rounders",
                callback_data="set:allrounders"
            )
        ],

        [
            InlineKeyboardButton(
                text="🥎 Fast Bowlers",
                callback_data="set:fastbowlers"
            ),
            InlineKeyboardButton(
                text="🎩 Spinners",
                callback_data="set:spinners"
            )
        ],

        [
            InlineKeyboardButton(
                text="🔓 UC Batters",
                callback_data="set:uncapped_batters"
            ),
            InlineKeyboardButton(
                text="🔓 UC All Rounders",
                callback_data="set:uncapped_allrounders"
            )
        ],

        [
            InlineKeyboardButton(
                text="🔓 UC Fast Bowlers",
                callback_data="set:uncapped_fastbowlers"
            ),
            InlineKeyboardButton(
                text="🔓 UC Spinners",
                callback_data="set:uncapped_spinners"
            )
        ],

        [
            InlineKeyboardButton(
                text="🔙 Back",
                callback_data="sets_home"
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await callback.message.edit_text(
        "🏏 <b>IPL MEGA AUCTION</b>\n\n"
        "Browse Available Player Sets\n\n"
        "Select a player set below.",
        reply_markup=keyboard
    )

    await callback.answer()


# ====== PLAYER SET ======

@router.callback_query(
    F.data.startswith("set:")
)
async def player_set(
    callback: CallbackQuery
):

    #===== SLOWDOWN CHECK =====

    if not set_button_allowed(
        callback.from_user.id
    ):

        await callback.answer(
            "⚠️ Please slow down."
        )

        return

    #===== GET SET NAME =====

    set_name = callback.data.split(
        ":",
        1
    )[1]

    await show_player_page(
        callback,
        set_name,
        0
    )

#===== SHOW PLAYER PAGE =====

async def show_player_page(
    callback: CallbackQuery,
    set_name: str,
    page: int
):

    #===== PLAYER SET FOLDER =====

    folder = os.path.join(
        DATA_FOLDER,
        "mega_auction_sets",
        "players_sets"
    )

    #===== PLAYER SET FILE =====

    file_path = os.path.join(
        folder,
        f"{set_name}.json"
    )

    #===== FILE CHECK =====

    if not os.path.exists(
        file_path
    ):

        print(
            "PLAYER SET NOT FOUND:",
            file_path
        )

        await callback.answer()

        await callback.message.answer(
            "❌ <b>Player set not found.</b>",
            parse_mode="HTML"
        )

        return

    #===== LOAD PLAYERS =====

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            players = json.load(file)

    except Exception as e:

        print(
            "PLAYER SET JSON ERROR:",
            repr(e)
        )

        await callback.answer()

        await callback.message.answer(
            "❌ <b>Could not load this player set.</b>",
            parse_mode="HTML"
        )

        return

    #===== VALIDATE JSON =====

    if not isinstance(
        players,
        list
    ):

        print(
            "PLAYER SET IS NOT A LIST:",
            set_name
        )

        await callback.answer()

        await callback.message.answer(
            "❌ <b>Invalid player set format.</b>",
            parse_mode="HTML"
        )

        return

    #===== PAGINATION =====

    per_page = 20

    total_players = len(
        players
    )

    total_pages = max(
        1,
        (
            total_players
            + per_page
            - 1
        ) // per_page
    )

    page = max(
        0,
        min(
            page,
            total_pages - 1
        )
    )

    start = page * per_page

    end = start + per_page

    page_players = players[
        start:end
    ]

    #===== BUILD TEXT =====

    text = (
        f"🏏 <b>"
        f"{set_name.replace('_', ' ').title()}"
        f"</b>\n\n"
        "<b>SI | PLAYER NAME | BASE PRICE</b>\n\n"
    )

    #===== PLAYER ROWS =====

    for index, player in enumerate(
        page_players,
        start=start + 1
    ):

        try:

            player_id = player.get(
                "id",
                "-"
            )

            name = str(
                player.get(
                    "name",
                    "Unknown"
                )
            )

            price = player.get(
                "base_price",
                0
            )

            #===== PRICE VALIDATION =====

            try:

                price = float(
                    price
                )

            except (
                TypeError,
                ValueError
            ):

                print(
                    "INVALID PRICE:",
                    set_name,
                    name,
                    repr(price)
                )

                price = 0.0

            #===== OVERSEAS =====

            if player.get(
                "overseas",
                False
            ):

                name += " [OS]"

            #===== PLAYER ROW =====

            text += (
                f"{index} | "
                f"<b><i>{name}</i></b> "
                f"[<code>{player_id}</code>] | "
                f"<b>₹{price:.2f} Cr</b>\n\n"
            )

        except Exception as e:

            print(
                "PLAYER ROW ERROR:",
                set_name,
                index,
                repr(e)
            )

    #===== TOTAL PLAYERS =====

    text += (
        f"\n<b>Total Players: "
        f"{total_players}</b>"
    )

    #===== NAVIGATION =====

    navigation = []

    #===== PREVIOUS =====

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=(
                    f"players:"
                    f"{set_name}:"
                    f"{page - 1}"
                )
            )
        )

    #===== PAGE INFO =====

    navigation.append(
        InlineKeyboardButton(
            text=(
                f"Page "
                f"{page + 1}/"
                f"{total_pages}"
            ),
            callback_data="page_info"
        )
    )

    #===== NEXT =====

    if page < total_pages - 1:

        navigation.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=(
                    f"players:"
                    f"{set_name}:"
                    f"{page + 1}"
                )
            )
        )

    #===== KEYBOARD =====

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            navigation,
            [
                InlineKeyboardButton(
                    text="🔙 Back to Sets",
                    callback_data="mega_auction"
                )
            ]
        ]
    )

    #===== SHOW PAGE =====

    try:

        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )

        await callback.answer()

    except Exception as e:

        print(
            "PLAYER PAGE DISPLAY ERROR:",
            repr(e)
        )

        await callback.answer()

        await callback.message.answer(
            "❌ <b>Could not display this player set.</b>",
            parse_mode="HTML"
        )
    
    
# ====== PLAYER PAGE CALLBACK ======

@router.callback_query(
    F.data.startswith("players:")
)
async def player_page(
    callback: CallbackQuery
):

    #===== SLOWDOWN CHECK =====

    if not set_button_allowed(
        callback.from_user.id
    ):

        await callback.answer(
            "⚠️ Please slow down."
        )

        return

    #===== READ CALLBACK DATA =====

    parts = callback.data.split(
        ":"
    )

    if len(parts) != 3:

        await callback.answer(
            "❌ Invalid page.",
            show_alert=True
        )

        return

    set_name = parts[1]

    #===== PAGE NUMBER =====

    try:

        page = int(
            parts[2]
        )

    except ValueError:

        await callback.answer(
            "❌ Invalid page.",
            show_alert=True
        )

        return

    #===== SHOW PAGE =====

    await show_player_page(
        callback,
        set_name,
        page
    )
# ====== PAGE INFO ======

@router.callback_query(
    F.data == "page_info"
)
async def page_info(
    callback: CallbackQuery
):

    await callback.answer()



#===== AUCTION POOL CALLBACK =====

@router.callback_query(F.data.startswith("aucpool:"))
async def auction_pool_callback(callback: CallbackQuery):

    #===== COOLDOWN =====

    user_id = callback.from_user.id
    current_time = time.time()

    last_time = AUCPOOL_COOLDOWNS.get(user_id, 0)

    if current_time - last_time < AUCPOOL_COOLDOWN:

        await callback.answer(
            "⏳ Please wait a moment...",
            show_alert=False
        )
        return

    AUCPOOL_COOLDOWNS[user_id] = current_time

    action = callback.data.split(":", 1)[1]

    #===== NO OPERATION =====

    if action == "noop":

        await callback.answer()
        return

    #===== PAGE INDICATOR =====

    if action == "page":

        await callback.answer(
            "📄 Use the arrows to change page.",
            show_alert=False
        )
        return

    #===== LOAD TOURNAMENT =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == callback.message.chat.id
            and item.get("status")
            not in ("ENDED", "CANCELLED")
        ):
            tournament = item
            break

    if not tournament:

        await callback.answer(
            "❌ Tournament no longer exists.",
            show_alert=True
        )
        return

    #===== REFRESH =====

    if action == "refresh":

        current_page = 0

        text, keyboard = build_auction_pool_page(
            tournament,
            current_page
        )

        try:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard
            )
        except Exception:
            pass

        await callback.answer(
            "🔄 Pool refreshed.",
            show_alert=False
        )
        return

    #===== PAGE NUMBER =====

    try:
        page = int(action)

    except (ValueError, TypeError):

        await callback.answer(
            "❌ Invalid page.",
            show_alert=False
        )
        return

    #===== BUILD PAGE =====

    text, keyboard = build_auction_pool_page(
        tournament,
        page
    )

    #===== EDIT SAME MESSAGE =====

    try:

        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )

    except Exception as e:

        if "message is not modified" not in str(e).lower():

            await callback.answer(
                "❌ Unable to update pool.",
                show_alert=False
            )
            return

    await callback.answer()
    
    
#===== NO PROFILE =====

@router.callback_query(F.data == "aucpool:no_profile")
async def aucpool_no_profile(callback: CallbackQuery):

    await callback.answer(
        "ℹ️ This user doesn't have a public Telegram username.",
        show_alert=True
    )
    
    
    
#===== END TOURNAMENT CALLBACK =====

@router.callback_query(F.data.startswith("endtour:"))
async def end_tournament_callback(callback: CallbackQuery):
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("❌ Invalid request.", show_alert=True)
        return

    action = parts[1]
    tournament_code = parts[2]

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None
    tournament_index = None

    for index, item in enumerate(tournaments):
        if item.get("code") == tournament_code:
            tournament = item
            tournament_index = index
            break

    if not tournament:
        await callback.answer(
            "❌ Tournament not found.",
            show_alert=True
        )
        return

    # Host only
    if tournament.get("host_id") != callback.from_user.id:
        await callback.answer(
            "❌ Only the Tournament Host can do this.",
            show_alert=True
        )
        return

    # Cancel confirmation
    if action == "cancel":
        await callback.message.edit_text(
            "❎ <b>Tournament ending cancelled.</b>\n\n"
            f"🏆 {tournament['name']}"
        )
        await callback.answer()
        return

    # Confirm ending
    if action == "confirm":

        if tournament.get("status") != "REGISTRATION_ENDED":
            await callback.answer(
                "❌ Tournament is no longer ready to end.",
                show_alert=True
            )
            return

        tournament["status"] = "ENDED"

        tournaments[tournament_index] = tournament
        save_json(TOURNAMENTS_FILE, tournaments)

        await callback.message.edit_text(
            "🔒 <b>TOURNAMENT ENDED</b>\n\n"
            f"🏆 Tournament : <b>{tournament['name']}</b>\n"
            f"🔑 Code : <code>{tournament['code']}</code>\n"
            f"👥 Players : <b>{len(tournament.get('players', []))}</b>\n\n"
            "📦 Tournament data has been preserved.\n"
            "🚫 Registration and player management are now closed."
        )

        await callback.answer("🏆 Tournament ended.")
        return

    await callback.answer(
        "❌ Unknown action.",
        show_alert=True
    )
        
    

    
#===== TOURNAMENT SETS CALLBACK =====

@router.callback_query(F.data.startswith("tourset:"))
async def tournament_sets_callback(callback: CallbackQuery):

    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer(
            "❌ Invalid request.",
            show_alert=True
        )
        return

    action = parts[1]
    tour_code = parts[2]

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []

    # Find ONLY this group's tournament
    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == callback.message.chat.id
            and item.get("code") == tour_code
            and item.get("sets_converted") is True
        ):
            tournament = item
            break

    if not tournament:
        await callback.answer(
            "❌ Tournament sets not found.",
            show_alert=True
        )
        return

    # Find tournament folder
    tour_folder = os.path.join(
        TOURSETS_FOLDER,
        str(tour_code)
    )

    if not os.path.exists(tour_folder):
        await callback.answer(
            "❌ Tournament sets folder not found.",
            show_alert=True
        )
        return

    # Get sets
    set_files = []

    for filename in os.listdir(tour_folder):

        if (
            filename.startswith("set")
            and filename.endswith(".json")
        ):
            set_files.append(filename)

    set_files.sort(
        key=lambda x: int(
            x[3:-5]
        )
    )

    if not set_files:
        await callback.answer(
            "❌ No sets available.",
            show_alert=True
        )
        return

    # Current page
    if action == "refresh":
        page = 0

    else:
        try:
            page = int(action)
        except ValueError:
            await callback.answer(
                "❌ Invalid page.",
                show_alert=True
            )
            return

    total_pages = len(set_files)

    if page < 0:
        page = 0

    if page >= total_pages:
        page = total_pages - 1

    # Load selected set
    selected_file = set_files[page]

    set_data = load_json(
        os.path.join(
            tour_folder,
            selected_file
        )
    )

    if not isinstance(set_data, dict):
        await callback.answer(
            "❌ Invalid set file.",
            show_alert=True
        )
        return

    players = set_data.get(
        "players",
        []
    )

    set_number = set_data.get(
        "set_number",
        page + 1
    )

    text = (
        "🏆 <b>TOURNAMENT SETS</b>\n\n"
        f"🔑 Code : <code>{tour_code}</code>\n"
        f"📦 <b>Set {set_number}</b>\n"
        f"👥 Players : <b>{len(players)}</b>\n\n"
    )

    for index, player in enumerate(
        players,
        start=1
    ):

        if isinstance(player, dict):

            name = player.get(
                "first_name"
            ) or player.get(
                "name"
            ) or "Unknown"

            text += (
                f"{index}. {name}\n"
            )

        else:
            text += (
                f"{index}. {player}\n"
            )

    # Navigation
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙",
                    callback_data=(
                        f"tourset:{page - 1}:{tour_code}"
                        if page > 0
                        else f"tourset:{page}:{tour_code}"
                    )
                ),
                InlineKeyboardButton(
                    text=f"{page + 1} / {total_pages}",
                    callback_data=(
                        f"tourset:{page}:{tour_code}"
                    )
                ),
                InlineKeyboardButton(
                    text="🔜",
                    callback_data=(
                        f"tourset:{page + 1}:{tour_code}"
                        if page < total_pages - 1
                        else f"tourset:{page}:{tour_code}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔃 Refresh",
                    callback_data=(
                        f"tourset:refresh:{tour_code}"
                    )
                )
            ]
        ]
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise

    await callback.answer()
    
                    
#===== TOURNAMENT SQUAD SIZE CALLBACK =====

@router.callback_query(
    F.data.startswith("tourlimit:size:")
)
async def tournament_squad_size_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    squad_size = int(
        callback.data.split(":")[-1]
    )


    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []


    #===== FIND THIS GROUP TOURNAMENT =====

    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == callback.message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await callback.answer(
            "❌ Tournament not found.",
            show_alert=True
        )

        return


    #===== HOST ONLY =====

    if callback.from_user.id != tournament.get(
        "host_id"
    ):

        await callback.answer(
            "❌ Only the Tournament Host can do this.",
            show_alert=True
        )

        return


    #===== AUCTION LOCK =====

    if tournament.get("auction_started") is True:

        await callback.answer(
            "❌ Auction already started.",
            show_alert=True
        )

        return


    #===== SAVE SELECTED SIZE TEMPORARILY =====

    await state.update_data(
        squad_size=squad_size
    )


    #===== ASK BASE PRICE =====

    await callback.message.edit_text(
        "🏆 <b>TOURNAMENT SET LIMITS</b>\n\n"
        f"👥 Squad Size : <b>{squad_size}</b>\n\n"
        "💰 <b>Enter base price for all players</b>\n\n"
        "Enter amount in <b>Lakhs</b>.\n"
        "Example: <code>50</code>"
    )

    await state.set_state(
        TournamentSetLimitState.waiting_base_price
    )

    await callback.answer()
    
                    
#===== TOURNAMENT CUSTOM SIZE =====

@router.callback_query(
    F.data == "tourlimit:custom"
)
async def tournament_custom_size_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.message.edit_text(
        "🏆 <b>TOURNAMENT SET LIMITS</b>\n\n"
        "👥 <b>Enter Custom Squad Size</b>\n\n"
        "Example: <code>12</code>"
    )

    await state.set_state(
        TournamentSetLimitState.waiting_custom_size
    )

    await callback.answer()
    
#===== CUSTOM SQUAD SIZE INPUT =====

@router.message(
    TournamentSetLimitState.waiting_custom_size
)
async def tournament_custom_size_input(
    message: Message,
    state: FSMContext
):

    #===== HOST CHECK =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []


    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await state.clear()

        await message.reply(
            "❌ Tournament not found."
        )

        return


    if message.from_user.id != tournament.get(
        "host_id"
    ):

        await state.clear()

        await message.reply(
            "❌ Only the Tournament Host can do this."
        )

        return


    #===== VALIDATE SIZE =====

    try:

        squad_size = int(
            message.text.strip()
        )

    except:

        await message.reply(
            "❌ Please enter a valid whole number."
        )

        return


    if squad_size < 1:

        await message.reply(
            "❌ Squad size must be at least 1."
        )

        return


    #===== SAVE TEMPORARY SIZE =====

    await state.update_data(
        squad_size=squad_size
    )


    #===== ASK BASE PRICE =====

    await message.reply(
        "💰 <b>BASE PRICE</b>\n\n"
        f"👥 Squad Size : <b>{squad_size}</b>\n\n"
        "Enter base price for all players "
        "in <b>Lakhs</b>.\n\n"
        "Example: <code>50</code>"
    )

    await state.set_state(
        TournamentSetLimitState.waiting_base_price
    )
    
#===== CUSTOM SQUAD SIZE INPUT =====

@router.message(
    TournamentSetLimitState.waiting_custom_size
)
async def tournament_custom_size_input(
    message: Message,
    state: FSMContext
):

    #===== HOST CHECK =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []


    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await state.clear()

        await message.reply(
            "❌ Tournament not found."
        )

        return


    if message.from_user.id != tournament.get(
        "host_id"
    ):

        await state.clear()

        await message.reply(
            "❌ Only the Tournament Host can do this."
        )

        return


    #===== VALIDATE SIZE =====

    try:

        squad_size = int(
            message.text.strip()
        )

    except:

        await message.reply(
            "❌ Please enter a valid whole number."
        )

        return


    if squad_size < 1:

        await message.reply(
            "❌ Squad size must be at least 1."
        )

        return


    #===== SAVE TEMPORARY SIZE =====

    await state.update_data(
        squad_size=squad_size
    )


    #===== ASK BASE PRICE =====

    await message.reply(
        "💰 <b>BASE PRICE</b>\n\n"
        f"👥 Squad Size : <b>{squad_size}</b>\n\n"
        "Enter base price for all players "
        "in <b>Lakhs</b>.\n\n"
        "Example: <code>50</code>"
    )

    await state.set_state(
        TournamentSetLimitState.waiting_base_price
    )
    
                                                                                                                                                                                                                                                                                                                            
#===== TOURNAMENT BASE PRICE INPUT =====

@router.message(
    TournamentSetLimitState.waiting_base_price
)
async def tournament_base_price_input(
    message: Message,
    state: FSMContext
):

    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []


    #===== FIND TOURNAMENT =====

    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await state.clear()

        await message.reply(
            "❌ Tournament not found."
        )

        return


    #===== HOST ONLY =====

    if message.from_user.id != tournament.get(
        "host_id"
    ):

        await state.clear()

        await message.reply(
            "❌ Only the Tournament Host can do this."
        )

        return


    #===== AUCTION LOCK =====

    if tournament.get("auction_started") is True:

        await state.clear()

        await message.reply(
            "❌ Tournament auction has already started."
        )

        return


    #===== GET TEMPORARY DATA =====

    data = await state.get_data()

    squad_size = data.get(
        "squad_size"
    )


    if squad_size is None:

        await state.clear()

        await message.reply(
            "❌ Squad size was not selected."
        )

        return


    #===== VALIDATE BASE PRICE =====

    try:

        base_price = float(
            message.text.strip()
        )

    except:

        await message.reply(
            "❌ Please enter a valid number in Lakhs."
        )

        return


    if base_price <= 0:

        await message.reply(
            "❌ Base price must be greater than 0."
        )

        return


    #===== SAVE LIMITS =====

    tournament["squad_size"] = squad_size

    tournament["base_price_lakhs"] = base_price

    tournament["limits_configured"] = True


    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    #===== CLEAR FSM =====

    await state.clear()


    #===== SUCCESS =====

    await message.reply(
        "✅ <b>TOURNAMENT LIMITS SAVED</b>\n\n"
        f"👥 Squad Size : <b>{squad_size}</b>\n"
        f"💰 Base Price : <b>₹{base_price:g} Lakhs</b>\n\n"
        "🔓 You can change these limits again "
        "using <code>/setlimits</code> "
        "before the auction starts."
    )
    
                                                                                        
#===== TOURNAMENT LIMITS SAVE =====

@router.callback_query(
    F.data == "tourlimit:save"
)
async def tournament_limits_save_callback(
    callback: CallbackQuery
):

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []


    tournament = None

    for item in tournaments:

        if (
            item.get("chat_id") == callback.message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await callback.answer(
            "❌ Tournament not found.",
            show_alert=True
        )

        return


    #===== HOST ONLY =====

    if callback.from_user.id != tournament.get(
        "host_id"
    ):

        await callback.answer(
            "❌ Only the Tournament Host can save.",
            show_alert=True
        )

        return


    #===== CHECK CONFIGURATION =====

    if not tournament.get(
        "squad_size"
    ):

        await callback.answer(
            "❌ Squad size not configured.",
            show_alert=True
        )

        return


    if not tournament.get(
        "base_price_lakhs"
    ):

        await callback.answer(
            "❌ Base price not configured.",
            show_alert=True
        )

        return


    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    await callback.message.edit_text(
        "✅ <b>TOURNAMENT LIMITS SAVED</b>\n\n"
        f"👥 Squad Size : "
        f"<b>{tournament['squad_size']}</b>\n"
        f"💰 Base Price : "
        f"<b>₹{tournament['base_price_lakhs']:g} Lakhs</b>\n\n"
        "🏆 Tournament is ready for the next stage."
    )

    await callback.answer(
        "✅ Saved."
    )
    
#===== TOURNAMENT AUCTION CALLBACKS =====

@router.callback_query(
    F.data.startswith("tourauction:")
    & ~F.data.startswith("tourauction:start:")
)

async def tournament_auction_callback(
    callback: CallbackQuery
):

    parts = callback.data.split(":")

    if len(parts) < 3:
        await callback.answer()
        return

    action = parts[1]
    tour_code = parts[2]

    #----- LOAD TOURNAMENTS -----

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []

    #----- FIND TOURNAMENT -----

    tournament = None

    for item in tournaments:

        if item.get("code") == tour_code:

            tournament = item
            break

    if not tournament:

        await callback.answer(
            "Tournament not found.",
            show_alert=True
        )
        return

    #----- HOST ONLY -----

    if callback.from_user.id != tournament.get(
        "host_id"
    ):

        await callback.answer(
            "Only the Tournament Host can use this.",
            show_alert=True
        )
        return

    #----- SELECT SET -----

    if action == "set":

        tour_folder = os.path.join(
            TOURSETS_FOLDER,
            tour_code
        )

        set_files = []

        if os.path.exists(tour_folder):

            for filename in os.listdir(
                tour_folder
            ):

                if (
                    filename.startswith("set")
                    and filename.endswith(".json")
                ):
                    set_files.append(filename)

        set_files.sort(
            key=lambda x: int(x[3:-5])
        )

        if not set_files:

            await callback.answer(
                "No tournament sets found.",
                show_alert=True
            )
            return

        buttons = []

        for filename in set_files:

            set_number = int(
                filename[3:-5]
            )

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📦 Set {set_number}",
                        callback_data=(
                            f"tourauction:choose:{tour_code}:{set_number}"
                        )
                    )
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔙 Back",
                    callback_data=(
                        f"tourauction:back:{tour_code}"
                    )
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons
        )

        await callback.message.edit_text(

            "📦 <b>SELECT TOURNAMENT SET</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏆 Tournament : <b>{tournament.get('name')}</b>\n"
            f"🔑 Code : <code>{tour_code}</code>\n\n"
            "Select the player set to auction:",

            reply_markup=keyboard
        )

        await callback.answer()
        return

    #----- CHOOSE SET -----

    if action == "choose":

        if len(parts) < 4:
            await callback.answer()
            return

        set_number = int(parts[3])

        if "auction_setup" not in tournament:
            tournament["auction_setup"] = {}

        tournament["auction_setup"][
            "selected_set"
        ] = set_number

        save_json(
            TOURNAMENTS_FILE
            
        )

        await callback.answer(
            f"Set {set_number} selected."
        )

        # Rebuild setup screen

        squad_size = tournament.get(
            "squad_size"
        )

        base_price = tournament.get(
            "base_price"
        )

        players = tournament.get(
            "players"
           
        )

        tour_folder = os.path.join(
            TOURSETS_FOLDER,
            tour_code
        )

        set_files = []

        if os.path.exists(tour_folder):

            for filename in os.listdir(
                tour_folder
            ):

                if (
                    filename.startswith("set")
                    and filename.endswith(".json")
                ):
                    set_files.append(filename)

        set_files.sort(
            key=lambda x: int(x[3:-5])
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="📦 Select Set",
                        callback_data=(
                            f"tourauction:set:{tour_code}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="⚙️ Auction Settings",
                        callback_data=(
                            f"tourauction:settings:{tour_code}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="▶️ Start Auction",
                        callback_data=(
                            f"tourauction:start:{tour_code}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data=(
                            f"tourauction:cancel:{tour_code}"
                        )
                    )
                ]

            ]
        )

        await callback.message.edit_text(

            "🏆 <b>TOURNAMENT AUCTION SETUP</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            f"🔑 Code : <code>{tour_code}</code>\n"
            f"👥 Squad Size : <b>{squad_size}</b>\n"
            f"💰 Base Price : <b>₹{base_price} Lakhs</b>\n"
            f"👤 Players : <b>{len(players)}</b>\n"
            f"📦 Player Sets : <b>{len(set_files)}</b>\n\n"

            f"📌 <b>Selected Set : {set_number}</b>\n\n"

            "Choose an option below:",

            reply_markup=keyboard
        )

        return

    #----- BACK -----

    if action == "back":

        await callback.message.delete()

        # Re-run the setup command logic
        # by sending the same command internally.

        await callback.message.answer(
            "Use <code>/tourauction</code> to reopen the auction setup."
        )

        await callback.answer()
        return

    #----- AUCTION SETTINGS -----

    if action == "settings":

        squad_size = tournament.get(
            "squad_size"
        )

        base_price = tournament.get(
            "base_price"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="👥 Change Squad Size",
                        callback_data=(
                            f"tourauction:limits:{tour_code}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="💰 Change Base Price",
                        callback_data=(
                            f"tourauction:price:{tour_code}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔙 Back",
                        callback_data=(
                            f"tourauction:back:{tour_code}"
                        )
                    )
                ]

            ]
        )

        await callback.message.edit_text(

            "⚙️ <b>AUCTION SETTINGS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            f"👥 Squad Size : <b>{squad_size}</b>\n"
            f"💰 Base Price : <b>₹{base_price} Lakhs</b>\n\n"

            "Tournament settings can be edited before "
            "the auction starts.",

            reply_markup=keyboard
        )

        await callback.answer()
        return

    

    #----- CANCEL -----

    if action == "cancel":

        if tournament.get(
            "auction_setup"
        ):

            tournament[
                "auction_setup"
            ]["status"] = "CANCELLED"

        save_json(
            TOURNAMENTS_FILE,
            
        )

        await callback.message.edit_text(

            "❌ <b>TOURNAMENT AUCTION CANCELLED</b>\n\n"
            f"🏆 Tournament : <b>{tournament.get('name')}</b>\n"
            f"🔑 Code : <code>{tour_code}</code>\n\n"
            "The tournament itself is still available."
        )

        await callback.answer()
        return                                                                                                                                                                                                                                                    #===== TOURNAMENT AUCTION START =====

@router.callback_query(
    F.data.startswith("tourauction:start:")
)
async def tournament_auction_start_callback(
    callback: CallbackQuery
):
    try:

        chat_id = callback.message.chat.id

        #===== GET TOURNAMENT CODE =====
        tour_code = callback.data.split(
            ":",
            2
        )[2]

        #===== LOAD TOURNAMENTS =====
        with open(
            TOURNAMENTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            tournaments = json.load(file)

        if not isinstance(
            tournaments,
            list
        ):
            tournaments = []

        tournament = None
        tournament_index = None

        #===== FIND TOURNAMENT =====
        for index, tour in enumerate(
            tournaments
        ):
            if (
                tour.get("chat_id")
                == chat_id
                and tour.get("code")
                == tour_code
            ):
                tournament = tour
                tournament_index = index
                break

        if not tournament:
            await callback.answer(
                "❌ Tournament not found.",
                show_alert=True
            )
            return


        #===== HOST CHECK =====

        if (
            callback.from_user.id
            != tournament.get("host_id")
        ):

            await callback.answer(
                "❌ Only the tournament host can start the auction.",
                show_alert=True
            )

            return


        #===== STATUS CHECK =====

        if (
            tournament.get("status")
            != "REGISTRATION_ENDED"
        ):

            await callback.answer(
                "❌ Tournament is not ready for auction.",
                show_alert=True
            )

            return


        #===== AUCTION SETUP =====

        setup = tournament.get(
            "auction_setup",
            {}
        )


        if (
            setup.get("status")
            != "SETUP"
        ):

            await callback.answer(
                "❌ Auction setup is not ready.",
                show_alert=True
            )

            return


        selected_set = int(
            setup.get(
                "selected_set",
                1
            )
        )


        squad_size = tournament.get(
            "squad_size",
            setup.get("squad_size")
        )


        base_price = tournament.get(
            "base_price_lakhs",
            setup.get("base_price")
        )


        if (
            squad_size is None
            or base_price is None
        ):

            await callback.answer(
                "❌ Auction limits are not configured.",
                show_alert=True
            )

            return


        #===== TEAM CHECK =====

        teams = tournament.get(
            "teams"            
        )


        if not teams:

            await callback.answer(
                "❌ No tournament teams found.",
                show_alert=True
            )

            return


        #===== PURSE CHECK =====

        for team in teams:

            purse_lakhs = float(
                team.get(
                    "purse_lakhs",
                    team.get(
                        "purse",
                        0
                    )
                )
            )


            if purse_lakhs <= 0:

                code = team.get(
                    "short_code",
                    team.get(
                        "code",
                        "UNKNOWN"
                    )
                )


                await callback.answer(
                    f"❌ Team {code} has no purse.",
                    show_alert=True
                )

                return


        #===== SET FILE =====

        set_file = os.path.join(
            TOURSETS_FOLDER,
            tour_code,
            f"set{selected_set}.json"
        )


        if not os.path.exists(
            set_file
        ):

            await callback.answer(
                f"❌ Set {selected_set} not found.",
                show_alert=True
            )

            return


        #===== LOAD PLAYERS =====

        with open(
            set_file,
            "r",
            encoding="utf-8"
        ) as file:
            players = json.load(file)


            if isinstance(
                players,
                dict
            ):

                players = players.get(
                    "players",
                
                )


        if not players:

            await callback.answer(
                "❌ Selected player set is empty.",
                show_alert=True
            )

            return


        #===== GET FIRST PLAYER =====

        first_player = players[0]


        player_name = (
            first_player.get("name")
            or first_player.get("display_name")
            or first_player.get("first_name")
            or first_player.get("player_name")
            or "Unknown Player"
        )


        #===== START AUCTION =====

        tournament["status"] = (
            "AUCTION_RUNNING"
        )


        tournament["auction_setup"] = {

            "status": "RUNNING",

            "selected_set": selected_set,

            "squad_size": squad_size,

            "base_price": base_price,

            "current_player_index": 0,

            "players": players,

            "current_player": first_player,

            "current_bid_lakhs": float(
                base_price
            ),

            "leading_team": None,

            "leading_manager_id": None,

            "timer": 20

        }


        #===== SAVE BEFORE MESSAGE =====

        tournaments[
            tournament_index
        ] = tournament


        save_json(
            TOURNAMENTS_FILE,
            tournaments
        )


        #===== AUCTION MESSAGE =====

        text = (

            "🏆 <b>TOURNAMENT AUCTION STARTED!</b>\n"

            "━━━━━━━━━━━━━━━━━━━━\n\n"

            f"📦 Set : <b>{selected_set}</b>\n"

            f"👤 Player : <b>{player_name}</b>\n"

            f"💰 Base Price : "
            f"<b>₹{float(base_price):g} Lakhs</b>\n\n"

            "🔨 <b>Current Bid</b>\n"

            f"₹{float(base_price):g} Lakhs\n\n"

            "⏳ Timer : <b>20 sec</b>\n"

            "👑 Leading Team : <b>None</b>"

        )


        #===== EDIT AUCTION MESSAGE =====

        await callback.message.edit_text(
            text,
            parse_mode="HTML"
        )


        #===== SAVE AUCTION MESSAGE ID =====

        tournament["auction_setup"][
            "auction_message_id"
        ] = callback.message.message_id


        #===== UPDATE TOURNAMENT LIST =====

        tournaments[
            tournament_index
        ] = tournament


        #===== SAVE MESSAGE ID =====

        save_json(
            TOURNAMENTS_FILE,
            tournaments
        )


        #===== START TOURNAMENT TIMER =====

        start_player_timer(
            callback.bot,
            chat_id
        )

        #===== SUCCESS =====

        await callback.answer(
            "✅ Auction started!"
        )


    except Exception as e:
        import traceback

        print(
            "🔥🔥🔥 TOURNAMENT AUCTION START ERROR"
        )

        traceback.print_exc()

            
            
            
            
            
            
            