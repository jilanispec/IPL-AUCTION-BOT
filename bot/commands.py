#===== IMPORTS =====

import os
import time
import asyncio
import time
import math

from aiogram import Router , F
from aiogram.filters import Command

from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

from utils.image_helper import prepare_player_image

from storage.json_manager import (
    load_json,
    save_json
)

from config import (
    AUCTION_FILE,
    DATA_FOLDER
)

from bot.keyboards import (
    start_keyboard,
    auction_keyboard,
    sets_home_keyboard,
    check_dm_keyboard,
    group_start_keyboard
)

from auction.manager import (
    create_auction,
    add_team,
    get_auction,
    save_auction,
    get_teams,
    remove_team,
    load_player_set,
    start_auction,
    manager_bid,
    set_chat_context,
    pause_auction,
    resume_auction,
    get_team_squad,
    set_squad_limits,
    apply_default_squad_limits,
    get_squad_limits,
    DEFAULT_MIN_SQUAD,
    DEFAULT_MAX_SQUAD,
    DEFAULT_OS_LIMIT,
    SQUAD_SETUP_TIMEOUT,
    PLAYER_SETS_FOLDER,

)

from utils.helpers import (
    is_admin,
    is_group
)

from auction.timer import (
    start_player_timer
)


#===== FILES =====

USERS_FILE = os.path.join(
    DATA_FOLDER,
    "users.json"
)

CHATS_FILE = os.path.join(
    DATA_FOLDER,
    "chats.json"
)


#===== ROUTER =====

router = Router()


#===== SAVE USER =====

def save_user(message: Message):

    users = load_json(
        USERS_FILE
    )

    if not isinstance(
        users,
        list
    ):
        users = []

    for user in users:

        if user.get(
            "user_id"
        ) == message.from_user.id:

            return

    users.append({

        "user_id":
            message.from_user.id,

        "username":
            message.from_user.username,

        "first_name":
            message.from_user.first_name
    })

    save_json(
        USERS_FILE,
        users
    )


#===== SAVE CHAT =====

def save_chat(message: Message):

    chats = load_json(
        CHATS_FILE
    )

    if not isinstance(
        chats,
        list
    ):
        chats = []

    for chat in chats:

        if chat.get(
            "chat_id"
        ) == message.chat.id:

            return

    chats.append({

        "chat_id":
            message.chat.id,

        "title":
            message.chat.title,

        "type":
            message.chat.type
    })

    save_json(
        CHATS_FILE,
        chats
    )


print("COMMANDS.PY LOADED")


#===== START =====

@router.message(
    Command("start")
)
async def start_command(
    message: Message
):

    save_chat(
        message
    )

    save_user(
        message
    )

    #===== GROUP START =====

    if is_group(
        message.chat.type
    ):

        await message.reply(

            "🏏 <b>IPL AUCTION</b>\n\n"

            "Start an Auction\n\n"

            "Choose an auction type below.",

            reply_markup=
                group_start_keyboard
        )

        return


    #===== PRIVATE START =====

    text = (

        "🏏 <b>IPL AUCTION BOT</b>\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "Welcome!\n\n"

        "Host and manage your own IPL-style\n"
        "auction in Telegram groups.\n\n"

        "👑 <b>Admin Features</b>\n"

        "• Create Auction\n"
        "• Manage Teams\n"
        "• Live Auction\n\n"

        "👇 <b>Get Started</b>"
    )


    await message.reply(

        text=text,

        reply_markup=
            start_keyboard
    )


#===== CREATE AUCTION =====

@router.message(
    Command("create_auction")
)
async def create_auction_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== ADMIN ONLY =====

    if not is_admin(
        message.from_user.id
    ):

        await message.reply(
            "❌ You are not authorized to use this command."
        )

        return


    #===== CREATE =====

    auction = create_auction(

        chat_id=
            message.chat.id,

        host_id=
            message.from_user.id,

        host_username=
            message.from_user.username
            or message.from_user.first_name
    )


    #===== ALREADY EXISTS =====

    if auction == "already_exists":

        await message.reply(
            "❌ An auction is already active in this group."
        )

        return


    #===== START SQUAD SETUP TIMER =====

    # Give the host a short window to configure
    # minimum/maximum squad size and overseas limit.
    start_squad_setup_timer(
        message.bot,
        message.chat.id
    )

    #===== SUCCESS =====

    await message.reply(

        "🏏 <b>Auction Created Successfully!</b>\n\n"

        f"🆔 Auction ID : "
        f"<code>{auction['auction_id']}</code>\n"

        f"👑 Host : "
        f"@{message.from_user.username or message.from_user.first_name}\n\n"

        "📣 Type : Mega Auction\n"

        "📌 Status : Waiting\n"

        "👤 Current Player : None\n"

        "💰 Current Bid : ₹0.00 Cr"
    )


#===== ADD TEAM =====

@router.message(
    Command("add_team")
)
async def add_team_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== GET THIS GROUP AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    if not auction:

        await message.reply(

            "❌ No auction has been created yet.\n\n"

            "Use <code>/start</code> → "
            "<b>MEGA AUCTION</b> → <b>Claim Host</b> first."
        )

        return


    #===== HOST ONLY =====

    if message.from_user.id != auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the auction host can add teams."
        )

        return


    #===== CHECK STATUS =====

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await message.reply(
            "❌ This auction has already ended."
        )

        return


    #===== COMMAND ARGUMENTS =====

    args = message.text.split()


    if len(args) != 4:

        await message.reply(

            "❌ Invalid Usage\n\n"

            "<code>/add_team TEAM_NAME PURSE @USERNAME</code>\n\n"

            "Example:\n"

            "<code>/add_team CSK 120 @csk_manager</code>"
        )

        return


    team_name = args[1]

    manager_username = args[3]


    #===== USERNAME CHECK =====

    if not manager_username.startswith(
        "@"
    ):

        await message.reply(
            "❌ Manager username must start with @"
        )

        return


    #===== PURSE =====

    try:

        purse = float(
            args[2]
        )

    except ValueError:

        await message.reply(
            "❌ Purse must be a number."
        )

        return


    if purse <= 0:

        await message.reply(
            "❌ Purse must be greater than 0."
        )

        return


    #===== FIND MANAGER =====

    manager_id = None

    users = load_json(
        USERS_FILE
    )

    if not isinstance(
        users,
        list
    ):

        users = []


    for user in users:

        username = user.get(
            "username"
        )

        if not username:
            continue

        if (
            f"@{username}".lower()
            ==
            manager_username.lower()
        ):

            manager_id = user.get(
                "user_id"
            )

            break


    #===== MANAGER NOT FOUND =====

    if manager_id is None:

        await message.reply(

            "❌ Manager not found.\n\n"

            f"Ask {manager_username} to send "
            "<code>/start</code> to the bot first."
        )

        return


