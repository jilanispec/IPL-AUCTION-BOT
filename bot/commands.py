#===== IMPORTS =====

import os
import time
import asyncio
import time
import math
import random
import string


from aiogram import Router , F
from aiogram.filters import Command

from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

#===== TOURNAMENT SET LIMIT STATES =====

class TournamentSetLimitState(StatesGroup):

    waiting_custom_size = State()

    waiting_base_price = State()
    
    
#========↑^^^^^^^^ 


from auction.timer import (
    start_player_timer,
    cancel_player_timer
)

from auction.manager import (
    get_auction,
    save_auction
)


from utils.image_helper import prepare_player_image

from storage.json_manager import (
    load_json,
    save_json
)


from config import (
    AUCTION_FILE,
    DATA_FOLDER,
    TOURNAMENTS_FILE,
    TOURSETS_FOLDER
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
        message
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
        message
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
        message
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== COMMAND ARGUMENTS =====

    args = message.text.split()


    if len(args) < 3:

        await message.reply(
            "❌ <b>Invalid command.</b>\n\n"

            "Use manager username:\n"
            "<code>/add_team TEAM PURSE @username</code>\n\n"

            "Use Telegram user ID:\n"
            "<code>/add_team TEAM PURSE USER_ID</code>\n\n"

            "If manager has no username:\n"
            "Reply to the manager's message and use:\n"
            "<code>/add_team TEAM PURSE</code>"
        )

        return


    #===== TEAM NAME =====

    team_name = args[1].strip()


    if not team_name:

        await message.reply(
            "❌ Team name cannot be empty."
        )

        return


    #===== PURSE =====

    try:

        purse = float(
            args[2].strip()
        )

    except ValueError:

        await message.reply(
            "❌ Purse must be a valid number."
        )

        return


    if purse <= 0:

        await message.reply(
            "❌ Purse must be greater than 0."
        )

        return


    #===== MANAGER DEFAULT =====

    manager_username = None

    manager_id = None


    #===== REPLY MODE =====

    if message.reply_to_message:

        replied_user = (
            message.reply_to_message.from_user
        )


        if replied_user:

            manager_id = replied_user.id


            if replied_user.username:

                manager_username = (
                    f"@{replied_user.username}"
                )


    #===== DIRECT MANAGER ARGUMENT =====

    elif len(args) >= 4:

        manager_arg = args[3].strip()


        #===== USERNAME =====

        if manager_arg.startswith("@"):

            if len(manager_arg) <= 1:

                await message.reply(
                    "❌ Invalid Telegram username."
                )

                return


            manager_username = (
                manager_arg
            )


        #===== TELEGRAM USER ID =====

        elif manager_arg.isdigit():

            try:

                manager_id = int(
                    manager_arg
                )

            except ValueError:

                await message.reply(
                    "❌ Invalid Telegram user ID."
                )

                return


        #===== INVALID MANAGER =====

        else:

            await message.reply(
                "❌ Invalid manager.\n\n"

                "Use:\n"
                "<code>/add_team TEAM PURSE @username</code>\n\n"

                "or:\n"
                "<code>/add_team TEAM PURSE USER_ID</code>\n\n"

                "or reply to the manager's message."
            )

            return


    #===== NO MANAGER =====

    else:

        await message.reply(
            "❌ Manager is required.\n\n"

            "Use a username, Telegram user ID, "
            "or reply to the manager's message."
        )

        return


    #===== CHECK EXISTING TEAMS =====

    teams = get_teams()


    #===== CHECK DUPLICATE TEAM =====

    for team in teams:

        existing_team_name = (
            team.get("name")
        )


        if (
            existing_team_name
            and existing_team_name.lower()
            == team_name.lower()
        ):

            await message.reply(
                "❌ A team with this name already exists."
            )

            return


    #===== CHECK DUPLICATE MANAGER =====

    for team in teams:

        existing_manager_id = (
            team.get("manager_id")
        )

        existing_manager_username = (
            team.get("manager_username")
        )


        #===== CHECK USER ID =====

        if (
            manager_id is not None
            and existing_manager_id is not None
        ):

            try:

                if (
                    int(existing_manager_id)
                    == int(manager_id)
                ):

                    await message.reply(
                        "❌ This manager is already assigned to a team."
                    )

                    return

            except (
                ValueError,
                TypeError
            ):

                pass


        #===== CHECK USERNAME =====

        if (
            manager_username
            and existing_manager_username
        ):

            if (
                manager_username.lower()
                == existing_manager_username.lower()
            ):

                await message.reply(
                    "❌ This manager is already assigned to a team."
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


    #===== MANAGER DISPLAY =====

    if manager_username:

        manager_display = (
            manager_username
        )

    elif manager_id is not None:

        manager_display = (
            f"<code>{manager_id}</code>"
        )

    else:

        manager_display = (
            "Not Assigned"
        )


    #===== SUCCESS =====

    await message.reply(

        "✅ <b>Team Added Successfully!</b>\n\n"

        f"🏏 Team : <b>{team_name}</b>\n"

        f"💰 Purse : ₹{purse:.2f} Cr\n"

        f"👤 Manager : {manager_display}\n"

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
        message
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
        message
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

        message

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
        message
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
        message
    ):

        await message.reply(
            "❌ Bidding is only available in groups."
        )

        return


    #===============
    #===== TOURNAMENT BID CHECK 
    #================

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        tournaments = []


    #===== FIND RUNNING TOURNAMENT =====

    tournament = None

    tournament_index = None

    for index, tour in enumerate(
        tournaments
    ):

        if (
            tour.get("chat_id")
            == message.chat.id

            and tour.get("status")
            == "AUCTION_RUNNING"
        ):

            tournament = tour

            tournament_index = index

            break


    #==================================================
    #===== TOURNAMENT BIDDING =========================
    #==================================================

    if tournament is not None:

        #===== GET AUCTION SETUP =====

        setup = tournament.get(
            "auction_setup",
            {}
        )


        #===== CHECK AUCTION STATUS =====

        if setup.get(
            "status"
        ) != "RUNNING":

            await message.reply(
                "❌ Tournament auction is not currently running."
            )

            return


        #===== CHECK TIMER =====

        timer = int(
            setup.get(
                "timer",
                0
            )
        )

        if timer <= 0:

            await message.reply(
                "❌ Bidding time is over."
            )

            return


        #===== COMMAND ARGUMENTS =====

        args = message.text.split()


        if len(args) != 2:

            await message.reply(

                "❌ <b>Invalid bid.</b>\n\n"

                "Use:\n"

                "<code>/bid 60</code>\n\n"

                "Amount must be in <b>Lakhs</b>."

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


        if bid_amount <= 0:

            await message.reply(
                "❌ Bid must be greater than 0."
            )

            return


        #===== GET CURRENT BID =====

        current_bid = float(
            setup.get(
                "current_bid_lakhs",
                setup.get(
                    "base_price",
                    0
                )
            )
        )


        #===== FIND MANAGER TEAM =====

        team = None

        for item in tournament.get(
            "teams",
            []
        ):

            if not isinstance(
                item,
                dict
            ):

                continue


            manager_id = item.get(
                "manager_id"
            )


            try:

                if (
                    manager_id is not None
                    and int(manager_id)
                    == int(message.from_user.id)
                ):

                    team = item

                    break

            except (
                TypeError,
                ValueError
            ):

                continue


        #===== NOT A TEAM MANAGER =====

        if team is None:

            await message.reply(
                "❌ <b>Only tournament team managers can bid.</b>"
            )

            return


        #===== TEAM SHORT CODE =====

        short_code = team.get(
            "short_code",
            team.get(
                "name",
                "Unknown"
            )
        )


        #===== CHECK ALREADY LEADING =====

        leading_team = setup.get(
            "leading_team"
        )


        leading_code = None


        if isinstance(
            leading_team,
            dict
        ):

            leading_code = (
                leading_team.get(
                    "short_code"
                )

                or leading_team.get(
                    "code"
                )

                or leading_team.get(
                    "name"
                )
            )

        elif leading_team:

            leading_code = str(
                leading_team
            )


        if (
            leading_code
            and str(
                leading_code
            ).upper()
            == str(
                short_code
            ).upper()
        ):

            await message.reply(
                "❌ <b>Your team is already the highest bidder.</b>"
            )

            return


        #===== BID MUST BE HIGHER =====

        if bid_amount <= current_bid:

            await message.reply(

                "❌ <b>Bid too low.</b>\n\n"

                f"💰 Current Bid : "
                f"<b>₹{current_bid:g} Lakhs</b>\n\n"

                "⬆️ Your bid must be higher."

            )

            return


        #===== GET TEAM PURSE =====

        purse_lakhs = float(
            team.get(
                "purse_lakhs",
                team.get(
                    "purse",
                    0
                )
            )
        )


        #===== CHECK PURSE =====

        if bid_amount > purse_lakhs:

            await message.reply(

                "❌ <b>Insufficient Purse!</b>\n\n"

                f"🏏 Team : "
                f"<b>{short_code}</b>\n"

                f"💰 Available : "
                f"<b>₹{purse_lakhs:g} Lakhs</b>\n"

                f"🔨 Your Bid : "
                f"<b>₹{bid_amount:g} Lakhs</b>"

            )

            return


        #===== SQUAD SIZE =====

        squad_size = int(
            tournament.get(
                "squad_size",
                setup.get(
                    "squad_size",
                    0
                )
            )
        )


        #===== CURRENT SQUAD =====

        team_players = team.get(
            "players",
            []
        )


        if not isinstance(
            team_players,
            list
        ):

            team_players = []


        #===== CHECK SQUAD LIMIT =====

        # Manager/captain occupies one squad slot.
        if (len(team_players) + 1) >= squad_size:

            await message.reply(

                "❌ <b>Your squad is full.</b>\n\n"

                f"👥 Squad Size : "
                f"<b>{len(team_players) + 1} / {squad_size}</b>"

            )

            return


        #===== SAVE CURRENT BID =====

        setup[
            "current_bid_lakhs"
        ] = bid_amount


        #===== SAVE LEADING TEAM =====

        setup[
            "leading_team"
        ] = short_code


        #===== SAVE LEADING MANAGER =====

        setup[
            "leading_manager_id"
        ] = message.from_user.id


        #===== RESET TIMER =====

        setup[
            "timer"
        ] = 20


        #===== SAVE SETUP =====

        tournament[
            "auction_setup"
        ] = setup


        tournaments[
            tournament_index
        ] = tournament


        #===== SAVE JSON =====

        save_json(
            TOURNAMENTS_FILE,
            tournaments
        )


        #===== DISPLAY TEAM =====

        team_name = team.get(
            "name",
            short_code
        )


        if str(
            team_name
        ).upper() != str(
            short_code
        ).upper():

            display_team = (
                f"{short_code} — "
                f"{team_name}"
            )

        else:

            display_team = short_code


        #===== BID SUCCESS =====

        await message.reply(

            "🔨 <b>BID ACCEPTED!</b>\n\n"

            f"🏏 Team : "
            f"<b>{display_team}</b>\n"

            f"💰 Bid : "
            f"<b>₹{bid_amount:g} Lakhs</b>\n"

            "⏳ Timer reset to "
            "<b>20 sec</b>."

        )


        #==================================================
        #===== UPDATE TOURNAMENT AUCTION CARD ============
        #==================================================

        auction_message_id = setup.get(
            "auction_message_id"
        )


        if auction_message_id:

            player = setup.get(
                "current_player",
                {}
            )


            player_name = (
                player.get("name")
                or player.get("player_name")
                or "Unknown Player"
            )


            country = player.get(
                "country",
                "Unknown"
            )


            role = player.get(
                "role",
                "Unknown"
            )


            base_price = float(
                setup.get(
                    "base_price",
                    0
                )
            )


            caption = (

                "🏆 <b>TOURNAMENT AUCTION</b>\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                f"👤 <b>{player_name}</b>\n"

                f"🌍 Country : <b>{country}</b>\n"

                f"🎯 Role : <b>{role}</b>\n\n"

                f"📦 Set : "
                f"<b>{setup.get('selected_set', 1)}</b>\n\n"

                f"💰 Base Price : "
                f"<b>₹{base_price:g} Lakhs</b>\n"

                f"💰 Current Bid : "
                f"<b>₹{bid_amount:g} Lakhs</b>\n\n"

                f"👑 Leading Team : "
                f"<b>{display_team}</b>\n"

               f"⏳ Time Left : "
               f"<b>{setup.get('timer', 20)} sec</b>\n\n"

                "📢 <b>BIDDING IS OPEN!</b>"

            )


            #===== UPDATE TOURNAMENT AUCTION CARD =====

            try:

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=auction_message_id,
                    text=caption,
                    parse_mode="HTML"
                )

            except TelegramBadRequest as e:

                if (
                    "message is not modified"
                    not in str(e).lower()
                ):

                    print(
                        "TOURNAMENT BID CARD ERROR:",
                        e
                    )

            except Exception as e:

                print(
                    "TOURNAMENT BID CARD ERROR:",
                    e
                )

        return

    #==================================================
    #===== NORMAL AUCTION =============================
    #==================================================


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
        message
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
        message
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
        message
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
        message
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

@router.message(
    Command("squad")
)
async def squad_command(
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
        message
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== TEAM NAME / CODE =====

    args = message.text.split(
        maxsplit=1
    )

    if len(args) != 2:

        await message.reply(
            "❌ Invalid Usage\n\n"
            "<code>/squad TEAM_CODE</code>\n\n"
            "Example:\n"
            "<code>/squad PB</code>"
        )

        return


    team_identifier = args[1].strip()


    #==================================================
    #===== CHECK TOURNAMENT TEAM FIRST ================
    #==================================================

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    tournament = None

    if isinstance(
        tournaments,
        list
    ):

        for tour in reversed(tournaments):

            if (
                tour.get("chat_id") == message.chat.id
                and tour.get("status") not in (
                    "ENDED",
                    "CANCELLED"
                )
            ):

                tournament = tour

                break


    if tournament is not None:

        tournament_teams = tournament.get(
            "teams",
            []
        )

        tournament_team = None

        for team in tournament_teams:

            short_code = str(
                team.get(
                    "short_code",
                    ""
                )
            ).strip()

            name = str(
                team.get(
                    "name",
                    ""
                )
            ).strip()

            if (
                team_identifier.upper()
                == short_code.upper()
                or
                team_identifier.lower()
                == name.lower()
            ):

                tournament_team = team

                break


        #===== TOURNAMENT SQUAD =====

        if tournament_team is not None:

            name = tournament_team.get(
                "name",
                "Unknown"
            )

            short_code = tournament_team.get(
                "short_code",
                name
            )

            manager = tournament_team.get(
                "manager_name",
                tournament_team.get(
                    "manager_username",
                    "Not Assigned"
                )
            )

            purse_lakhs = float(
                tournament_team.get(
                    "purse_lakhs",
                    tournament_team.get("purse", 0)
                )
            )

            purse_crore = purse_lakhs / 100

            players = tournament_team.get(
                "players",
                []
            )


            display_name = (
                f"{short_code} — {name}"
                if name.upper() != short_code.upper()
                else short_code
            )


            text = (
                f"🏏 <b>{display_name} SQUAD</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👑 Manager : <b>{manager}</b>\n"
                f"💰 Purse : <b>₹{purse_crore:.2f} Cr</b>\n"
                f"👥 Squad : <b>{len(players) + 1} / {tournament.get('squad_size', 0)}</b>\n\n"
            )


            if not players:

                text += (
                    "📭 No players bought yet."
                )

            else:

                for index, player in enumerate(
                    players,
                    start=1
                ):

                    player_name = player.get(
                        "name",
                        "Unknown"
                    )

                    sold_price = float(
                        player.get(
                            "sold_price",
                            0
                        )
                    )

                    text += (
                        f"{index}. "
                        f"<b>{player_name}</b>\n"
                        f"   💰 ₹{sold_price:.2f} Cr\n\n"
                    )


            await message.reply(
                text
            )

            return


    #==================================================
    #===== ORIGINAL NORMAL AUCTION CORE ===============
    #==================================================

    team = get_team_squad(
        message.chat.id,
        team_identifier
    )


    if team is None:

        await message.reply(
            f"❌ Team <b>{team_identifier}</b> not found."
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

        text += (
            "📭 No players bought yet."
        )

    else:

        for index, player in enumerate(
            players,
            start=1
        ):

            text += (
                f"{index}. "
                f"<b>{player.get('name') or player.get('display_name') or player.get('first_name') or player.get('player_name') or 'Unknown'}</b>\n"
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

@router.message(
    Command("squads")
)
async def squads_command(
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
        message
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== FIND TOURNAMENT =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    tournament = None

    if isinstance(
        tournaments,
        list
    ):

        for tour in reversed(tournaments):

            if (
                tour.get("chat_id") == message.chat.id
                and tour.get("status") not in (
                    "ENDED",
                    "CANCELLED"
                )
            ):

                tournament = tour

                break


    #==================================================
    #===== TOURNAMENT SQUADS ==========================
    #==================================================

    if tournament is not None:

        teams = tournament.get(
            "teams",
            []
        )

        if teams:

            buttons = []
            row = []

            for team in teams:

                name = team.get(
                    "name",
                    "Unknown"
                )

                short_code = team.get(
                    "short_code",
                    name
                )


                row.append(
                    InlineKeyboardButton(
                        text=f"🏏 {short_code}",
                        callback_data=(
                            f"tour_squad:{short_code}"
                        )
                    )
                )


                if len(row) == 2:

                    buttons.append(
                        row
                    )

                    row = []


            if row:

                buttons.append(
                    row
                )


            keyboard = InlineKeyboardMarkup(
                inline_keyboard=buttons
            )


            await message.reply(
                "🏆 <b>TOURNAMENT SQUADS</b>\n\n"
                "Select a team to view its squad:",
                reply_markup=keyboard
            )

            return


    #==================================================
    #===== ORIGINAL NORMAL AUCTION ====================
    #==================================================

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

            buttons.append(
                row
            )

            row = []


    if row:

        buttons.append(
            row
        )


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


    await message.reply(
        "🏆 <b>AUCTION SQUADS</b>\n\n"
        "Select a team to view its squad:",
        reply_markup=keyboard
    )

    
#===== TOURNAMENT SQUAD CALLBACK =====

@router.callback_query(
    F.data.startswith("tour_squad:")
)
async def view_tournament_squad(
    callback: CallbackQuery
):

    chat_id = callback.message.chat.id

    set_chat_context(
        chat_id
    )


    short_code = callback.data.split(
        ":",
        1
    )[1]


    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    tournament = None


    if isinstance(
        tournaments,
        list
    ):

        for tour in reversed(tournaments):

            if (
                tour.get("chat_id") == chat_id
                and tour.get("status") not in (
                    "ENDED",
                    "CANCELLED"
                )
            ):

                tournament = tour

                break


    if tournament is None:

        await callback.answer(
            "❌ Tournament not found.",
            show_alert=True
        )

        return


    #===== FIND TEAM =====

    team = None

    for item in tournament.get(
        "teams",
        []
    ):

        if str(
            item.get(
                "short_code",
                ""
            )
        ).upper() == short_code.upper():

            team = item

            break


    if team is None:

        await callback.answer(
            "❌ Team not found.",
            show_alert=True
        )

        return


    name = team.get(
        "name",
        "Unknown"
    )

    code = team.get(
        "short_code",
        short_code
    )

    manager = team.get(
        "manager_name",
        team.get(
            "manager_username",
            "Not Assigned"
        )
    )

    purse = float(
        team.get(
            "purse",
            0
        )
    )

    players = team.get(
        "players",
        []
    )


    display_name = (
        f"{code} — {name}"
        if name.upper() != code.upper()
        else code
    )


    text = (
        f"🏏 <b>{display_name} SQUAD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 Manager : <b>{manager}</b>\n"
        f"💰 Purse : <b>₹{purse:.2f} Cr</b>\n"
        f"👥 Players : <b>{len(players)}</b>\n\n"
    )


    if not players:

        text += (
            "📭 No players bought yet."
        )

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
                    callback_data="tour_squads"
                )
            ]
        ]
    )


    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()
    
                    
#===== TOURNAMENT ALL SQUADS CALLBACK =====

@router.callback_query(
    F.data == "tour_squads"
)
async def view_tournament_squads_callback(
    callback: CallbackQuery
):

    chat_id = callback.message.chat.id

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    tournament = None


    if isinstance(
        tournaments,
        list
    ):

        for tour in reversed(tournaments):

            if (
                tour.get("chat_id") == chat_id
                and tour.get("status") not in (
                    "ENDED",
                    "CANCELLED"
                )
            ):

                tournament = tour

                break


    if tournament is None:

        await callback.answer(
            "❌ Tournament not found.",
            show_alert=True
        )

        return


    teams = tournament.get(
        "teams",
        []
    )


    if not teams:

        await callback.answer(
            "❌ No tournament teams.",
            show_alert=True
        )

        return


    buttons = []
    row = []


    for team in teams:

        code = team.get(
            "short_code",
            team.get(
                "name",
                "Unknown"
            )
        )


        row.append(
            InlineKeyboardButton(
                text=f"🏏 {code}",
                callback_data=f"tour_squad:{code}"
            )
        )


        if len(row) == 2:

            buttons.append(
                row
            )

            row = []


    if row:

        buttons.append(
            row
        )


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


    await callback.message.edit_text(
        "🏆 <b>TOURNAMENT SQUADS</b>\n\n"
        "Select a team to view its squad:",
        reply_markup=keyboard
    )


    await callback.answer()
    
                                    
           
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
        message
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
        message
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
    
#=====================================


# THIS SECTION ALL ABOUT THE TOURNAMENT TILL above HELP


#=====================================
    
#===== TOURNAMENT SYSTEM =====



TOURNAMENTS_FILE = os.path.join(DATA_FOLDER, "tournaments.json")


#===== GENERATE UNIQUE TOURNAMENT CODE =====

def generate_tournament_code():
    tournaments = load_json(TOURNAMENTS_FILE)

    if not isinstance(tournaments, list):
        tournaments = []

    existing_codes = {
        str(t.get("code", "")).upper()
        for t in tournaments
        if isinstance(t, dict)
    }

    while True:
        code = "T" + "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=5
            )
        )

        if code not in existing_codes:
            return code


