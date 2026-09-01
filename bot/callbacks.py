# ====== IMPORTS ======

import os
import json

from aiogram import Router, F

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import DATA_FOLDER

from auction.manager import (
    create_auction,
    get_auction,
    save_auction,
    set_chat_context,
    save_restore_snapshot,
)

from bot.keyboards import (
    auction_keyboard,
    group_start_keyboard,
)


# ====== ROUTER ======

router = Router()


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

    set_name = callback.data.split(
        ":",
        1
    )[1]

    await show_player_page(
        callback,
        set_name,
        0
    )


# ====== SHOW PLAYER PAGE ======

async def show_player_page(
    callback: CallbackQuery,
    set_name: str,
    page: int
):

    folder = os.path.join(
        DATA_FOLDER,
        "mega_auction_sets",
        "players_sets"
    )

    file_path = os.path.join(
        folder,
        f"{set_name}.json"
    )

    # =========================
    # FILE CHECK
    # =========================

    if not os.path.exists(file_path):

        await callback.answer(
            "❌ Player set not found.",
            show_alert=True
        )

        return

    # =========================
    # LOAD PLAYERS
    # =========================

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            players = json.load(file)

    except Exception as e:

        print(
            "PLAYER SET ERROR:",
            e
        )

        await callback.answer(
            "❌ Could not load this player set.",
            show_alert=True
        )

        return

    # =========================
    # PAGINATION
    # =========================

    per_page = 20

    total_players = len(players)

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

    # =========================
    # BUILD TEXT
    # =========================

    text = (
        f"🏏 <b>"
        f"{set_name.replace('_', ' ').title()}"
        f"</b>\n\n"
        "<b>SI | PLAYER NAME | BASE PRICE</b>\n\n"
    )

    for index, player in enumerate(
        page_players,
        start=start + 1
    ):

        player_id = player.get(
            "id",
            "-"
        )

        name = player.get(
            "name",
            "Unknown"
        )

        price = player.get(
            "base_price",
            0
        )

        if player.get(
            "overseas",
            False
        ):

            name += " [OS]"

        text += (
            f"{index} | "
            f"<b><i>{name}</i></b> "
            f"[<code>{player_id}</code>] | "
            f"<b>₹{float(price):.2f} Cr</b>\n\n"
        )

    text += (
        f"\n<b>Total Players: "
        f"{total_players}</b>"
    )

    # =========================
    # NAVIGATION
    # =========================

    navigation = []

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

    # =========================
    # SHOW PAGE
    # =========================

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


# ====== PLAYER PAGE CALLBACK ======

@router.callback_query(
    F.data.startswith("players:")
)
async def player_page(
    callback: CallbackQuery
):

    parts = callback.data.split(":")

    if len(parts) != 3:

        await callback.answer(
            "❌ Invalid page.",
            show_alert=True
        )

        return

    set_name = parts[1]

    try:

        page = int(parts[2])

    except ValueError:

        await callback.answer(
            "❌ Invalid page.",
            show_alert=True
        )

        return

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


# ====== OLD BID +5 BUTTON ======

@router.callback_query(
    F.data == "bid_5"
)
async def bid_5(
    callback: CallbackQuery
):

    await callback.answer(
        "Use /bid <amount> to bid."
    )


# ====== OLD BID +10 BUTTON ======

@router.callback_query(
    F.data == "bid_10"
)
async def bid_10(
    callback: CallbackQuery
):

    await callback.answer(
        "Use /bid <amount> to bid."
    )


# ====== OLD BID +20 BUTTON ======

@router.callback_query(
    F.data == "bid_20"
)
async def bid_20(
    callback: CallbackQuery
):

    await callback.answer(
        "Use /bid <amount> to bid."
    )


# ====== OLD SKIP BUTTON ======

@router.callback_query(
    F.data == "skip"
)
async def skip(
    callback: CallbackQuery
):

    await callback.answer(
        "⏭ Use the auction command system for bidding."
    )