#===== ADD TEAM =====

    result = add_team(
        team_name,
        purse,
        manager_username,
        manager_id
    )

    if not result:

        await message.reply(
            "❌ Team already exists or auction cannot accept teams."
        )

        return

    #===== SUCCESS =====

    await message.reply(

        "✅ <b>Team Added Successfully!</b>\n\n"

        f"🏏 Team : <b>{team_name}</b>\n"

        f"💰 Purse : ₹{purse:.2f} Cr\n"

        f"👤 Manager : {manager_username}\n"

        "👥 Players : 0"
    )


#===== LIST TEAMS =====

@router.message(
    Command("list_teams")
)
async def list_teams_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== GET THIS GROUP TEAMS =====

    teams = get_teams()
    


    if not teams:

        await message.reply(
            "📭 No teams have been added yet."
        )

        return


    #===== BUILD TEAM LIST =====

    text = (
        "🏏 <b>IPL Teams</b>\n"
        "━━━━━━━━━━━━━━\n\n"
    )


    for index, team in enumerate(
        teams,
        start=1
    ):

        players = team.get(
            "players",
            []
        )

        text += (

            f"{index}. <b>"
            f"{team.get('name', 'Unknown')}"
            f"</b>\n"

            f"💰 Purse : ₹"
            f"{float(team.get('purse', 0)):.2f} Cr\n"

            f"👤 Manager : "
            f"{team.get('manager_username', 'Not Assigned')}\n"

            f"👥 Players : "
            f"{len(players)}\n\n"
        )


    await message.reply(
        text
    )


#===== REMOVE TEAM =====

@router.message(
    Command("remove_team")
)
async def remove_team_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== ADMIN ONLY =====

    if not is_admin(
        message.from_user.id
    ):

        await message.reply(
            "❌ Only admins can use this command."
        )

        return


    #===== ARGUMENTS =====

    args = message.text.split()


    if len(args) != 2:

        await message.reply(

            "❌ Invalid Usage\n\n"

            "<code>/remove_team TEAM_NAME</code>\n\n"

            "Example:\n"

            "<code>/remove_team CSK</code>"
        )

        return


    team_name = args[1]


    #===== REMOVE =====

    result = remove_team(
        team_name
    )


    if result:

        await message.reply(

            f"✅ Team <b>{team_name}</b> "
            "removed successfully."
        )

    else:

        await message.reply(

            f"❌ Team <b>{team_name}</b> "
            "not found."
        )


#===== LOAD PLAYER SET =====

@router.message(
    Command("load_set")
)
async def load_set_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    #===== GET GROUP AUCTION =====

    auction = get_auction(
        message.chat.id
    )

    if not auction:

        await message.reply(

            "❌ No auction room exists.\n\n"

            "Use <code>/start</code> → "
            "<b>MEGA AUCTION</b> → "
            "<b>Claim Host</b> first."
        )

        return

    #===== HOST OR BOT OWNER =====

    if (
        message.from_user.id
        != auction.get("host_id")
        and not is_admin(
            message.from_user.id
        )
    ):

        await message.reply(

            "❌ Only the auction host or bot owner "
            "can load a player set."
        )

        return

    #===== CHECK RUNNING =====

    if auction.get(
        "status"
    ) == "RUNNING":

        await message.reply(

            "❌ A player is currently being auctioned.\n\n"

            "Wait until this player is SOLD/UNSOLD "
            "before loading another set."
        )

        return

    #===== CHECK ENDED =====

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await message.reply(
            "❌ This auction has already ended."
        )

        return

    #===== ARGUMENTS =====

    args = message.text.split()

    #===== SHOW AVAILABLE SETS =====

    if len(args) == 1:

        try:

            files = sorted(
                [
                    filename
                    for filename in os.listdir(
                        PLAYER_SETS_FOLDER
                    )
                    if filename.lower().endswith(
                        ".json"
                    )
                ],
                key=str.lower
            )

        except Exception as e:

            print(
                "PLAYER SET LIST ERROR:",
                e
            )

            await message.reply(
                "❌ Could not read player sets."
            )

            return

        if not files:

            await message.reply(
                "❌ No player sets found."
            )

            return

        sets_text = "\n".join(
            f"<code>{filename[:-5]}</code>"
            for filename in files
        )

        await message.reply(

            "📦 <b>Available Player Sets</b>\n\n"

            f"{sets_text}\n\n"

            "Use:\n"
            "<code>/load_set SET_NAME</code>"
        )

        return

    #===== INVALID ARGUMENTS =====

    if len(args) != 2:

        await message.reply(

            "❌ Invalid Usage\n\n"

            "Use:\n"
            "<code>/load_set SET_NAME</code>"
        )

        return

    #===== SET NAME =====

    set_name = args[1].strip().lower()

    if set_name.endswith(
        ".json"
    ):

        set_name = set_name[:-5]

    #===== LOAD SET =====

    result = load_player_set(

        set_name,

        message.chat.id
    )

    #===== RESULT: RUNNING =====

    if result == "auction_running":

        await message.reply(

            "❌ A player is currently being auctioned.\n\n"

            "Wait until this player is SOLD/UNSOLD "
            "before loading another set."
        )

        return

    #===== RESULT: NO AUCTION =====

    if result == "no_auction":

        await message.reply(
            "❌ No auction room exists."
        )

        return

    #===== RESULT: ENDED =====

    if result == "auction_ended":

        await message.reply(
            "❌ This auction has already ended."
        )

        return

    #===== RESULT: ALREADY LOADED =====

    if result == "set_already_loaded":

        await message.reply(

            f"❌ Player set "
            f"<b>{set_name}</b> is already loaded."
        )

        return

    #===== RESULT: NOT FOUND =====

    if result is False:

        await message.reply(

            f"❌ Player set "
            f"<b>{set_name}</b> not found."
        )

        return

    #===== SUCCESS =====

    await message.reply(

        "✅ <b>Player Set Loaded</b>\n\n"

        f"📦 Set : "
        f"<b>{set_name.replace('_', ' ').title()}</b>\n"

        f"👥 Players : <b>{result}</b>\n\n"

        "🎲 Player order has been randomized.\n\n"

        "Use <code>/start_auction</code> "
        "to begin."
    )