#===== HOST TOURNAMENT =====

@router.message(Command("hosttournament"))
async def host_tournament_command(message: Message):

    save_user(message)
    save_chat(message)

    # Tournament hosting is group only
    if not is_group(message):
        await message.reply(
            "❌ <b>Group Only</b>\n\n"
            "Tournament hosting must be done inside the auction group."
        )
        return

    #===== CHECK GROUP ADMIN =====

    try:
        member = await message.bot.     get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id
        )

        if member.status not in ["creator", "administrator"]:
            await message.reply(
                "❌ <b>Admin Only</b>\n\n"
                "Only the group owner or an administrator can host a tournament."
            )
            return

    except Exception:
        await message.reply(
            "❌ <b>Permission Check Failed</b>\n\n"
            "I couldn't verify your group permissions."
        )
        return

    # Tournament name required
    args = message.text.split(maxsplit=1)

    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "🏆 <b>Host Tournament</b>\n\n"
            "Use:\n"
            "<code>/hosttournament Tournament Name</code>\n\n"
            "Example:\n"
            "<code>/hosttournament IPL 2026 Championship</code>"
        )
        return

    tournament_name = args[1].strip()

    tournaments = load_json(TOURNAMENTS_FILE)

    if not isinstance(tournaments, list):
        tournaments = []

    # Check active tournament in this group
    for tournament in tournaments:

        if not isinstance(tournament, dict):
            continue

        if (
            tournament.get("chat_id") == message.chat.id
            and tournament.get("status") not in ["ENDED", "CANCELLED"]
        ):
            await message.reply(
                "⚠️ <b>Tournament Already Exists</b>\n\n"
                f"🏆 Name: <b>{tournament.get('name', 'Unnamed')}</b>\n"
                f"🔑 Code: <code>{tournament.get('code')}</code>\n\n"
                "Finish or cancel the current tournament before creating another one in this group."
            )
            return

    # Generate unique code
    code = generate_tournament_code()

    username = message.from_user.username

    if username:
        host_username = f"@{username}"
    else:
        host_username = message.from_user.first_name or "Unknown"

    # Create tournament
    tournament = {
        "code": code,
        "name": tournament_name,
        "chat_id": message.chat.id,
        "chat_title": message.chat.title,
        "host_id": message.from_user.id,
        "host_username": host_username,
        "status": "SETUP",
        "players": [],
        "teams": [],
        "auctions": [],
        "created_at": int(time.time())
    }

    tournaments.append(tournament)

    save_json(TOURNAMENTS_FILE, tournaments)

    await message.reply(
        "🏆 <b>TOURNAMENT CREATED!</b>\n\n"
        f"📛 Name: <b>{tournament_name}</b>\n"
        f"🔑 Code: <code>{code}</code>\n"
        f"👤 Host: <b>{host_username}</b>\n"
        f"📍 Group: <b>{message.chat.title}</b>\n\n"
        "📌 <b>Status:</b> SETUP\n\n"
        "Your tournament has been created successfully."
    )
    
    
    
