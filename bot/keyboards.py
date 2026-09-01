# ====== IMPORTS ======

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== CONFIG ======

BOT_USERNAME = "ipl_auctionbot"
DEVELOPER_USERNAME = "jilan97"

# ====== START KEYBOARD ======

start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Add to Group to Play",
                url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton(
                text="📩 Contact Developer",
                url=f"https://t.me/{DEVELOPER_USERNAME}"
            )
        ]
    ]
)

# ====== AUCTION KEYBOARD ======

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

auction_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ 5L",
                callback_data="bid_5"
            ),
            InlineKeyboardButton(
                text="➕ 10L",
                callback_data="bid_10"
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ 20L",
                callback_data="bid_20"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭ SKIP",
                callback_data="skip"
            )
        ]
    ]
)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ===== IPL AUCTION MENU =====

sets_home_keyboard = InlineKeyboardMarkup(
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

#======= DM BUTTON=====

check_dm_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📩 Check DM",
                url="https://t.me/ipl_auctionbot"
            )
        ]
    ]
)


# ====== GROUP START AUCTION KEYBOARD ======

group_start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📣 MEGA AUCTION",
                callback_data="start_mega_auction"
            )
        ],
        [
            InlineKeyboardButton(
                text="🦁 LEGENDS AUCTION",
                callback_data="start_legends_auction"
            )
        ]
    ]
)