#===== LOAD SET BUTTON =====

@router.callback_query(
    F.data.startswith("loadset:")
)
async def load_set_button(
    callback: CallbackQuery
):

    set_name = callback.data.split(
        ":",
        1
    )[1]

    chat_id = callback.message.chat.id

    auction = get_auction(
        chat_id
    )

    if not auction:

        await callback.answer(
            "❌ No auction room exists.",
            show_alert=True
        )

        return

    if (
        callback.from_user.id
        != auction.get("host_id")
        and not is_admin(
            callback.from_user.id
        )
    ):

        await callback.answer(
            "❌ Only the auction host or bot owner can load a set.",
            show_alert=True
        )

        return

    result = load_player_set(
        set_name,
        chat_id
    )

    if result is False:

        await callback.answer(
            "❌ Player set not found.",
            show_alert=True
        )

        return

    if result == "set_already_loaded":

        await callback.answer(
            "❌ This set is already loaded.",
            show_alert=True
        )

        return

    if result == "auction_running":

        await callback.answer(
            "❌ Auction is currently running.",
            show_alert=True
        )

        return

    if result == "auction_ended":

        await callback.answer(
            "❌ This auction has ended.",
            show_alert=True
        )

        return

    await callback.answer(
        "✅ Player set loaded."
    )

    await callback.message.edit_text(

        "✅ <b>Player Set Loaded</b>\n\n"

        f"📦 Set : "
        f"<b>{set_name.replace('_', ' ').title()}</b>\n"

        f"👥 Players : <b>{result}</b>\n\n"

        "🎲 Player order has been randomized.\n\n"

        "Use <code>/start_auction</code> "
        "to begin."
    )
    
    
    
    

#===== SEND AUCTION PLAYER =====

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


    #===== COUNTRY =====

    if overseas:

        overseas_text = "🌍 Overseas"

    else:

        overseas_text = "🇮🇳 Indian"


    #===== PLAYER IMAGE =====

    image_path = prepare_player_image(

        player.get(
            "image"
        ),

        name,

        country,

        base_price
    )


    #===== CAPTION =====

    caption = (

        "🏏 <b>IPL MEGA AUCTION</b>\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 <b>{name}</b>\n\n"

        f"🆔 ID : <code>{player_id}</code>\n"

        f"🌎 Nationality : "
        f"<b>{country}</b>\n"

        f"{overseas_text}\n\n"

        f"💰 <b>Base Price : "
        f"₹{float(base_price):.2f} Cr</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Current Bid : "
        f"<b>₹"
        f"{float(auction.get('current_bid', 0)):.2f}"
        f" Cr</b>\n"

        "👥 Leading Team : "
        "<b>No Bids Yet</b>\n"

        f"⏳ Time Left : "
        f"<b>{auction.get('timer', 20)} sec</b>\n\n"

        "📢 <b>Managers can now bid.</b>"
    )


    #===== SEND PLAYER =====

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


    #===== SAVE MESSAGE =====

    auction["auction_message_id"] = (
        sent_message.message_id
    )

    auction["auction_chat_id"] = (
        chat_id
    )


    save_auction(
        auction
    )


    return sent_message


#===== START AUCTION =====

@router.message(
    Command("start_auction")
)
async def start_auction_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== GET GROUP AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    if not auction:

        await message.reply(

            "❌ No auction room exists.\n\n"

            "Claim a host and create an auction first."
        )

        return


    #===== HOST ONLY =====

    if message.from_user.id != auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the auction host can start the auction."
        )

        return


    #===== CHECK STATUS =====

    if auction.get(
        "status"
    ) == "RUNNING":

        await message.reply(
            "❌ Auction is already running."
        )

        return


    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await message.reply(
            "❌ This auction has already ended."
        )

        return


    #===== CHECK PLAYERS =====

    if not auction.get(
        "players"
    ):

        await message.reply(

            "❌ No player set loaded.\n\n"

            "Use <code>/load_set SET_NAME</code> first."
        )

        return


    #===== START PLAYER =====

    player = start_auction(
        message.chat.id
    )


    if player == "no_auction":

        await message.reply(
            "❌ No auction room exists."
        )

        return


    if player == "already_running":

        await message.reply(
            "❌ Auction is already running."
        )

        return


    if player == "no_players":

        await message.reply(
            "❌ No players available."
        )

        return


    #===== RELOAD AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    if not auction:

        await message.reply(
            "❌ Auction data could not be loaded."
        )

        return


    #===== SEND PLAYER =====

    await send_auction_player(

        message.bot,

        message.chat.id,

        player,

        auction
    )


    #===== START TIMER =====

    start_player_timer(

        message.bot,

        message.chat.id
    )


#===== UPDATE AUCTION MESSAGE =====

async def update_auction_message(
    bot,
    auction
):

    message_id = auction.get(
        "auction_message_id"
    )

    chat_id = auction.get(
        "auction_chat_id"
    )

    player = auction.get(
        "current_player"
    )


    if (
        not message_id
        or not chat_id
        or not player
    ):

        return


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


    #===== COUNTRY =====

    if overseas:

        overseas_text = "🌍 Overseas"

    else:

        overseas_text = "🇮🇳 Indian"


    #===== LEADING TEAM =====

    leading_team = auction.get(
        "leading_team"
    )


    if not leading_team:

        leading_team = "No Bids Yet"


    #===== CAPTION =====

    caption = (

        "🏏 <b>IPL MEGA AUCTION</b>\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 <b>{name}</b>\n\n"

        f"🆔 ID : <code>{player_id}</code>\n"

        f"🌎 Nationality : "
        f"<b>{country}</b>\n"

        f"{overseas_text}\n\n"

        f"💰 <b>Base Price : "
        f"₹{float(base_price):.2f} Cr</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Current Bid : "
        f"<b>₹"
        f"{float(auction.get('current_bid', 0)):.2f}"
        f" Cr</b>\n"

        f"👥 Leading Team : "
        f"<b>{leading_team}</b>\n"

        f"⏳ Time Left : "
        f"<b>{auction.get('timer', 0)} sec</b>\n\n"

        "📢 <b>Managers can now bid.</b>"
    )


    #===== EDIT MESSAGE =====

    try:

        await bot.edit_message_caption(

            chat_id=chat_id,

            message_id=message_id,

            caption=caption
        )

    except Exception as e:

        error_text = str(
            e
        )

        if "message is not modified" not in (
            error_text.lower()
        ):

            print(
                "AUCTION MESSAGE UPDATE ERROR:",
                e
            )