#===== TOURNAMENT REGISTER =====

@router.message(Command("register"))
async def register_tournament_command(message: Message):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ <b>/register</b> can only be used inside a group."
        )
        return

    #===== BLOCK BOTS =====

    if message.from_user.is_bot:
        await message.reply(
            "❌ <b>Bots cannot register.</b>"
        )
        return

    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None
    tournament_index = None

    #===== FIND ONLY OPEN REGISTRATION =====

    for index, item in enumerate(tournaments):

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") == "SETUP"
        ):
            tournament = item
            tournament_index = index
            break

    #===== NO OPEN REGISTRATION =====

    if tournament is None:

        await message.reply(
            "🔒 <b>Registration is closed.</b>\n\n"
            "❌ You cannot register for this tournament."
        )
        return

    #===== PLAYER DATA =====

    user_id = message.from_user.id

    first_name = (
        message.from_user.first_name
        or "Unknown"
    )

    username = message.from_user.username

    players = tournament.get("players", [])

    #===== CHECK ALREADY REGISTERED =====

    for player in players:

        if player.get("user_id") == user_id:

            mention = (
                f'<a href="tg://user?id={user_id}">'
                f'{first_name}'
                f'</a>'
            )

            await message.reply(
                "⚠️ <b>Already Registered!</b>\n\n"
                f"🏆 Tournament: "
                f"<b>{tournament.get('name', 'Unknown')}</b>\n\n"
                f"{mention}, you are already in the auction pool."
            )
            return

    #===== ADD PLAYER =====

    players.append({
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "display_name": first_name,
        "registered_at": int(time.time())
    })

    tournament["players"] = players

    tournaments[tournament_index] = tournament

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #===== SUCCESS =====

    mention = (
        f'<a href="tg://user?id={user_id}">'
        f'{first_name}'
        f'</a>'
    )

    await message.reply(
        "✅ <b>REGISTERED!</b>\n\n"
        f"🏆 Tournament: "
        f"<b>{tournament.get('name', 'Unknown')}</b>\n"
        f"🔑 Code: "
        f"<code>{tournament.get('code', 'N/A')}</code>\n\n"
        f"👤 You have been added to the auction pool.\n\n"
        f"👥 Registered Players: <b>{len(players)}</b>"
    )

            
                        
                                                
#===== AUCTION POOL =====

AUCPOOL_PAGE_SIZE = 10
AUCPOOL_COOLDOWN = 1.0

# user_id -> last callback time
AUCPOOL_COOLDOWNS = {}


def get_pool_display_name(player):
    username = player.get("username")

    if username:
        return f"@{username}"

    return player.get("first_name") or "Unknown"


#===== BUILD AUCTION POOL PAGE =====

def build_auction_pool_page(tournament, page):

    players = tournament.get("players", [])

    total_players = len(players)

    total_pages = max(
        1,
        math.ceil(total_players / AUCPOOL_PAGE_SIZE)
    )

    #===== SAFE PAGE =====

    page = max(
        0,
        min(page, total_pages - 1)
    )

    start = page * AUCPOOL_PAGE_SIZE
    end = start + AUCPOOL_PAGE_SIZE

    page_players = players[start:end]

    #===== HEADER =====

    text = (
        "🏏 <b>AUCTION POOL</b>\n\n"
        f"🏆 Tournament : "
        f"<b>{tournament.get('name', 'Unknown')}</b>\n"
        f"🔑 Code : "
        f"<code>{tournament.get('code', 'N/A')}</code>\n"
        f"👥 Players : <b>{total_players}</b>\n\n"
    )

    #===== PLAYER LIST =====

    for index, player in enumerate(
        page_players,
        start=start + 1
    ):

        first_name = (
            player.get("first_name")
            or "Unknown"
        )

        user_id = player.get("user_id")

        if user_id:

            mention = (
                f'<a href="tg://user?id={user_id}">'
                f'{first_name}'
                f'</a>'
            )

        else:
            mention = first_name

        text += (
            f"<b>{index}.</b> 👤 {mention}\n"
        )

    #===== KEYBOARD =====

    keyboard = []

    navigation = []

    #===== NEXT =====

    if page < total_pages - 1:

        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"aucpool:{page + 1}"
            )
        )

    else:

        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data="aucpool:noop"
            )
        )

    #===== PAGE NUMBER =====

    navigation.append(
        InlineKeyboardButton(
            text=f"{page + 1} / {total_pages}",
            callback_data="aucpool:page"
        )
    )

    #===== PREVIOUS =====

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"aucpool:{page - 1}"
            )
        )

    else:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data="aucpool:noop"
            )
        )

    keyboard.append(navigation)

    #===== REFRESH =====

    keyboard.append([
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data="aucpool:refresh"
        )
    ])

    #===== RETURN =====

    return text, InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


#===== AUCPOOL COMMAND =====