#===== BID =====

@router.message(
    Command("bid")
)
async def bid_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ Bidding is only available in groups."
        )

        return


    #===== GET GROUP AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    if not auction:

        await message.reply(
            "❌ No active auction."
        )

        return


    #===== CHECK RUNNING =====

    if auction.get(
        "status"
    ) != "RUNNING":

        await message.reply(
            "❌ Auction is not currently running."
        )

        return


    #===== CHECK TIMER =====

    if auction.get(
        "timer",
        0
    ) <= 0:

        await message.reply(
            "❌ Bidding time is over."
        )

        return


    #===== COMMAND ARGUMENTS =====

    args = message.text.split()


    if len(args) != 2:

        await message.reply(

            "❌ Invalid bid.\n\n"

            "Use:\n"

            "<code>/bid 2.50</code>"
        )

        return


    #===== BID AMOUNT =====

    try:

        bid_amount = float(
            args[1]
        )

    except ValueError:

        await message.reply(
            "❌ Bid amount must be a number."
        )

        return


    #===== MANAGER BID =====

    result = manager_bid(

        message.chat.id,

        message.from_user.id,

        bid_amount
    )


    #===== NO AUCTION =====

    if result == "no_auction":

        await message.reply(
            "❌ No active auction."
        )

        return


    #===== NOT RUNNING =====

    if result == "not_running":

        await message.reply(
            "❌ Auction is not currently running."
        )

        return


    #===== TIME OVER =====

    if result == "time_over":

        await message.reply(
            "❌ Bidding time is over."
        )

        return


    #===== NOT MANAGER =====

    if result == "not_manager":

        await message.reply(
            "❌ Only registered team managers can bid."
        )

        return


    #===== INVALID BID =====

    if result == "invalid_bid":

        await message.reply(
            "❌ Invalid bid amount."
        )

        return


    #===== ALREADY LEADING =====

    if result == "already_leading":

        await message.reply(
            "❌ Your team is already the highest bidder."
        )

        return


    #===== BID TOO LOW =====

    if result == "bid_too_low":

        current_auction = get_auction(
            message.chat.id
        )

        current_bid = float(
            current_auction.get(
                "current_bid",
                0
            )
        )

        await message.reply(

            f"❌ Bid must be higher than "
            f"₹{current_bid:.2f} Cr."
        )

        return


    #===== INSUFFICIENT PURSE =====

    if result == "insufficient_purse":

        await message.reply(
            "❌ Your team does not have enough purse."
        )

        return


    #===== SUCCESS =====

    await message.reply(

        "🔨 <b>BID ACCEPTED!</b>\n\n"

        f"🏏 Team : "
        f"<b>{result['team']}</b>\n"

        f"💰 Bid : "
        f"<b>₹{result['bid']:.2f} Cr</b>\n"

        "⏳ Timer reset to <b>20 sec</b>."
    )


    #===== GET UPDATED AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    #===== UPDATE AUCTION MESSAGE =====

    await update_auction_message(

        message.bot,

        auction
    )






#===== PAUSE AUCTION ========

@router.message(Command("pause_auction"))
async def pause_auction_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    auction = get_auction(
        message.chat.id
    )

    if not auction:

        await message.reply(
            "❌ No auction room exists."
        )

        return

    if message.from_user.id != auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the auction host can pause the auction."
        )

        return

    result = pause_auction(
        message.chat.id
    )

    if result == "no_auction":

        await message.reply(
            "❌ No auction room exists."
        )

        return

    if result == "not_running":

        await message.reply(
            "❌ No player auction is currently running."
        )

        return

    if result == "no_player":

        await message.reply(
            "❌ No current player."
        )

        return

    await message.reply(
        "⏸️ <b>Auction Paused</b>\n\n"
        f"👤 Player: <b>{result['current_player']['name']}</b>\n"
        f"💰 Current Bid: <b>₹{float(result.get('current_bid', 0)):.2f} Cr</b>\n"
        f"⏳ Time Remaining: <b>{result.get('timer', 0)} sec</b>\n\n"
        "Use <code>/resume_auction</code> to continue."
    )


#===== RESUME AUCTION ========

@router.message(Command("resume_auction"))
async def resume_auction_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    auction = get_auction(
        message.chat.id
    )

    if not auction:

        await message.reply(
            "❌ No auction room exists."
        )

        return

    if message.from_user.id != auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the auction host can resume the auction."
        )

        return

    result = resume_auction(
        message.chat.id
    )

    if result == "no_auction":

        await message.reply(
            "❌ No auction room exists."
        )

        return

    if result == "not_paused":

        await message.reply(
            "❌ Auction is not paused."
        )

        return

    if result == "no_player":

        await message.reply(
            "❌ No current player."
        )

        return

    if result == "time_over":

        await message.reply(
            "❌ This player's auction time has expired."
        )

        return

    #===== START TIMER AGAIN ========

    start_player_timer(
        message.bot,
        message.chat.id
    )

    auction = get_auction(
        message.chat.id
    )

    await message.reply(
        "▶️ <b>Auction Resumed</b>\n\n"
        f"👤 Player: <b>{auction['current_player']['name']}</b>\n"
        f"💰 Current Bid: <b>₹{float(auction.get('current_bid', 0)):.2f} Cr</b>\n"
        f"⏳ Time Remaining: <b>{auction.get('timer', 0)} sec</b>"
    )
    
    
    

#===== END AUCTION =====

@router.message(
    Command("end_auction")
)
async def end_auction_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )


    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== GET GROUP AUCTION =====

    auction = get_auction(
        message.chat.id
    )


    if not auction:

        await message.reply(
            "❌ No active auction found."
        )

        return


    #===== CHECK STATUS =====

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await message.reply(
            "❌ This auction has already ended."
        )

        return


    #===== HOST OR GROUP ADMIN =====

    member = await message.chat.get_member(
        message.from_user.id
    )


    if (
        message.from_user.id
        != auction.get("host_id")
        and member.status
        not in [
            "creator",
            "administrator"
        ]
    ):

        await message.reply(

            "❌ Only the auction host or a "
            "group admin can end the auction."
        )

        return


    #===== END CONFIRMATION =====

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="✅ Yes, End Auction",

                    callback_data=
                        "confirm_end_auction"
                )
            ],

            [

                InlineKeyboardButton(

                    text="❌ Cancel",

                    callback_data=
                        "cancel_end_auction"
                )
            ]
        ]
    )


    await message.reply(

        "⚠️ <b>End Auction?</b>\n\n"

        f"🆔 Auction ID: "
        f"<code>{auction['auction_id']}</code>\n\n"

        "This will close the current auction room.\n"

        "You can create a new auction after it ends.",

        reply_markup=keyboard
    )



#===== HOST CHANGE REQUESTS =====

host_change_requests = {}


#===== CHANGE HOST =====

@router.message(
    Command("changehost")
)
async def changehost_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    #===== GET AUCTION =====

    auction = get_auction(
        message.chat.id
    )

    if not auction:

        await message.reply(
            "❌ No active auction found."
        )

        return

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        await message.reply(
            "❌ This auction has already ended."
        )

        return

    #===== FIND TARGET USER =====

    target_user = None

    #===== REPLY METHOD =====

    if message.reply_to_message:

        target_user = (
            message.reply_to_message.from_user
        )

    #===== USERNAME METHOD =====

    else:

        args = message.text.split(
            maxsplit=1
        )

        if len(args) < 2:

            await message.reply(
                "❌ Please mention a user or reply to their message.\n\n"
                "Use:\n"
                "<code>/changehost @username</code>\n\n"
                "Or reply to a user's message with:\n"
                "<code>/changehost</code>"
            )

            return

        username = args[1].strip()

        if not username.startswith("@"):

            username = "@" + username

        try:

            members = await message.chat.get_administrators()

            for member in members:

                user = member.user

                if (
                    user.username
                    and
                    "@"
                    + user.username.lower()
                    ==
                    username.lower()
                ):

                    target_user = user

                    break

        except Exception as e:

            print(
                "CHANGEHOST USER LOOKUP ERROR:",
                e
            )

    if target_user is None:

        await message.reply(
            "❌ Could not find that user.\n\n"
            "Reply to their message and use "
            "<code>/changehost</code> instead."
        )

        return

    #===== CHECK TARGET IS DIFFERENT =====

    if target_user.id == auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ That user is already the auction host."
        )

        return

    #===== GET AUCTION MEMBERS / MANAGERS =====

    teams = auction.get(
        "teams",
        []
    )

    if not isinstance(
        teams,
        list
    ):

        teams = []

    member_ids = set()

    for team in teams:

        if not isinstance(
            team,
            dict
        ):

            continue

        manager_id = team.get(
            "manager_id"
        )

        if manager_id is not None:

            member_ids.add(
                int(manager_id)
            )

    #===== REQUESTER =====

    member_ids.add(
        int(message.from_user.id)
    )

    total_members = len(
        member_ids
    )

    if total_members <= 0:

        await message.reply(
            "❌ No auction members found."
        )

        return

    #===== REQUIRED VOTES =====

    required_votes = math.ceil(
        total_members / 2
    )

    request_key = str(
        message.chat.id
    )

    #===== PREVENT DUPLICATE REQUEST =====

    existing = host_change_requests.get(
        request_key
    )

    if existing:

        await message.reply(
            "❌ A host change vote is already active."
        )

        return

    #===== CREATE REQUEST =====

    host_change_requests[request_key] = {

        "chat_id": message.chat.id,

        "target_id": target_user.id,

        "target_username": (
            target_user.username
            or target_user.full_name
        ),

        "requested_by": (
            message.from_user.id
        ),

        "member_ids": list(
            member_ids
        ),

        "votes": [],

        "required_votes": required_votes
    }

    #===== VOTE BUTTON =====

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text=(
                        f"✅ Approve 0/"
                        f"{required_votes}"
                    ),

                    callback_data=(
                        "hostvote:"
                        + request_key
                    )
                )
            ]
        ]
    )

    await message.reply(

        "👑 <b>HOST CHANGE REQUEST</b>\n\n"

        f"👤 New Host : "
        f"<b>{target_user.full_name}</b>\n"

        f"🙋 Requested By : "
        f"<b>{message.from_user.full_name}</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "Vote for the new auction host.\n\n"

        f"📊 Votes : <b>0/{required_votes}</b>\n"

        f"👥 Auction Members : "
        f"<b>{total_members}</b>\n\n"

        "🎯 Required : <b>50%</b> of members"
        " (rounded up)",

        reply_markup=keyboard
    )


#===== HOST CHANGE VOTE =====

@router.callback_query(
    F.data.startswith("hostvote:")
)
async def host_change_vote(
    callback: CallbackQuery
):

    request_key = (
        callback.data.split(
            ":",
            1
        )[1]
    )

    request = host_change_requests.get(
        request_key
    )

    if not request:

        try:

            await callback.answer(
                "❌ This vote has expired.",
                show_alert=True
            )

        except Exception:

            pass

        return

    chat_id = request.get(
        "chat_id"
    )

    voter_id = int(
        callback.from_user.id
    )

    member_ids = set(
        request.get(
            "member_ids",
            []
        )
    )

    #===== MEMBER CHECK =====

    if voter_id not in member_ids:

        try:

            await callback.answer(
                "❌ Only auction members can vote.",
                show_alert=True
            )

        except Exception:

            pass

        return

    votes = request.get(
        "votes",
        []
    )

    #===== DUPLICATE VOTE =====

    if voter_id in votes:

        try:

            await callback.answer(
                "❌ You have already voted.",
                show_alert=True
            )

        except Exception:

            pass

        return

    #===== ADD VOTE =====

    votes.append(
        voter_id
    )

    request["votes"] = votes

    vote_count = len(
        votes
    )

    required_votes = int(
        request.get(
            "required_votes",
            1
        )
    )

    #===== HOST CHANGE APPROVED =====

    if vote_count >= required_votes:

        auction = get_auction(
            chat_id
        )

        if not auction:

            host_change_requests.pop(
                request_key,
                None
            )

            try:

                await callback.answer(
                    "❌ Auction no longer exists.",
                    show_alert=True
                )

            except Exception:

                pass

            return

        target_id = request.get(
            "target_id"
        )

        target_username = request.get(
            "target_username"
        )

        auction["host_id"] = target_id

        auction["host_username"] = (
            target_username
        )

        save_auction(
            auction
        )

        host_change_requests.pop(
            request_key,
            None
        )

        try:

            await callback.message.edit_text(

                "👑 <b>HOST CHANGED</b>\n\n"

                f"👤 New Host : "
                f"<b>{target_username}</b>\n\n"

                f"✅ Approved by "
                f"<b>{vote_count}/{required_votes}</b> "
                "members.\n\n"

                "🏏 The auction continues normally."
            )

        except Exception as e:

            print(
                "HOST CHANGE MESSAGE ERROR:",
                e
            )

        try:

            await callback.answer(
                "👑 Host changed successfully."
            )

        except Exception:

            pass

        return

    #===== UPDATE VOTE BUTTON =====

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text=(
                        f"✅ Approve "
                        f"{vote_count}/"
                        f"{required_votes}"
                    ),

                    callback_data=(
                        "hostvote:"
                        + request_key
                    )
                )
            ]
        ]
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=keyboard
        )

    except Exception as e:

        error_text = str(
            e
        ).lower()

        if (
            "message is not modified"
            not in error_text
        ):

            print(
                "HOST VOTE UPDATE ERROR:",
                e
            )

    try:

        await callback.answer(
            "✅ Vote recorded."
        )

    except Exception:

        pass
        
        