@router.message(Command("aucpool"))
async def auction_pool_command(message: Message):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ <b>/aucpool</b> can only be used inside a group."
        )
        return

    #===== CHECK GROUP ADMIN =====

    member = await message.bot.get_chat_member(
        chat_id=message.chat.id,
        user_id=message.from_user.id
    )

    if member.status not in ("creator", "administrator"):
        await message.reply(
            "❌ Only group admins can use <b>/aucpool</b>."
        )
        return

    #===== LOAD TOURNAMENT =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None

    for item in tournaments:
        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in ("ENDED", "CANCELLED")
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ <b>No active tournament found</b> in this group."
        )
        return

    #===== CHECK POOL =====

    players = tournament.get("players", [])

    if not players:
        await message.reply(
            "⚠️ <b>Auction pool is empty.</b>\n\n"
            "Players can use <code>/register</code> to join."
        )
        return

    #===== BUILD PAGE =====

    text, keyboard = build_auction_pool_page(
        tournament,
        0
    )

    #===== SEND POOL =====

    pool_message = await message.reply(
        text,
        reply_markup=keyboard
    )

    #===== PIN ONCE =====

    try:
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=pool_message.message_id,
            disable_notification=True
        )
    except Exception:
        pass


#===== AUCPOOL PAGINATION =====

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

    #===== GET ACTION =====

    action = callback.data.split(":", 1)[1]

    #===== REFRESH =====

    if action == "refresh":

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
                "❌ No active tournament found.",
                show_alert=True
            )
            return

        text, keyboard = build_auction_pool_page(
            tournament,
            0
        )

        try:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard
            )

        except Exception as e:

            if "message is not modified" not in str(e).lower():
                await callback.answer(
                    "❌ Unable to refresh pool.",
                    show_alert=False
                )
                return

        await callback.answer(
            "🔄 Pool refreshed.",
            show_alert=False
        )
        return

    #===== CURRENT PAGE =====

    if action == "page":

        await callback.answer(
            "📄 You are viewing this page.",
            show_alert=False
        )
        return

    #===== NO OPERATION =====

    if action == "noop":

        await callback.answer()
        return

    #===== CLOSE =====

    if action == "close":

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.answer()
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

    #===== LOAD LATEST TOURNAMENT =====

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

    #===== BUILD PAGE =====

    text, keyboard = build_auction_pool_page(
        tournament,
        page
    )

    #===== UPDATE MESSAGE =====

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

        

#===== ADD PLAYER TO AUCTION POOL =====

@router.message(Command("add_player"))
async def add_player_command(message: Message):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ <b>/add_player</b> can only be used inside a group."
        )
        return

    #===== FIND TOURNAMENT =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None

    for item in tournaments:
        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in ("ENDED", "CANCELLED")
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ <b>No active tournament found</b> in this group."
        )
        return

    #===== HOST CHECK =====

    if tournament.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ Only the <b>Tournament Host</b> can add players."
        )
        return

    #===== FIND TARGET =====

    target_user = None

    if message.reply_to_message:

        target_user = message.reply_to_message.from_user

        if not target_user:
            await message.reply(
                "❌ Could not identify the user."
            )
            return

    else:

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await message.reply(
                "❌ <b>How to use:</b>\n\n"
                "Reply to a user:\n"
                "<code>/add_player</code>\n\n"
                "User ID:\n"
                "<code>/add_player 123456789</code>\n\n"
                "Username:\n"
                "<code>/add_player @username</code>"
            )
            return

        target = args[1].strip()

        #===== USER ID =====

        if target.isdigit():

            try:
                target_user = await message.bot.get_chat(
                    int(target)
                )
            except Exception:
                await message.reply(
                    "❌ Unable to find that Telegram user ID."
                )
                return

        #===== USERNAME =====

        else:

            username = target.lstrip("@")

            try:
                target_user = await message.bot.get_chat(
                    f"@{username}"
                )
            except Exception:
                await message.reply(
                    "❌ Unable to find that username.\n\n"
                    "💡 Try replying to the user's message."
                )
                return

    #===== BLOCK BOTS =====

    if getattr(target_user, "is_bot", False):
        await message.reply(
            "❌ <b>Bots cannot be added to the auction pool.</b>"
        )
        return

    target_user_id = target_user.id

    #===== CHECK GROUP MEMBERSHIP =====

    try:

        target_member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id
        )

    except Exception:

        await message.reply(
            "❌ This user is not a member of this group."
        )
        return

    if getattr(target_member.user, "is_bot", False):
        await message.reply(
            "❌ <b>Bots cannot be added to the auction pool.</b>"
        )
        return

    #===== USER DATA =====

    first_name = (
        target_member.user.first_name
        or "Unknown"
    )

    username = target_member.user.username

    #===== CHECK DUPLICATE =====

    players = tournament.get("players", [])

    for player in players:

        if player.get("user_id") == target_user_id:

            await message.reply(
                f"⚠️ <a href=\"tg://user?id={target_user_id}\">"
                f"{first_name}</a> "
                "is already in the auction pool."
            )
            return

    #===== ADD PLAYER =====

    players.append({
        "user_id": target_user_id,
        "username": username,
        "first_name": first_name,
        "display_name": first_name,
        "registered_at": int(time.time())
    })

    tournament["players"] = players

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #===== SUCCESS =====

    mention = (
        f'<a href="tg://user?id={target_user_id}">'
        f'{first_name}'
        f'</a>'
    )

    await message.reply(
        "🏏 <b>PLAYER ADDED</b>\n\n"
        f"👤 Player : {mention}\n"
        f"🏆 Tournament : "
        f"<b>{tournament.get('name', 'Unknown')}</b>\n"
        f"👥 Auction Pool : <b>{len(players)}</b>"
    )
    
                                                    
#===== REMOVE PLAYER FROM AUCTION POOL =====

@router.message(Command("remove_player"))
async def remove_player_command(message: Message):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ <b>/remove_player</b> can only be used inside a group."
        )
        return

    #===== FIND TOURNAMENT FIRST =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None

    for item in tournaments:
        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in ("ENDED", "CANCELLED")
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ <b>No active tournament found</b> in this group."
        )
        return

    #===== HOST CHECK =====

    if tournament.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ Only the <b>Tournament Host</b> can remove players."
        )
        return

    #===== FIND TARGET =====

    target_user = None

    #===== REPLY METHOD =====

    if message.reply_to_message:

        target_user = message.reply_to_message.from_user

        if not target_user:
            await message.reply(
                "❌ Could not identify the user."
            )
            return

    #===== ID / USERNAME METHOD =====

    else:

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await message.reply(
                "❌ <b>How to use:</b>\n\n"
                "Reply to a user:\n"
                "<code>/remove_player</code>\n\n"
                "User ID:\n"
                "<code>/remove_player 123456789</code>\n\n"
                "Username:\n"
                "<code>/remove_player @username</code>"
            )
            return

        target = args[1].strip()

        #===== USER ID =====

        if target.isdigit():

            try:
                target_user = await message.bot.get_chat(
                    int(target)
                )
            except Exception:
                await message.reply(
                    "❌ Unable to find that Telegram user ID."
                )
                return

        #===== USERNAME =====

        else:

            username = target.lstrip("@")

            try:
                target_user = await message.bot.get_chat(
                    f"@{username}"
                )
            except Exception:
                await message.reply(
                    "❌ Unable to find that username.\n\n"
                    "💡 Try replying to the user's message."
                )
                return

    #===== TARGET ID =====

    target_user_id = target_user.id

    #===== FIND PLAYER IN POOL =====

    players = tournament.get("players", [])

    player_found = None

    for player in players:

        if player.get("user_id") == target_user_id:
            player_found = player
            break

    if not player_found:

        first_name = (
            getattr(target_user, "first_name", None)
            or "Unknown"
        )

        await message.reply(
            f"❌ <a href=\"tg://user?id={target_user_id}\">"
            f"{first_name}</a> "
            "is not in the auction pool."
        )
        return

    #===== REMOVE PLAYER =====

    players.remove(player_found)

    tournament["players"] = players

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #===== PLAYER NAME =====

    first_name = (
        player_found.get("first_name")
        or getattr(target_user, "first_name", None)
        or "Unknown"
    )

    mention = (
        f'<a href="tg://user?id={target_user_id}">'
        f'{first_name}'
        f'</a>'
    )

    #===== SUCCESS =====

    await message.reply(
        "🗑️ <b>PLAYER REMOVED</b>\n\n"
        f"👤 Player : {mention}\n"
        f"🏆 Tournament : "
        f"<b>{tournament.get('name', 'Unknown')}</b>\n"
        f"👥 Auction Pool : <b>{len(players)}</b>"
    )
    
                                                                                        
#===== CREATE TOURNAMENT TEAM =====

def generate_team_short_code(team_name, existing_codes):

    #===== CLEAN TEAM NAME =====

    words = [
        word.strip().upper()
        for word in team_name.split()
        if word.strip()
    ]

    if not words:
        return "TM"

    #===== ALREADY SHORT NAME =====

    if len(words) == 1 and 2 <= len(words[0]) <= 4:
        base_code = words[0]
    else:

        #===== BUILD INITIALS =====

        base_code = "".join(
            word[0]
            for word in words
        )

        # Maximum 4 letters
        base_code = base_code[:4]

        # Fallback
        if len(base_code) < 2:

            letters = "".join(words)

            base_code = letters[:2]

    #===== MAKE UNIQUE =====

    code = base_code

    counter = 2

    while code.upper() in existing_codes:

        code = f"{base_code}{counter}"

        counter += 1

    return code


@router.message(Command("create_team"))
async def create_tournament_team_command(
    message: Message
):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):

        await message.reply(
            "❌ <b>/create_team</b> can only be used inside a group."
        )

        return


    #===== FIND CURRENT TOURNAMENT =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        tournaments = []


    tournament = None
    tournament_index = None


    # Search newest tournament first

    for index in range(
        len(tournaments) - 1,
        -1,
        -1
    ):

        item = tournaments[index]

        if not isinstance(
            item,
            dict
        ):

            continue


        if (
            item.get("chat_id")
            == message.chat.id
            and item.get("status")
            not in (
                "ENDED",
                "CANCELLED"
            )
        ):

            tournament = item
            tournament_index = index

            break


    if not tournament:

        await message.reply(
            "❌ <b>No active tournament found</b> in this group."
        )

        return


    #===== HOST CHECK =====

    if (
        tournament.get("host_id")
        != message.from_user.id
    ):

        await message.reply(
            "❌ Only the <b>Tournament Host</b> can create teams."
        )

        return


    #===== REGISTRATION CHECK =====

    if (
        tournament.get("status")
        != "REGISTRATION_ENDED"
    ):

        await message.reply(
            "❌ Registration must be ended first.\n\n"
            "Use <code>/endregistration</code>."
        )

        return


    #===== COMMAND ARGUMENTS =====

    args = message.text.split()


    if len(args) < 2:

        await message.reply(
            "❌ <b>Invalid Usage</b>\n\n"

            "Reply to the captain's message:\n"
            "<code>/create_team CSK</code>\n\n"

            "Or use Telegram User ID:\n"
            "<code>/create_team CSK 123456789</code>"
        )

        return


    #===== TEAM NAME + USER ID =====

    if len(args) >= 3 and args[-1].isdigit():

        team_name = " ".join(
            args[1:-1]
        ).strip()

        target_user_id = int(
            args[-1]
        )

    else:

        team_name = " ".join(
            args[1:]
        ).strip()

        target_user_id = None


    #===== FIND CAPTAIN =====

    target_user = None


    # Reply method

    if message.reply_to_message:

        target_user = (
            message.reply_to_message.from_user
        )


    # ID method

    elif target_user_id is not None:

        try:

            target_user = await message.bot.get_chat(
                target_user_id
            )

        except Exception:

            await message.reply(
                "❌ Unable to find that Telegram user ID."
            )

            return


    else:

        await message.reply(
            "❌ <b>Captain is required.</b>\n\n"

            "Reply to the captain's message:\n"
            "<code>/create_team CSK</code>\n\n"

            "Or use Telegram User ID:\n"
            "<code>/create_team CSK 123456789</code>"
        )

        return


    #===== VALIDATE USER =====

    if not target_user:

        await message.reply(
            "❌ Could not identify the captain."
        )

        return


    if getattr(
        target_user,
        "is_bot",
        False
    ):

        await message.reply(
            "❌ A bot cannot be a team manager."
        )

        return


    captain_id = target_user.id


    #===== CHECK REGISTERED PLAYER =====

    registered_players = tournament.get(
        "players",
        []
    )


    if not isinstance(
        registered_players,
        list
    ):

        registered_players = []


    registered = False


    for player in registered_players:

        if not isinstance(
            player,
            dict
        ):

            continue


        player_id = player.get(
            "user_id"
        )


        try:

            if (
                player_id is not None
                and int(player_id)
                == int(captain_id)
            ):

                registered = True

                break

        except (
            TypeError,
            ValueError
        ):

            continue


    if not registered:

        await message.reply(
            "❌ This user is not registered "
            "in the tournament."
        )

        return


    #===== GET TEAMS =====

    teams = tournament.get(
        "teams",
        []
    )


    if not isinstance(
        teams,
        list
    ):

        teams = []


    #===== CHECK DUPLICATE TEAM NAME =====

    for team in teams:

        if not isinstance(
            team,
            dict
        ):

            continue


        existing_name = str(
            team.get(
                "name",
                ""
            )
        ).strip()


        if (
            existing_name
            and existing_name.lower()
            == team_name.lower()
        ):

            await message.reply(
                "❌ A team with this name "
                "already exists."
            )

            return


    #===== CHECK CAPTAIN ALREADY ASSIGNED =====

    for team in teams:

        if not isinstance(
            team,
            dict
        ):

            continue


        existing_manager_id = team.get(
            "manager_id"
        )


        try:

            if (
                existing_manager_id is not None
                and int(existing_manager_id)
                == int(captain_id)
            ):

                await message.reply(
                    "❌ This captain is already "
                    "assigned to a team."
                )

                return

        except (
            TypeError,
            ValueError
        ):

            continue


    #===== GET EXISTING SHORT CODES =====

    existing_codes = set()


    for team in teams:

        if not isinstance(
            team,
            dict
        ):

            continue


        short_code = team.get(
            "short_code"
        )


        if short_code:

            existing_codes.add(
                str(short_code).upper()
            )


    #===== GENERATE SHORT CODE =====

    short_code = generate_team_short_code(
        team_name,
        existing_codes
    )


    #===== MANAGER NAME =====

    manager_name = (
        target_user.first_name
        or target_user.full_name
        or "Unknown"
    )


    #===== MANAGER USERNAME =====

    manager_username = None


    if getattr(
        target_user,
        "username",
        None
    ):

        manager_username = (
            f"@{target_user.username}"
        )


    #===== CREATE TEAM =====

    new_team = {

        "name":
            team_name,

        "short_code":
            short_code,

        "manager_id":
            captain_id,

        "manager_username":
            manager_username,

        "manager_name":
            manager_name,

        "purse":
            0.0,

        "players":
            []
    }


    teams.append(
        new_team
    )


    tournament["teams"] = teams


    tournaments[tournament_index] = (
        tournament
    )


    #===== SAVE TOURNAMENT =====

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    #===== MANAGER DISPLAY =====

    manager_display = (
        manager_username
        or manager_name
    )


    #===== SUCCESS =====

    if short_code.upper() == team_name.upper():

        team_display = (
            f"🏏 <b>{short_code}</b>"
        )

    else:

        team_display = (
            f"🏏 <b>{short_code}</b> "
            f"— <b>{team_name}</b>"
        )


    await message.reply(

        "✅ <b>TEAM CREATED!</b>\n\n"

        f"{team_display}\n"

        f"👑 Manager : "
        f"<b>{manager_display}</b>\n"

        f"💰 Purse : "
        f"<b>₹0 Cr</b>\n"

        f"👥 Players : "
        f"<b>0</b>"
    )
    


                          
                                                                                                                                        
#===== REMOVE TOURNAMENT TEAM =====

@router.message(
    Command("remove_tourteam")
)
async def remove_tourteam_command(
    message: Message
):

    save_chat(
        message
    )


    #===== GROUP ONLY =====

    if not is_group(
        message
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
            "<code>/remove_tourteam SHORT_CODE</code>\n\n"
            "Example:\n"
            "<code>/remove_tourteam PB</code>"
        )

        return


    team_code = args[1].strip().upper()


    #===== FIND TOURNAMENT =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        await message.reply(
            "❌ No tournaments found."
        )

        return


    tournament = None

    for tour in reversed(tournaments):

        if (
            tour.get("chat_id") == message.chat.id
            and tour.get("status") not in (
                "ENDED",
                "CANCELLED"
            )
        ):

            tournament = tour

            break


    if tournament is None:

        await message.reply(
            "❌ No active tournament found."
        )

        return


    #===== FIND TEAM =====

    teams = tournament.get(
        "teams",
        []
    )

    team_index = None

    for index, team in enumerate(teams):

        if (
            str(
                team.get("short_code", "")
            ).upper()
            == team_code
        ):

            team_index = index

            break


    if team_index is None:

        await message.reply(
            f"❌ Tournament team "
            f"<b>{team_code}</b> not found."
        )

        return


    #===== REMOVE TEAM =====

    team = teams[team_index]

    team_name = team.get(
        "name",
        team_code
    )

    manager_name = team.get(
        "manager_name",
        team.get(
            "manager_username",
            "Unknown"
        )
    )


    teams.pop(
        team_index
    )


    tournament["teams"] = teams


    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    #===== SUCCESS =====

    await message.reply(
        "✅ <b>TOURNAMENT TEAM REMOVED!</b>\n\n"
        f"🏏 <b>{team_code}</b>"
        + (
            f" — {team_name}"
            if team_name.upper() != team_code
            else ""
        )
        + "\n"
        f"👑 Manager : {manager_name}"
    )           
    

#===== LIST TOURNAMENT TEAMS =====

@router.message(
    Command("list_team")
)
async def list_tournament_teams_command(
    message: Message
):

    save_chat(
        message
    )


    #===== GROUP ONLY =====

    if not is_group(
        message
    ):

        await message.reply(
            "❌ This command can only be used in Telegram groups."
        )

        return


    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        await message.reply(
            "📭 No tournament found."
        )

        return


    #===== FIND CURRENT TOURNAMENT =====

    tournament = None

    for tour in reversed(tournaments):

        if (
            tour.get("chat_id") == message.chat.id
            and tour.get("status") not in (
                "ENDED",
                "CANCELLED"
            )
        ):

            tournament = tour

            break


    if tournament is None:

        await message.reply(
            "📭 No active tournament found."
        )

        return


    teams = tournament.get(
        "teams",
        []
    )


    if not teams:

        await message.reply(
            "📭 No tournament teams have been created yet."
        )

        return


    #===== BUILD LIST =====

    text = (
        "🏆 <b>TOURNAMENT TEAMS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )


    for index, team in enumerate(
        teams,
        start=1
    ):

        name = team.get(
            "name",
            "Unknown"
        )

        short_code = team.get(
            "short_code",
            name
        )

        manager = team.get(
            "manager_name",
            team.get(
                "manager_username",
                "Not Assigned"
            )
        )

        purse_lakhs = float(
            team.get(
                "purse_lakhs",
                team.get("purse", 0)
            )
        )

        purse_crore = purse_lakhs / 100

        players = team.get(
            "players",
            []
        )


        display_name = (
            f"{short_code} — {name}"
            if name.upper() != short_code.upper()
            else short_code
        )


        text += (
            f"{index}. 🏏 <b>{display_name}</b>\n"
            f"👑 Manager : <b>{manager}</b>\n"
            f"💰 Purse : <b>₹{purse_crore:.2f} Cr</b>\n"
            f"👥 Squad : <b>{len(players) + 1} / {tournament.get('squad_size', 0)}</b>\n\n"
        )


    await message.reply(
        text
    )                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
#===== END REGISTRATION =====

@router.message(Command("endregistration"))
async def end_registration_command(message: Message):

    save_user(message)
    save_chat(message)

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ <b>/endregistration</b> can only be used inside a group."
        )
        return

    #===== FIND TOURNAMENT =====

    tournaments = load_json(TOURNAMENTS_FILE)

    tournament = None
    tournament_index = None

    for index, item in enumerate(tournaments):

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status")
            not in ("ENDED", "CANCELLED")
        ):
            tournament = item
            tournament_index = index
            break

    if not tournament:
        await message.reply(
            "❌ <b>No active tournament found</b> in this group."
        )
        return

    #===== HOST CHECK =====

    if tournament.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ Only the <b>Tournament Host</b> can end registration."
        )
        return

    #===== ALREADY CLOSED =====

    if tournament.get("status") == "REGISTRATION_ENDED":

        await message.reply(
            "⚠️ <b>Registration is already closed.</b>"
        )
        return

    #===== CHECK POOL =====

    players = tournament.get("players", [])

    if not players:

        await message.reply(
            "⚠️ <b>Auction pool is empty.</b>\n\n"
            "Add players before ending registration."
        )
        return

    #===== CLOSE REGISTRATION =====

    tournament["status"] = "REGISTRATION_ENDED"

    tournaments[tournament_index] = tournament

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #===== SUCCESS =====

    await message.reply(
        "🔒 <b>REGISTRATION CLOSED</b>\n\n"
        f"🏆 Tournament : "
        f"<b>{tournament.get('name', 'Unknown')}</b>\n"
        f"🔑 Code : "
        f"<code>{tournament.get('code', 'N/A')}</code>\n"
        f"👥 Auction Pool : <b>{len(players)}</b>\n\n"
        "❌ <b>/register</b> is now disabled.\n"
        "✅ Host can still manage the auction pool."
    )                                                                                                                                                                                                                                                                  #===== END TOURNAMENT =====

@router.message(Command("endtour"))
async def end_tournament(message: Message):
    # Group only
    if not is_group(message):
        await message.reply(
            "❌ This command can only be used in a group."
        )
        return

    tournaments = load_json(TOURNAMENTS_FILE)

    # Find tournament for this group
    tournament = None

    for item in tournaments:
        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") not in ["ENDED", "CANCELLED"]
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ No active tournament found in this group."
        )
        return

    # Host only
    if tournament.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ Only the Tournament Host can end the tournament."
        )
        return

    # Registration must be ended first
    if tournament.get("status") != "REGISTRATION_ENDED":
        await message.reply(
            "❌ You must use /endregistration before ending the tournament."
        )
        return

    # Confirmation buttons
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 End Tournament",
                    callback_data=f"endtour:confirm:{tournament['code']}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"endtour:cancel:{tournament['code']}"
                )
            ]
        ]
    )

    await message.reply(
        "⚠️ <b>END TOURNAMENT?</b>\n\n"
        f"🏆 Tournament : <b>{tournament['name']}</b>\n"
        f"🔑 Code : <code>{tournament['code']}</code>\n"
        f"👥 Players : <b>{len(tournament.get('players', []))}</b>\n\n"
        "🔒 Once ended, this tournament cannot be reopened.\n"
        "Are you sure?",
        reply_markup=keyboard
    )



    

    
                  

                                
#===== SHOW TOURNAMENT SET PAGE =====

async def show_tournament_set_page(
    message,
    tour_code,
    set_files,
    page
):

    #===== PAGE VALIDATION =====

    total_pages = len(set_files)

    if total_pages == 0:
        await message.reply(
            "❌ No tournament sets available."
        )
        return

    if page < 0:
        page = 0

    if page >= total_pages:
        page = total_pages - 1

    #===== TOURNAMENT SET FOLDER =====

    tour_folder = os.path.join(
        TOURSETS_FOLDER,
        str(tour_code)
    )

    selected_file = set_files[page]

    set_path = os.path.join(
        tour_folder,
        selected_file
    )

    #===== LOAD SET =====

    set_data = load_json(
        set_path
    )

    #===== SUPPORT LIST OR DICT FORMAT =====

    if isinstance(set_data, list):

        players = set_data

        set_number = page + 1

    elif isinstance(set_data, dict):

        players = set_data.get(
            "players",
            []
        )

        set_number = set_data.get(
            "set_number",
            page + 1
        )

    else:

        await message.reply(
            "❌ Invalid tournament set."
        )
        return

    #===== PLAYERS VALIDATION =====

    if not isinstance(players, list):
        await message.reply(
            "❌ Invalid player data in tournament set."
        )
        return

    #===== BUILD SET TEXT =====

    text = (
        "🏆 <b>TOURNAMENT SET</b>\n\n"
        f"🔑 Code : <code>{tour_code}</code>\n"
        f"📦 <b>Set {set_number}</b>\n"
        f"👥 Players : <b>{len(players)}</b>\n\n"
    )

    #===== PLAYER LIST =====

    for index, player in enumerate(
        players,
        start=1
    ):

        if isinstance(player, dict):

            name = (
                player.get("first_name")
                or player.get("name")
                or player.get("username")
                or "Unknown"
            )

            user_id = player.get(
                "user_id"
            )

            if user_id:

                text += (
                    f'{index}. '
                    f'<a href="tg://user?id={user_id}">'
                    f'{name}'
                    f'</a>\n'
                )

            else:

                text += (
                    f"{index}. {name}\n"
                )

        else:

            text += (
                f"{index}. {player}\n"
            )

    #===== NAVIGATION KEYBOARD =====

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

    #===== SEND SET MESSAGE =====

    sent_message = await message.reply(
        text,
        reply_markup=keyboard
    )

    #===== PIN SET MESSAGE =====

    try:

        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=sent_message.message_id,
            disable_notification=True
        )

    except Exception as e:

        print(
            "TOUR SET PIN ERROR:",
            e
        )                                                         
                                                                                                                                
#===== TOURNAMENT SETS =====

@router.message(Command("toursets"))
async def tournament_sets_command(message: Message):

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ This command can only be used in a group."
        )
        return

    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(tournaments, list):
        tournaments = []

    #===== FIND CURRENT TOURNAMENT =====

    tournament = None

    # Search from newest to oldest
    for item in reversed(tournaments):

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") == "REGISTRATION_ENDED"
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ No active tournament found for this group."
        )
        return

    #===== GET CURRENT TOURNAMENT CODE =====

    tour_code = tournament.get(
        "code"
    )

    if not tour_code:
        await message.reply(
            "❌ Tournament code not found."
        )
        return

    #===== CURRENT TOURNAMENT SET FOLDER =====

    tour_folder = os.path.join(
        TOURSETS_FOLDER,
        str(tour_code)
    )

    if not os.path.exists(
        tour_folder
    ):
        await message.reply(
            "❌ Tournament sets have not been created yet."
        )
        return

    #===== GET SET FILES =====

    set_files = []

    for filename in os.listdir(
        tour_folder
    ):

        if (
            filename.startswith("set")
            and filename.endswith(".json")
        ):
            set_files.append(
                filename
            )

    #===== SORT SETS =====

    set_files.sort(
        key=lambda x: int(
            x[3:-5]
        )
    )

    if not set_files:
        await message.reply(
            "❌ No tournament sets available."
        )
        return

    #===== SHOW FIRST SET =====

    await show_tournament_set_page(
        message,
        tour_code,
        set_files,
        0
    )
    
                                                                                        #===== TOURNAMENT SET LIMITS =====

@router.message(
    Command("setlimits")
)
async def setlimits_command(
    message: Message,
    state: FSMContext
):

    #===== GROUP ONLY =====

    if not is_group(message):
        await message.reply(
            "❌ This command can only be used in a group."
        )
        return


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
            item.get("chat_id") == message.chat.id
            and item.get("status") not in [
                "ENDED",
                "CANCELLED"
            ]
        ):
            tournament = item
            break


    if not tournament:

        await message.reply(
            "❌ No active tournament found in this group."
        )

        return


    #===== HOST ONLY =====

    if message.from_user.id != tournament.get(
        "host_id"
    ):

        await message.reply(
            "❌ Only the Tournament Host can use /setlimits."
        )

        return


    #===== AUCTION START CHECK =====

    if tournament.get("auction_started") is True:

        await message.reply(
            "❌ <b>TOURNAMENT AUCTION ALREADY STARTED</b>\n\n"
            "Squad size and base price can no longer be changed."
        )

        return


    #===== CHECK EXISTING SETTINGS =====

    squad_size = tournament.get(
        "squad_size"
    )

    base_price = tournament.get(
        "base_price_lakhs"
    )


    #===== FIRST TIME =====

    if squad_size is None:

        text = (
            "🏆 <b>TOURNAMENT SET LIMITS</b>\n\n"
            "👥 Select Squad Size:"
        )

    else:

        text = (
            "🏆 <b>TOURNAMENT SET LIMITS</b>\n\n"
            f"👥 Squad Size : <b>{squad_size}</b>\n"
            f"💰 Base Price : "
            f"<b>₹{base_price} Lakhs</b>\n\n"
            "Select a new squad size:"
        )


    #===== SQUAD BUTTONS =====

    buttons = [

        [
            InlineKeyboardButton(
                text="5",
                callback_data="tourlimit:size:5"
            ),
            InlineKeyboardButton(
                text="7",
                callback_data="tourlimit:size:7"
            ),
            InlineKeyboardButton(
                text="8",
                callback_data="tourlimit:size:8"
            )
        ],

        [
            InlineKeyboardButton(
                text="10",
                callback_data="tourlimit:size:10"
            ),
            InlineKeyboardButton(
                text="15",
                callback_data="tourlimit:size:15"
            )
        ],

        [
            InlineKeyboardButton(
                text="Custom Size",
                callback_data="tourlimit:custom"
            )
        ]
    ]


    #===== SAVE BUTTON ONLY AFTER FIRST SETUP =====

    if squad_size is not None:

        buttons.append(
            [
                InlineKeyboardButton(
                    text="Save ✅",
                    callback_data="tourlimit:save"
                )
            ]
        )


    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )
    
                                                                            
#===== CONVERT TOURNAMENT SETS =====

@router.message(Command("convertsets"))
async def convert_sets_command(message: Message):

    #----- GROUP ONLY -----

    if not is_group(message):
        await message.reply(
            "❌ This command can only be used in a group."
        )
        return

    #----- LOAD TOURNAMENTS -----

    tournaments = load_json(TOURNAMENTS_FILE)

    if not isinstance(tournaments, list):
        tournaments = []

    #----- FIND CURRENT GROUP TOURNAMENT -----

    tournament = None

    for item in tournaments:
        if item.get("chat_id") == message.chat.id:
            if item.get("status") != "ENDED":
                tournament = item
                break

    if not tournament:
        await message.reply(
            "❌ No active tournament found for this group."
        )
        return

    #----- HOST ONLY -----

    if message.from_user.id != tournament.get("host_id"):
        await message.reply(
            "❌ Only the Tournament Host can use this command."
        )
        return

    #----- REGISTRATION MUST BE ENDED -----

    if tournament.get("status") != "REGISTRATION_ENDED":
        await message.reply(
            "❌ Registration must be ended before converting the player pool."
        )
        return

    #----- GET CURRENT TOURNAMENT CODE -----

    tour_code = str(tournament.get("code"))

    # IMPORTANT:
    # Each tournament gets its OWN folder.
    # Old tournament folders are completely ignored.

    tour_folder = os.path.join(
        TOURSETS_FOLDER,
        tour_code
    )

    #----- CHECK ONLY CURRENT TOURNAMENT FOLDER -----

    existing_sets = []

    if os.path.exists(tour_folder):

        for filename in os.listdir(tour_folder):

            if (
                filename.startswith("set")
                and filename.endswith(".json")
            ):
                existing_sets.append(filename)

    # If THIS tournament already has sets, block conversion.
    if existing_sets:

        existing_sets.sort(
            key=lambda x: int(x[3:-5])
        )

        await message.reply(
            f"❌ <b>PLAYER POOL ALREADY CONVERTED</b>\n\n"
            f"🔑 Code : <code>{tour_code}</code>\n"
            f"📦 Sets : <b>{len(existing_sets)}</b>"
        )
        return

    #----- GET PLAYER POOL -----

    players = tournament.get("players", [])

    if not isinstance(players, list) or not players:

        await message.reply(
            "❌ Tournament player pool is empty."
        )
        return

    #----- CREATE CURRENT TOURNAMENT FOLDER -----

    os.makedirs(
        tour_folder,
        exist_ok=True
    )

    #----- SPLIT PLAYERS INTO SETS OF 20 -----

    SET_SIZE = 20

    set_count = 0

    for start in range(0, len(players), SET_SIZE):

        set_count += 1

        set_players = players[
            start:start + SET_SIZE
        ]

        set_file = os.path.join(
            tour_folder,
            f"set{set_count}.json"
        )

        save_json(
            set_file,
            set_players
        )

    #----- SAVE CONVERSION STATUS -----

    tournament["sets_converted"] = True
    tournament["set_count"] = set_count

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #----- SUCCESS -----

    await message.reply(
        f"✅ <b>PLAYER POOL CONVERTED</b>\n\n"
        f"🏆 Tournament : <b>{tournament.get('name')}</b>\n"
        f"🔑 Code : <code>{tour_code}</code>\n"
        f"👥 Players : <b>{len(players)}</b>\n"
        f"📦 Sets Created : <b>{set_count}</b>\n"
        f"👤 Players / Set : <b>{SET_SIZE}</b>\n\n"
        f"📁 Folder : <code>toursets/{tour_code}/</code>"
    )
    
    
                                                                        
#===== ADD TOURNAMENT PURSE =====

@router.message(
    Command("add_purse")
)
async def add_tournament_purse_command(
    message: Message
):

    save_chat(
        message
    )


    #===== GROUP ONLY =====

    if not is_group(
        message
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

    if len(args) != 3:

        await message.reply(
            "❌ Invalid Usage\n\n"
            "<code>/add_purse SHORT_CODE AMOUNT</code>\n\n"
            "Amount is in Lakhs.\n\n"
            "Example:\n"
            "<code>/add_purse PB 120</code>"
        )

        return


    short_code = args[1].strip().upper()


    #===== CHECK AMOUNT =====

    try:

        amount_lakhs = float(
            args[2]
        )

    except ValueError:

        await message.reply(
            "❌ Amount must be a valid number.\n\n"
            "Example:\n"
            "<code>/add_purse PB 120</code>"
        )

        return


    if amount_lakhs <= 0:

        await message.reply(
            "❌ Amount must be greater than 0."
        )

        return


    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        await message.reply(
            "📭 No tournament found."
        )

        return


    #===== FIND CURRENT TOURNAMENT =====

    tournament = None

    for tour in reversed(tournaments):

        if (
            tour.get("chat_id") == message.chat.id
            and tour.get("status") not in (
                "ENDED",
                "CANCELLED"
            )
        ):

            tournament = tour

            break


    if tournament is None:

        await message.reply(
            "📭 No active tournament found."
        )

        return


    #===== FIND TEAM =====

    team = None

    for item in tournament.get(
        "teams",
        []
    ):

        if str(
            item.get(
                "short_code",
                ""
            )
        ).upper() == short_code:

            team = item

            break


    if team is None:

        await message.reply(
            f"❌ Tournament team "
            f"<b>{short_code}</b> not found."
        )

        return


    #===== GET OLD PURSE =====

    old_purse_lakhs = float(
        team.get(
            "purse_lakhs",
            0
        )
    )


    #===== ADD PURSE =====

    new_purse_lakhs = (
        old_purse_lakhs
        + amount_lakhs
    )


    team["purse_lakhs"] = (
        new_purse_lakhs
    )


    #===== SAVE =====

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    #===== DISPLAY NAME =====

    team_name = team.get(
        "name",
        short_code
    )


    display_name = (
        f"{short_code} — {team_name}"
        if team_name.upper() != short_code
        else short_code
    )


    #===== CONVERT TO CRORE FOR DISPLAY =====

    total_crore = (
        new_purse_lakhs / 100
    )


    #===== SUCCESS =====

    await message.reply(
        "💰 <b>PURSE ADDED!</b>\n\n"
        f"🏏 <b>{display_name}</b>\n"
        f"➕ Added : <b>₹{amount_lakhs:.2f} Lakhs</b>\n"
        f"💰 Total Purse : "
        f"<b>₹{new_purse_lakhs:.2f} Lakhs</b>\n"
        f"💵 Value : "
        f"<b>₹{total_crore:.2f} Cr</b>"
    )
    
   
                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
#===== REMOVE TOURNAMENT PURSE =====

@router.message(
    Command("rn_purse")
)
async def remove_tournament_purse_command(
    message: Message
):

    save_chat(
        message
    )


    #===== GROUP ONLY =====

    if not is_group(
        message
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

    if len(args) != 3:

        await message.reply(
            "❌ Invalid Usage\n\n"
            "<code>/rn_purse SHORT_CODE AMOUNT</code>\n\n"
            "Amount is in Lakhs.\n\n"
            "Example:\n"
            "<code>/rn_purse PB 20</code>"
        )

        return


    short_code = args[1].strip().upper()


    #===== CHECK AMOUNT =====

    try:

        amount_lakhs = float(
            args[2]
        )

    except ValueError:

        await message.reply(
            "❌ Amount must be a valid number.\n\n"
            "Example:\n"
            "<code>/rn_purse PB 20</code>"
        )

        return


    if amount_lakhs <= 0:

        await message.reply(
            "❌ Amount must be greater than 0."
        )

        return


    #===== LOAD TOURNAMENTS =====

    tournaments = load_json(
        TOURNAMENTS_FILE
    )

    if not isinstance(
        tournaments,
        list
    ):

        await message.reply(
            "📭 No tournament found."
        )

        return


    #===== FIND CURRENT TOURNAMENT =====

    tournament = None

    for tour in reversed(tournaments):

        if (
            tour.get("chat_id") == message.chat.id
            and tour.get("status") not in (
                "ENDED",
                "CANCELLED"
            )
        ):

            tournament = tour

            break


    if tournament is None:

        await message.reply(
            "📭 No active tournament found."
        )

        return


    #===== FIND TEAM =====

    team = None

    for item in tournament.get(
        "teams",
        []
    ):

        if str(
            item.get(
                "short_code",
                ""
            )
        ).upper() == short_code:

            team = item

            break


    if team is None:

        await message.reply(
            f"❌ Tournament team "
            f"<b>{short_code}</b> not found."
        )

        return


    #===== CURRENT PURSE =====

    current_purse_lakhs = float(
        team.get(
            "purse_lakhs",
            0
        )
    )


    #===== CHECK AVAILABLE PURSE =====

    if amount_lakhs > current_purse_lakhs:

        await message.reply(
            "❌ <b>Insufficient Purse!</b>\n\n"
            f"🏏 Team : <b>{short_code}</b>\n"
            f"💰 Available : "
            f"<b>₹{current_purse_lakhs:.2f} Lakhs</b>\n"
            f"➖ Requested : "
            f"<b>₹{amount_lakhs:.2f} Lakhs</b>"
        )

        return


    #===== REMOVE PURSE =====

    new_purse_lakhs = (
        current_purse_lakhs
        - amount_lakhs
    )


    team["purse_lakhs"] = (
        new_purse_lakhs
    )


    #===== SAVE =====

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )


    #===== DISPLAY NAME =====

    team_name = team.get(
        "name",
        short_code
    )


    display_name = (
        f"{short_code} — {team_name}"
        if team_name.upper() != short_code
        else short_code
    )


    #===== CONVERT TO CRORE =====

    total_crore = (
        new_purse_lakhs / 100
    )


    #===== SUCCESS =====

    await message.reply(
        "💰 <b>PURSE REMOVED!</b>\n\n"
        f"🏏 <b>{display_name}</b>\n"
        f"➖ Removed : "
        f"<b>₹{amount_lakhs:.2f} Lakhs</b>\n"
        f"💰 Remaining : "
        f"<b>₹{new_purse_lakhs:.2f} Lakhs</b>\n"
        f"💵 Value : "
        f"<b>₹{total_crore:.2f} Cr</b>"
    )                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
#===== TOURNAMENT AUCTION SETUP =====

@router.message(Command("tourauction"))
async def tournament_auction_command(message: Message):

    #----- GROUP ONLY -----

    if not is_group(message):
        await message.reply(
            "❌ This command can only be used in a group."
        )
        return

    #----- LOAD TOURNAMENTS -----

    tournaments = load_json(TOURNAMENTS_FILE)

    if not isinstance(tournaments, list):
        tournaments = []

    #===== FIND CURRENT GROUP TOURNAMENT =====

    tournament = None

    for item in reversed(tournaments):

        if (
            item.get("chat_id") == message.chat.id
            and item.get("status") == "REGISTRATION_ENDED"
        ):
            tournament = item
            break

    if not tournament:
        await message.reply(
            "❌ No active tournament found for this group."
        )
        return

    #----- HOST ONLY -----

    if message.from_user.id != tournament.get("host_id"):
        await message.reply(
            "❌ Only the Tournament Host can use this command."
        )
        return

    #----- REGISTRATION CHECK -----

    if tournament.get("status") != "REGISTRATION_ENDED":
        await message.reply(
            "❌ Registration must be ended first.\n\n"
            "Use <code>/endregistration</code>."
        )
        return

    #----- GET TOURNAMENT CODE -----

    tour_code = str(
        tournament.get("code")
    )

    #----- CURRENT TOURNAMENT SET FOLDER -----

    tour_folder = os.path.join(
        TOURSETS_FOLDER,
        tour_code
    )

    #----- FIND ONLY CURRENT TOURNAMENT SETS -----

    set_files = []

    if os.path.exists(tour_folder):

        for filename in os.listdir(tour_folder):

            if (
                filename.startswith("set")
                and filename.endswith(".json")
            ):
                set_files.append(filename)

    set_files.sort(
        key=lambda x: int(x[3:-5])
    )

    #----- SET CHECK -----

    if not set_files:

        await message.reply(
            "❌ <b>TOURNAMENT SETS NOT CREATED</b>\n\n"
            f"🔑 Code : <code>{tour_code}</code>\n\n"
            "Use <code>/convertsets</code> first."
        )
        return

    #----- LIMIT CHECK -----

    squad_size = tournament.get(
        "squad_size"
    )

    base_price = tournament.get(
        "base_price_lakhs"
    )

    if (
        squad_size is None
        or base_price is None
    ):
        await message.reply(
            "❌ <b>TOURNAMENT LIMITS NOT SET</b>\n\n"
            "Use <code>/setlimits</code> first."
        )
        return

    #----- PLAYER COUNT -----

    players = tournament.get(
        "players",
        []
    )

    player_count = len(players)

    #----- SET COUNT -----

    set_count = len(set_files)

    #----- SAVE CURRENT AUCTION SETUP -----

    tournament["auction_setup"] = {
        "status": "SETUP",
        "selected_set": 1,
        "squad_size": squad_size,
        "base_price": base_price
    }

    save_json(
        TOURNAMENTS_FILE,
        tournaments
    )

    #----- KEYBOARD -----

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📦 Select Set",
                    callback_data=f"tourauction:set:{tour_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⚙️ Auction Settings",
                    callback_data=f"tourauction:settings:{tour_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="▶️ Start Auction",
                    callback_data=f"tourauction:start:{tour_code}"
                )
            ],

            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"tourauction:cancel:{tour_code}"
                )
            ]

        ]
    )

    #----- SETUP MESSAGE -----

    await message.reply(

        "🏆 <b>TOURNAMENT AUCTION SETUP</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"🔑 Code : <code>{tour_code}</code>\n"
        f"👥 Squad Size : <b>{squad_size}</b>\n"
        f"💰 Base Price : <b>₹{base_price} Lakhs</b>\n"
        f"👤 Players : <b>{player_count}</b>\n"
        f"📦 Player Sets : <b>{set_count}</b>\n\n"

        "📌 <b>Selected Set : 1</b>\n\n"

        "Choose an option below:",

        reply_markup=keyboard
    )                                                                                                                     

        
                                                                                           
#===== GET EMOJI PACK IDs =====

@router.message(Command("emoji_pack"))
async def emoji_pack_test(message: Message):
    try:
        sticker_set = await message.bot.get_sticker_set("easportbot")

        text = "🎨 <b>Custom Emoji IDs</b>\n\n"

        for sticker in sticker_set.stickers:
            text += (
                f"{sticker.emoji or '❓'} "
                f"<code>{sticker.custom_emoji_id}</code>\n"
            )

        await message.reply(text, parse_mode="HTML")

    except Exception as e:
        await message.reply(
            f"❌ Error:\n<code>{e}</code>",
            parse_mode="HTML"
        )    
    
#===== CUSTOM EMOJI TEST =====
CUSTOM_EMOJI_ID = "6120396953067987320"
@router.message(Command("emoji_test"))
async def emoji_test(message: Message):
    await message.reply(
        f'<tg-emoji emoji-id="{CUSTOM_EMOJI_ID}">🏏</tg-emoji>',
        parse_mode="HTML"
    )
  
#===== GET CUSTOM EMOJI ID =====

@router.message(Command("getemoji"))
async def get_emoji_id(message: Message):
    if not message.reply_to_message:
        await message.reply(
            "❌ Reply to a message containing a custom emoji with:\n\n"
            "<code>/getemoji</code>",
            parse_mode="HTML"
        )
        return

    entities = message.reply_to_message.entities or []

    for entity in entities:
        if entity.type == "custom_emoji":
            await message.reply(
                f"✅ Custom Emoji ID:\n\n"
                f"<code>{entity.custom_emoji_id}</code>",
                parse_mode="HTML"
            )
            return

    await message.reply(
        "❌ No custom emoji found in the replied message."
    )

#===== PAUSE / RESUME AUCTION =====

@router.message(Command("pauseauction"))
async def pause_auction(message: Message):

    if not is_group(message):
        return

    # Tournament check first
    tournaments = load_json(TOURNAMENTS_FILE)

    if isinstance(tournaments, list):

        for tournament in tournaments:

            if (
                tournament.get("chat_id") == message.chat.id
                and tournament.get("status") == "AUCTION_RUNNING"
            ):

                if tournament.get("host_id") != message.from_user.id:
                    await message.reply(
                        "❌ <b>Only the auction host can pause the auction.</b>",
                        parse_mode="HTML"
                    )
                    return

                setup = tournament.get("auction_setup", {})

                if setup.get("status") != "RUNNING":
                    await message.reply(
                        "⚠️ <b>Auction is not currently running.</b>",
                        parse_mode="HTML"
                    )
                    return

                setup["status"] = "PAUSED"
                tournament["auction_setup"] = setup

                save_json(
                    TOURNAMENTS_FILE,
                    tournaments
                )

                cancel_player_timer(
                    message.chat.id
                )

                await message.reply(
                    "⏸️ <b>TOURNAMENT AUCTION PAUSED</b>\n\n"
                    "The timer has been stopped.\n"
                    "The current player and bid are preserved.",
                    parse_mode="HTML"
                )

                return

    #===== NORMAL AUCTION =====

    auction = get_auction(message.chat.id)

    if not auction:
        await message.reply(
            "❌ <b>No active auction.</b>",
            parse_mode="HTML"
        )
        return

    if auction.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ <b>Only the auction host can pause the auction.</b>",
            parse_mode="HTML"
        )
        return

    if auction.get("status") != "RUNNING":
        await message.reply(
            "⚠️ <b>Auction is not currently running.</b>",
            parse_mode="HTML"
        )
        return

    auction["status"] = "PAUSED"

    save_auction(auction)

    cancel_player_timer(
        message.chat.id
    )

    await message.reply(
        "⏸️ <b>AUCTION PAUSED</b>\n\n"
        "The timer has been stopped.\n"
        "The current player and bid are preserved.",
        parse_mode="HTML"
    )


@router.message(Command("resumeauction"))
async def resume_auction(message: Message):

    if not is_group(message):
        return

    # Tournament check first
    tournaments = load_json(TOURNAMENTS_FILE)

    if isinstance(tournaments, list):

        for tournament in tournaments:

            if (
                tournament.get("chat_id") == message.chat.id
                and tournament.get("status") == "AUCTION_RUNNING"
            ):

                if tournament.get("host_id") != message.from_user.id:
                    await message.reply(
                        "❌ <b>Only the auction host can resume the auction.</b>",
                        parse_mode="HTML"
                    )
                    return

                setup = tournament.get("auction_setup", {})

                if setup.get("status") != "PAUSED":
                    await message.reply(
                        "⚠️ <b>Auction is not paused.</b>",
                        parse_mode="HTML"
                    )
                    return

                setup["status"] = "RUNNING"
                tournament["auction_setup"] = setup

                save_json(
                    TOURNAMENTS_FILE,
                    tournaments
                )

                await message.reply(
                    "▶️ <b>TOURNAMENT AUCTION RESUMED</b>\n\n"
                    f"⏳ Timer : <b>{setup.get('timer', 0)} sec</b>",
                    parse_mode="HTML"
                )

                start_player_timer(
                    message.bot,
                    message.chat.id
                )

                return

    #===== NORMAL AUCTION =====

    auction = get_auction(message.chat.id)

    if not auction:
        await message.reply(
            "❌ <b>No active auction.</b>",
            parse_mode="HTML"
        )
        return

    if auction.get("host_id") != message.from_user.id:
        await message.reply(
            "❌ <b>Only the auction host can resume the auction.</b>",
            parse_mode="HTML"
        )
        return

    if auction.get("status") != "PAUSED":
        await message.reply(
            "⚠️ <b>Auction is not paused.</b>",
            parse_mode="HTML"
        )
        return

    auction["status"] = "RUNNING"

    save_auction(auction)

    await message.reply(
        "▶️ <b>AUCTION RESUMED</b>\n\n"
        f"⏳ Timer : <b>{auction.get('timer', 0)} sec</b>",
        parse_mode="HTML"
    )

    start_player_timer(
        message.bot,
        message.chat.id
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