#===== SHOW TEAM SQUAD =====

@router.message(Command("squad"))
async def squad_command(message: Message):

    save_chat(message)
    set_chat_context(message.chat.id)

    if not is_group(message.chat.type):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    args = message.text.split(
        maxsplit=1
    )

    if len(args) != 2:

        await message.reply(
            "❌ Invalid Usage\n\n"
            "<code>/squad TEAM_NAME</code>\n\n"
            "Example:\n"
            "<code>/squad CSK</code>"
        )

        return

    team_name = args[1].strip()

    team = get_team_squad(
        message.chat.id,
        team_name
    )

    if team is None:

        await message.reply(
            f"❌ Team <b>{team_name}</b> not found."
        )

        return

    players = team.get(
        "players",
        []
    )

    text = (
        f"🏏 <b>{team['name']} SQUAD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Manager : "
        f"<b>{team.get('manager_username', 'Not Assigned')}</b>\n"
        f"💰 Purse : "
        f"<b>₹{float(team.get('purse', 0)):.2f} Cr</b>\n"
        f"👥 Players : "
        f"<b>{len(players)}</b>\n\n"
    )

    if not players:

        text += "📭 No players bought yet."

    else:

        for index, player in enumerate(
            players,
            start=1
        ):

            text += (
                f"{index}. "
                f"<b>{player.get('name', 'Unknown')}</b>\n"
                f"   💰 ₹"
                f"{float(player.get('sold_price', 0)):.2f} Cr\n\n"
            )

    await message.reply(
        text
    )
    
   
    
#===== VIEW TEAM SQUAD =====

@router.callback_query(F.data.startswith("squad:"))
async def view_team_squad(callback: CallbackQuery):

    chat_id = callback.message.chat.id

    set_chat_context(
        chat_id
    )

    team_name = callback.data.split(
        ":",
        1
    )[1]

    team = get_team_squad(
        chat_id,
        team_name
    )

    if team is None:

        await callback.answer(
            "❌ Team not found.",
            show_alert=True
        )

        return

    players = team.get(
        "players",
        []
    )

    text = (
        f"🏏 <b>{team['name']} SQUAD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Manager : "
        f"<b>{team.get('manager_username', 'Not Assigned')}</b>\n"
        f"💰 Purse : "
        f"<b>₹{float(team.get('purse', 0)):.2f} Cr</b>\n"
        f"👥 Players : <b>{len(players)}</b>\n\n"
    )

    if not players:

        text += "📭 No players bought yet."

    else:

        for index, player in enumerate(
            players,
            start=1
        ):

            text += (
                f"{index}. "
                f"<b>{player.get('name', 'Unknown')}</b>\n"
                f"   💰 ₹"
                f"{float(player.get('sold_price', 0)):.2f} Cr\n\n"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 All Squads",
                    callback_data="squads"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()
    
         
              
                        
#===== SHOW ALL SQUADS =====

@router.message(Command("squads"))
async def squads_command(message: Message):

    save_chat(message)
    set_chat_context(message.chat.id)

    if not is_group(message.chat.type):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return

    teams = get_teams()

    if not teams:

        await message.reply(
            "📭 No teams have been added yet."
        )

        return

    buttons = []

    row = []

    for team in teams:

        name = team.get(
            "name",
            "Unknown"
        )

        row.append(
            InlineKeyboardButton(
                text=f"🏏 {name}",
                callback_data=f"squad:{name}"
            )
        )

        if len(row) == 2:

            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.reply(
        "🏆 <b>AUCTION SQUADS</b>\n\n"
        "Select a team to view its squad:",
        reply_markup=keyboard
    )
    
           
#===== ALL SQUADS CALLBACK =====

@router.callback_query(F.data == "squads")
async def view_all_squads_callback(
    callback: CallbackQuery
):
    chat_id = callback.message.chat.id

    set_chat_context(
        chat_id
    )

    teams = get_teams()

    if not teams:
        await callback.answer(
            "❌ No teams have been added yet.",
            show_alert=True
        )
        return

    buttons = []
    row = []

    for team in teams:
        name = team.get(
            "name",
            "Unknown"
        )

        row.append(
            InlineKeyboardButton(
                text=f"🏏 {name}",
                callback_data=f"squad:{name}"
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await callback.message.edit_text(
        "🏆 <b>AUCTION SQUADS</b>\n\n"
        "Select a team to view its squad:",
        reply_markup=keyboard
    )

    await callback.answer()


#===== SQUAD SETUP TASKS =====

squad_setup_tasks = {}

                                    
                                                      
#===== START SQUAD SETUP TIMER =====

def start_squad_setup_timer(
    bot,
    chat_id
):

    old_task = squad_setup_tasks.get(
        chat_id
    )

    if (
        old_task
        and not old_task.done()
    ):

        old_task.cancel()

    task = asyncio.create_task(
        squad_setup_timeout(
            bot,
            chat_id
        )
    )

    squad_setup_tasks[chat_id] = task

    return task


#===== SQUAD SETUP TIMEOUT =====

async def squad_setup_timeout(
    bot,
    chat_id
):

    try:

        await asyncio.sleep(
            SQUAD_SETUP_TIMEOUT
        )

        auction = get_auction(
            chat_id
        )

        if not auction:
            return

        if auction.get(
            "squad_settings_locked",
            False
        ):
            return

        result = apply_default_squad_limits(
            chat_id
        )

        if isinstance(
            result,
            dict
        ):

            await bot.send_message(
                chat_id,

                "⏰ <b>Squad Setup Time Over!</b>\n\n"

                "Default limits have been applied:\n\n"

                f"👥 Minimum Squad: "
                f"<b>{DEFAULT_MIN_SQUAD}</b>\n"

                f"👥 Maximum Squad: "
                f"<b>{DEFAULT_MAX_SQUAD}</b>\n"

                f"🌍 Overseas Limit: "
                f"<b>{DEFAULT_OS_LIMIT}</b>\n\n"

                "✅ Auction will continue with "
                "these limits."
            )

    except asyncio.CancelledError:

        return

    except Exception as e:

        print(
            "SQUAD SETUP TIMER ERROR:",
            e
        )

    finally:

        squad_setup_tasks.pop(
            chat_id,
            None
        )
        

                                                                                        #===== SET SQUAD LIMITS =====

@router.message(
    Command("set_limits")
)
async def set_limits_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    #===== GROUP ONLY =====

    if not is_group(
        message.chat.type
    ):

        await message.reply(
            "❌ This command can only be used in a group."
        )

        return

    #===== GET AUCTION =====

    auction = get_auction(
        message.chat.id
    )

    if not auction:

        await message.reply(
            "❌ No auction found."
        )

        return

    #===== HOST ONLY =====

    if message.from_user.id != auction.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the auction host can set squad limits."
        )

        return

    #===== CHECK LOCK =====

    if auction.get(
        "squad_settings_locked",
        False
    ):

        await message.reply(
            "❌ Squad limits are already locked."
        )

        return

    #===== ARGUMENTS =====

    args = message.text.split()

    if len(args) != 4:

        await message.reply(
            "❌ <b>Invalid Usage</b>\n\n"

            "Use:\n"
            "<code>/set_limits MIN MAX OS</code>\n\n"

            "Example:\n"
            "<code>/set_limits 18 25 8</code>"
        )

        return

    try:

        min_squad = int(
            args[1]
        )

        max_squad = int(
            args[2]
        )

        os_limit = int(
            args[3]
        )

    except ValueError:

        await message.reply(
            "❌ All limits must be numbers."
        )

        return

    result = set_squad_limits(
        message.chat.id,
        min_squad,
        max_squad,
        os_limit
    )

    if result == "invalid_min":

        await message.reply(
            "❌ Minimum squad must be at least 1."
        )

        return

    if result == "invalid_max":

        await message.reply(
            "❌ Maximum squad cannot be lower than minimum squad."
        )

        return

    if result == "invalid_os":

        await message.reply(
            "❌ Overseas limit cannot exceed maximum squad."
        )

        return

    if result in [
        "invalid",
        "no_auction"
    ]:

        await message.reply(
            "❌ Invalid squad settings."
        )

        return

    if result == "already_locked":

        await message.reply(
            "❌ Squad settings are already locked."
        )

        return

    #===== STOP SETUP TIMER =====

    task = squad_setup_tasks.get(
        message.chat.id
    )

    if (
        task
        and not task.done()
    ):

        task.cancel()

    await message.reply(

        "✅ <b>Squad Settings Saved!</b>\n\n"

        f"👥 Minimum Squad: "
        f"<b>{min_squad}</b>\n"

        f"👥 Maximum Squad: "
        f"<b>{max_squad}</b>\n"

        f"🌍 Overseas Limit: "
        f"<b>{os_limit}</b>\n\n"

        "🔒 Settings locked for this auction."
    )
                                                            
#===== PING =====

@router.message(
    Command("ping")
)
async def ping_command(
    message: Message
):

    save_chat(
        message
    )


    start = time.perf_counter()


    sent = await message.reply(
        "🏓 Pinging..."
    )


    latency = (
        time.perf_counter()
        - start
    ) * 1000


    await sent.edit_text(

        f"🏓 <b>Pong!</b>\n\n"

        "🟢 Status: Online\n"

        f"⚡ Latency: "
        f"<code>{latency:.2f} ms</code>"
    )


#===== SETS =====

@router.message(
    Command("sets")
)
async def list_sets_command(
    message: Message
):

    save_user(
        message
    )

    save_chat(
        message
    )


    #===== GROUP =====

    if is_group(
        message.chat.type
    ):

        try:

            await message.bot.send_message(

                chat_id=
                    message.from_user.id,

                text=(

                    "🏏 <b>IPL AUCTION</b>\n\n"

                    "Browse Available Player Sets\n\n"

                    "Select an auction type below."
                ),

                reply_markup=
                    sets_home_keyboard
            )


            await message.reply(

                "📩 <b>Check your DM</b>\n\n"

                "Tap the button below to open "
                "the player sets.",

                reply_markup=
                    check_dm_keyboard
            )


        except Exception as e:

            print(
                "SETS DM ERROR:",
                e
            )


            await message.reply(

                "❌ Please start the bot in DM first "
                "using /start."
            )


        return


    #===== PRIVATE =====

    await message.reply(

        text=(

            "🏏 <b>IPL AUCTION</b>\n\n"

            "Browse Available Player Sets\n\n"

            "Select an auction type below."
        ),

        reply_markup=
            sets_home_keyboard
    )


#===== BROADCAST =====

@router.message(
    Command("broadcast")
)
async def broadcast(
    message: Message
):

    save_chat(
        message
    )

    #===== ADMIN ONLY =====

    if not is_admin(
        message.from_user.id
    ):

        await message.reply(
            "❌ You are not the owner of this bot."
        )

        return

    users = load_json(
        USERS_FILE
    )

    chats = load_json(
        CHATS_FILE
    )

    if not isinstance(
        users,
        list
    ):

        users = []

    if not isinstance(
        chats,
        list
    ):

        chats = []

    success = 0
    failed = 0
    group_sent = 0

    #===== REPLY BROADCAST =====

    if message.reply_to_message:

        source = message.reply_to_message

        # Use Telegram's native FORWARD operation.
        # This preserves the original message, including
        # supported custom emoji, formatting and media,
        # and shows the original sender/source.

        for user in users:

            try:

                await message.bot.forward_message(
                    chat_id=user["user_id"],
                    from_chat_id=source.chat.id,
                    message_id=source.message_id
                )

                success += 1

            except Exception as e:

                print(
                    "USER BROADCAST ERROR:",
                    e
                )

                failed += 1

        for chat in chats:

            try:

                if chat.get(
                    "type"
                ) in [
                    "group",
                    "supergroup"
                ]:

                    await message.bot.forward_message(
                        chat_id=chat["chat_id"],
                        from_chat_id=source.chat.id,
                        message_id=source.message_id
                    )

                    group_sent += 1

            except Exception as e:

                print(
                    "GROUP BROADCAST ERROR:",
                    e
                )

                failed += 1

    #===== TEXT BROADCAST =====

    else:

        args = message.text.split(
            maxsplit=1
        )

        if len(args) < 2:

            await message.reply(

                "Usage:\n"

                "/broadcast Message\n\n"

                "OR\n"

                "Reply to any message with "
                "/broadcast"
            )

            return

        text = args[1]

        for user in users:

            try:

                await message.bot.send_message(
                    chat_id=user["user_id"],
                    text=text
                )

                success += 1

            except Exception as e:

                print(
                    "USER BROADCAST ERROR:",
                    e
                )

                failed += 1

        for chat in chats:

            try:

                if chat.get(
                    "type"
                ) in [
                    "group",
                    "supergroup"
                ]:

                    await message.bot.send_message(
                        chat_id=chat["chat_id"],
                        text=text
                    )

                    group_sent += 1

            except Exception as e:

                print(
                    "GROUP BROADCAST ERROR:",
                    e
                )

                failed += 1

    #===== RESULT =====

    await message.reply(

        "📢 <b>Broadcast Completed</b>\n\n"

        f"👤 Users : {success}\n"

        f"👥 Groups : {group_sent}\n"

        f"❌ Failed : {failed}"
    )


#===== BOT STATS =====

@router.message(
    Command("botstats")
)
async def botstats_command(
    message: Message
):

    save_chat(
        message
    )

    set_chat_context(
        message.chat.id
    )

    #===== ADMIN ONLY =====

    if not is_admin(
        message.from_user.id
    ):

        await message.reply(
            "❌ You are not the owner of this bot."
        )

        return

    #===== LOAD USERS =====

    users = load_json(
        USERS_FILE
    )

    if not isinstance(
        users,
        list
    ):

        users = []

    #===== LOAD CHATS =====

    chats = load_json(
        CHATS_FILE
    )

    if not isinstance(
        chats,
        list
    ):

        chats = []

    #===== COUNT GROUPS =====

    groups = 0

    for chat in chats:

        if chat.get(
            "type"
        ) in [
            "group",
            "supergroup"
        ]:

            groups += 1

    #===== COUNT AUCTIONS =====

    auctions_created = 0
    active_auctions = 0

    for chat in chats:

        chat_id = chat.get(
            "chat_id"
        )

        if chat_id is None:
            continue

        auction = get_auction(
            chat_id
        )

        if not auction:
            continue

        auctions_created += 1

        if auction.get(
            "status"
        ) == "RUNNING":

            active_auctions += 1

    #===== PLAYER SETS =====

    mega_sets = 0
    legends_sets = 0

    try:

        files = [
            filename
            for filename in os.listdir(
                PLAYER_SETS_FOLDER
            )
            if filename.lower().endswith(
                ".json"
            )
        ]

        # Current player-set folder
        mega_sets = len(
            files
        )

    except Exception as e:

        print(
            "BOT STATS SET ERROR:",
            e
        )

    #===== STATS MESSAGE =====

    await message.reply(

        "📊 <b>BOT STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 Users : <b>{len(users)}</b>\n"

        f"👥 Groups : <b>{groups}</b>\n"

        f"🏏 Auctions Created: "
        f"<b>{auctions_created}</b>\n"

        f"🏏 Active Auctions : "
        f"<b>{active_auctions}</b>\n"

        "📦 <b>Current Sets</b>\n"

        f"        - Mega Auction Sets : "
        f"<b>{mega_sets}</b>\n"

        f"        - Legends Auction Sets : "
        f"<b>{legends_sets}</b>\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🤖 Bot is running normally."
    )
    
    
#===== HELP =====

@router.message(
    Command("help")
)
async def help_command(
    message: Message
):

    save_chat(
        message
    )

    await message.reply(

        "🏏 <b>IPL AUCTION BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "🎮 <b>AUCTION</b>\n"
        "/start — Choose Auction Type "
        "/create_auction — Create auction\n"
        "/load_set — Show available sets\n"
        "/load_set <code>SET_NAME</code> — Load player set\n"
        "/start_auction — Start auction\n"
        "/pause_auction — Pause auction\n"
        "/resume_auction — Resume auction\n"
        "/end_auction — End auction\n"
        "/restore <code>AUC-ID</code> — Restore auction\n\n"

        "💰 <b>BIDDING</b>\n"
        "/bid AMOUNT— Place a bid\n"
        "Example: /bid <code>2.50</code>\n\n"

        "👥 <b>TEAMS</b>\n"
        "/add_team — Add team\n"
        "/remove_team — Remove team\n"
        "/list_teams — List teams\n\n"

        "🏏 <b>SQUADS</b>\n"
        "/squad — View your squad\n"
        "/squads — View all squads\n\n"

        "📦 <b>PLAYER SETS</b>\n"
        "/sets — List player sets\n"
        "/load_set  — Show available sets\n"
        "/load_set SET_NAME — Load a set\n\n"

        "📊 <b>RESULTS & STATS</b>\n"
        "/results — Auction results\n"
        "/teamstats — Team financial statistics\n\n"

        "👑 <b>HOST</b>\n"
        "/changehost <code>@username</code> — Request host change\n\n"

        "⚙️ <b>OTHER</b>\n"
        "/ping— Check bot status\n"
        "/broadcast — Broadcast message\n"
        "/help — Show this help\n\n"

        "📋 <b>AUTO SQUAD LIMITS</b>\n"
        "Minimum : <b>18</b>\n"
        "Maximum : <b>25</b>\n"
        "Overseas : <b>8</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )    