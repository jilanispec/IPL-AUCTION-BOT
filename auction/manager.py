# ====== IMPORTS ======

import os
import random
import uuid

from config import (
    AUCTION_FILE,
    PLAYER_SETS_FOLDER,
    DATA_FOLDER,
)

from storage.json_manager import (
    load_json,
    save_json,
)


# ====== AUCTION HISTORY FILE ======

AUCTIONS_FILE = os.path.join(
    DATA_FOLDER,
    "auctions.json"
)


# ====== LIVE AUCTIONS FOLDER ======

LIVE_AUCTIONS_FOLDER = os.path.join(
    DATA_FOLDER,
    "live_auctions"
)

os.makedirs(
    LIVE_AUCTIONS_FOLDER,
    exist_ok=True
)


# ====== CURRENT CHAT CONTEXT ======

CURRENT_CHAT_ID = None


# ====== SET CHAT CONTEXT ======

def set_chat_context(chat_id):

    global CURRENT_CHAT_ID

    CURRENT_CHAT_ID = chat_id


# ====== GET LIVE AUCTION FILE ======

def get_live_auction_file(
    chat_id=None
):

    if chat_id is None:

        chat_id = CURRENT_CHAT_ID

    if chat_id is None:

        return AUCTION_FILE

    return os.path.join(
        LIVE_AUCTIONS_FOLDER,
        f"{chat_id}.json"
    )


# ====== CREATE AUCTION ======

def create_auction(
    chat_id,
    host_id,
    host_username,
    auction_type="mega"
):

    # =========================
    # SET GROUP CONTEXT
    # =========================

    set_chat_context(
        chat_id
    )

    # =========================
    # CHECK EXISTING AUCTION
    # =========================

    current = get_auction(
        chat_id
    )

    if current:

        if current.get(
            "status"
        ) not in [
            "ENDED",
            "CANCELLED"
        ]:

            return "already_exists"

    # =========================
    # CREATE AUCTION ID
    # =========================

    auction_id = (
        "AUC-"
        + uuid.uuid4().hex[:8].upper()
    )

    # =========================
    # CREATE LIVE AUCTION
    # =========================

    auction = {

        "auction_id": auction_id,

        "auction_name": (
            "Mega Auction"
        ),

        "auction_type": auction_type,

        "chat_id": chat_id,

        "host_id": host_id,

        "host_username": (
            host_username
        ),

        "status": "WAITING",

        "loaded_set": None,

        "current_set": None,

        "current_index": 0,

        "players": [],

        "current_player": None,

        "current_bid": 0,

        "leading_team": None,

        "leading_manager_id": None,

        "timer": 20,

        "timer_version": 0,

        "auction_message_id": None,

        "auction_chat_id": None,

        "skip_votes": [],

        "pending_bid": None,

        "teams": [],

        "sold_players": [],

        "unsold_players": [],
       
		#===== SQUAD SETTINGS =====
		
		"squad_min": None,
		"squad_max": None,
		"os_limit": None,
		
		"squad_settings_locked": False,
		"squad_setup_started": False,    
	}
			    
    # =========================
    # SAVE LIVE AUCTION
    # =========================

    save_auction(
        auction
    )

    # =========================
    # SAVE AUCTION HISTORY
    # =========================

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        auctions = []

    auctions.append({

        "auction_id": auction_id,

        "auction_name": (
            "Mega Auction"
        ),

        "auction_type": auction_type,

        "chat_id": chat_id,

        "host_id": host_id,

        "host_username": (
            host_username
        ),

        "status": "WAITING",

        "players": [],

        "sold_players": [],

        "unsold_players": [],

        "teams": [],

        "created_at": None,

        "ended_at": None
    })

    save_json(
        AUCTIONS_FILE,
        auctions
    )

    return auction


#===== SQUAD LIMIT DEFAULTS =====

DEFAULT_MIN_SQUAD = 18
DEFAULT_MAX_SQUAD = 25
DEFAULT_OS_LIMIT = 8
SQUAD_SETUP_TIMEOUT = 45


# ====== GET LIVE AUCTION ======

def get_auction(
    chat_id=None
):

    file_path = (
        get_live_auction_file(
            chat_id
        )
    )

    auction = load_json(
        file_path
    )

    if not isinstance(
        auction,
        dict
    ):

        return None

    return auction


# ====== SAVE LIVE AUCTION ======

def save_auction(
    auction
):

    if not isinstance(
        auction,
        dict
    ):

        return False

    chat_id = auction.get(
        "chat_id"
    )

    if chat_id is None:

        return False

    file_path = (
        get_live_auction_file(
            chat_id
        )
    )

    save_json(
        file_path,
        auction
    )

    return True


# ====== GET AUCTION HISTORY ======

def get_auctions():

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        return []

    return auctions
    
#===== SAVE RESTORE SNAPSHOT =====

def save_restore_snapshot(
    auction
):

    if not isinstance(
        auction,
        dict
    ):

        return False

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        auctions = []

    import time

    snapshot = dict(
        auction
    )

    now = time.time()

    snapshot[
        "restore_saved_at"
    ] = now

    snapshot[
        "restore_available_until"
    ] = (
        now + (2 * 60 * 60)
    )

    snapshot[
        "status"
    ] = "ENDED"

    auction_id = snapshot.get(
        "auction_id"
    )

    if not auction_id:

        return False

    # Remove old snapshot
    auctions = [
        item
        for item in auctions
        if not isinstance(
            item,
            dict
        )
        or item.get(
            "auction_id"
        ) != auction_id
    ]

    # Save complete auction data
    auctions.append(
        snapshot
    )

    save_json(
        AUCTIONS_FILE,
        auctions
    )

    return True


#===== RESTORE AUCTION =====

def restore_auction(
    auction_id,
    host_id
):

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        return "not_found"

    import time

    for snapshot in auctions:

        if not isinstance(
            snapshot,
            dict
        ):

            continue

        if snapshot.get(
            "auction_id"
        ) != auction_id:

            continue

        #===== ORIGINAL HOST ONLY =====

        if snapshot.get(
            "host_id"
        ) != host_id:

            return "not_host"

        #===== RESTORE TIME CHECK =====

        restore_until = snapshot.get(
            "restore_available_until"
        )

        if not restore_until:

            return "expired"

        try:

            restore_until = float(
                restore_until
            )

        except (
            TypeError,
            ValueError
        ):

            return "expired"

        if time.time() > restore_until:

            return "expired"

        #===== COPY COMPLETE AUCTION =====

        restored = dict(
            snapshot
        )

        #===== RESTORE STATUS =====

        restored[
            "status"
        ] = "WAITING"

        #===== REMOVE RESTORE METADATA =====

        restored.pop(
            "restore_saved_at",
            None
        )

        restored.pop(
            "restore_available_until",
            None
        )

        #===== SAVE LIVE AUCTION =====

        if not save_auction(
            restored
        ):

            return "save_error"

        return restored

    return "not_found"


#===== APPLY DEFAULT SQUAD LIMITS =====

def apply_default_squad_limits(
    chat_id
):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    if auction.get(
        "squad_settings_locked",
        False
    ):
        return auction

    auction["squad_min"] = (
        DEFAULT_MIN_SQUAD
    )

    auction["squad_max"] = (
        DEFAULT_MAX_SQUAD
    )

    auction["os_limit"] = (
        DEFAULT_OS_LIMIT
    )

    auction["squad_settings_locked"] = True
    auction["squad_setup_started"] = True

    save_auction(
        auction
    )

    return auction


#===== GET SQUAD LIMITS =====

def get_squad_limits(
    chat_id
):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return None

    return {
        "min": auction.get(
            "squad_min"
        ),

        "max": auction.get(
            "squad_max"
        ),

        "os": auction.get(
            "os_limit"
        ),

        "locked": auction.get(
            "squad_settings_locked",
            False
        )
    }


#===== CHECK PLAYER SQUAD LIMIT =====

def check_player_limits(
    team,
    player
):

    squad_max = team.get(
        "_squad_max"
    )

    os_limit = team.get(
        "_os_limit"
    )

    players = team.get(
        "players",
        []
    )

    if squad_max is not None:

        if len(players) >= int(
            squad_max
        ):

            return "squad_full"

    #===== CHECK OVERSEAS =====

    if player.get(
        "overseas",
        False
    ):

        overseas_count = 0

        for existing_player in players:

            if existing_player.get(
                "overseas",
                False
            ):

                overseas_count += 1

        if (
            os_limit is not None
            and overseas_count >= int(
                os_limit
            )
        ):

            return "os_full"

    return True
    
    
    
    
# ====== GET PLAYER SETS ======

def get_player_sets():

    sets = []

    if not os.path.exists(
        PLAYER_SETS_FOLDER
    ):

        return sets

    for file_name in os.listdir(
        PLAYER_SETS_FOLDER
    ):

        if file_name.endswith(
            ".json"
        ):

            sets.append(
                file_name[:-5]
            )

    return sorted(
        sets
    )


# ====== LOAD PLAYER SET ======

def load_player_set(
    set_name,
    chat_id
):

    # =========================
    # SET GROUP CONTEXT
    # =========================

    set_chat_context(
        chat_id
    )

    # =========================
    # GET GROUP AUCTION
    # =========================

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    # =========================
    # DON'T LOAD DURING AUCTION
    # =========================

    if auction.get(
        "status"
    ) == "RUNNING":

        return "auction_running"

    # =========================
    # DON'T LOAD CLOSED AUCTION
    # =========================

    if auction.get(
        "status"
    ) in [
        "ENDED",
        "CANCELLED"
    ]:

        return "auction_ended"

    # =========================
    # SET FILE
    # =========================

    file_path = os.path.join(
        PLAYER_SETS_FOLDER,
        f"{set_name}.json"
    )

    if not os.path.exists(
        file_path
    ):

        return False

    # =========================
    # LOAD PLAYERS
    # =========================

    players = load_json(
        file_path
    )

    if not isinstance(
        players,
        list
    ):

        return False

    if not players:

        return False

    # =========================
    # NORMALIZE SET NAME
    # =========================

    set_name = str(
        set_name
    ).strip().lower()

    # =========================
    # LOADED SET HISTORY
    # =========================

    loaded_sets = auction.get(
        "loaded_sets"
    )

    if not isinstance(
        loaded_sets,
        list
    ):

        loaded_sets = []

    # =========================
    # PREVENT DUPLICATE SET
    # =========================

    if set_name in [
        str(x).strip().lower()
        for x in loaded_sets
    ]:

        return "set_already_loaded"

    # =========================
    # RANDOMIZE PLAYERS
    # =========================

    players = list(
        players
    )

    random.shuffle(
        players
    )

    # =========================
    # ADD SET TO HISTORY
    # =========================

    loaded_sets.append(
        set_name
    )

    auction["loaded_sets"] = (
        loaded_sets
    )

    # =========================
    # CURRENT SET
    # =========================

    auction["loaded_set"] = (
        set_name
    )

    auction["current_set"] = (
        set_name
    )

    auction["current_index"] = 0

    # =========================
    # ADD PLAYERS
    # =========================
    #
    # IMPORTANT:
    # Do NOT replace existing
    # players from another set.
    #

    existing_players = auction.get(
        "players",
        []
    )

    if not isinstance(
        existing_players,
        list
    ):

        existing_players = []

    existing_players.extend(
        players
    )

    auction["players"] = (
        existing_players
    )

    # =========================
    # RESET CURRENT PLAYER
    # =========================

    auction["current_player"] = None

    auction["current_bid"] = 0

    auction["leading_team"] = None

    auction["leading_manager_id"] = None

    # =========================
    # RESET TIMER
    # =========================

    auction["timer"] = 20

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    # =========================
    # RESET BID STATE
    # =========================

    auction["skip_votes"] = []

    auction["pending_bid"] = None

    # =========================
    # WAITING
    # =========================

    auction["status"] = "WAITING"

    # =========================
    # SAVE
    # =========================

    save_auction(
        auction
    )

    return len(
        players
    )


# ====== START AUCTION ======

def start_auction(
    chat_id
):

    # =========================
    # GET GROUP AUCTION
    # =========================

    auction = get_auction(
        chat_id
    )

    if not auction:

        return "no_auction"

    # =========================
    # CHECK RUNNING
    # =========================

    if auction.get(
        "status"
    ) == "RUNNING":

        return "already_running"

    # =========================
    # GET REMAINING PLAYERS
    # =========================

    players = auction.get(
        "players",
        []
    )

    if not players:

        return "no_players"

    # =========================
    # SELECT NEXT PLAYER
    # =========================

    player = random.choice(
        players
    )

    # =========================
    # REMOVE SELECTED PLAYER
    # =========================

    players.remove(
        player
    )

    auction["players"] = players

    # =========================
    # START PLAYER AUCTION
    # =========================

    auction["status"] = "RUNNING"

    auction["current_player"] = (
        player
    )

    # =========================
    # SET BASE PRICE
    # =========================

    auction["current_bid"] = float(
        player.get(
            "base_price",
            0
        )
    )

    # =========================
    # RESET LEADING TEAM
    # =========================

    auction["leading_team"] = None

    auction["leading_manager_id"] = None

    # =========================
    # RESET TIMER
    # =========================

    auction["timer"] = 20

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    # =========================
    # RESET PLAYER STATE
    # =========================

    auction["skip_votes"] = []

    auction["pending_bid"] = None

    # =========================
    # UPDATE PLAYER INDEX
    # =========================

    auction["current_index"] = (
        auction.get(
            "current_index",
            0
        ) + 1
    )

    # =========================
    # SAVE
    # =========================

    save_auction(
        auction
    )

    return player


# ====== BUILD AUCTION TEXT ======

def build_auction_text(
    chat_id=None
):

    auction = get_auction(
        chat_id
    )

    if not auction:

        return "❌ No active auction."

    # =========================
    # CURRENT PLAYER
    # =========================

    player = auction.get(
        "current_player"
    )

    if not player:

        return "❌ No current player."

    # =========================
    # TEAMS
    # =========================

    teams = auction.get(
        "teams",
        []
    )

    # =========================
    # SKIP VOTES
    # =========================

    skip_votes = len(
        auction.get(
            "skip_votes",
            []
        )
    )

    # =========================
    # LEADING TEAM
    # =========================

    leading_team = auction.get(
        "leading_team"
    )

    if leading_team is None:

        leading_team = (
            "No Bids Yet"
        )

    # =========================
    # BUILD TEXT
    # =========================

    return (
        "🏏 <b>IPL MEGA AUCTION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 <b>Player:</b> "
        f"{player.get('name', 'Unknown')}\n"

        f"🏏 <b>Role:</b> "
        f"{player.get('role', 'Unknown')}\n"

        f"💰 <b>Base Price:</b> "
        f"₹{float(player.get('base_price', 0)):.2f} Cr\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 <b>Current Price:</b> "
        f"₹{float(auction.get('current_bid', 0)):.2f} Cr\n"

        f"👥 <b>Leading Team:</b> "
        f"{leading_team}\n"

        f"⏳ <b>Time Left:</b> "
        f"{auction.get('timer', 0)} sec\n"

        f"⏭ <b>Skip Votes:</b> "
        f"{skip_votes}/{len(teams)}"
    )


# ====== ADD TEAM ======

def add_team(
    name,
    purse,
    manager_username=None,
    manager_id=None
):

    # ====== GET AUCTION ======

    auction = get_auction()

    if not auction:
        return False

    # ====== CHECK AUCTION STATUS ======

    if auction.get("status") in [
        "ENDED",
        "CANCELLED"
    ]:
        return False

    # ====== GET TEAMS ======

    teams = auction.get(
        "teams",
        []
    )

    # ====== CHECK DUPLICATE TEAM ======

    for team in teams:

        if team.get(
            "name",
            ""
        ).lower() == name.lower():

            return False

    # ====== CHECK DUPLICATE MANAGER ======

    if manager_id is not None:

        for team in teams:

            if team.get(
                "manager_id"
            ) == manager_id:

                return False

    # ====== CREATE TEAM ======

    team = {
        "name": name,
        "purse": float(purse),
        "manager_username": manager_username,
        "manager_id": manager_id,
        "players": []
    }

    # ====== ADD TEAM ======

    teams.append(
        team
    )

    auction["teams"] = teams

    # ====== SAVE AUCTION ======

    save_auction(
        auction
    )

    return True


# ====== GET TEAMS ======

def get_teams():

    auction = get_auction()

    if not auction:

        return []

    return auction.get(
        "teams",
        []
    )


# ====== REMOVE TEAM ======

def remove_team(
    team_name
):

    auction = get_auction()

    if not auction:

        return False

    # =========================
    # GET TEAMS
    # =========================

    teams = auction.get(
        "teams",
        []
    )

    # =========================
    # FIND TEAM
    # =========================

    for team in teams:

        if team.get(
            "name",
            ""
        ).lower() == team_name.lower():

            teams.remove(
                team
            )

            auction["teams"] = (
                teams
            )

            save_auction(
                auction
            )

            return True

    return False


# ====== PLACE BID LEGACY ======

def place_bid(
    increment
):

    auction = get_auction()

    if not auction:

        return False

    # =========================
    # CHECK RUNNING
    # =========================

    if auction.get(
        "status"
    ) != "RUNNING":

        return False

    # =========================
    # APPLY INCREMENT
    # =========================

    current_bid = float(
        auction.get(
            "current_bid",
            0
        )
    )

    auction["current_bid"] = (
        current_bid + float(
            increment
        )
    )

    # =========================
    # RESET TIMER
    # =========================

    auction["timer"] = 20

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    # =========================
    # SAVE
    # =========================

    save_auction(
        auction
    )

    return auction

# ====== MANAGER BID ======

def manager_bid(
    chat_id,
    user_id,
    bid_amount
):

    # =========================
    # GET THIS GROUP AUCTION
    # =========================

    auction = get_auction(
        chat_id
    )

    if not auction:

        return "no_auction"

    # =========================
    # CHECK GROUP
    # =========================

    if auction.get(
        "chat_id"
    ) != chat_id:

        return "no_auction"

    # =========================
    # CHECK AUCTION STATUS
    # =========================

    if auction.get(
        "status"
    ) != "RUNNING":

        return "not_running"

    # =========================
    # CHECK TIMER
    # =========================

    if auction.get(
        "timer",
        0
    ) <= 0:

        return "time_over"

    # =========================
    # VALIDATE BID NUMBER
    # =========================

    try:

        bid_amount = float(
            bid_amount
        )

    except (
        TypeError,
        ValueError
    ):

        return "invalid_bid"

    # =========================
    # CHECK POSITIVE BID
    # =========================

    if bid_amount <= 0:

        return "invalid_bid"

    # =========================
    # GET CURRENT BID
    # =========================

    try:

        current_bid = float(
            auction.get(
                "current_bid",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        current_bid = 0.0

    # =========================
    # BID MUST BE HIGHER
    # =========================

    if bid_amount <= current_bid:

        return "bid_too_low"

    # =========================
    # GET CURRENT PLAYER
    # =========================

    current_player = auction.get(
        "current_player"
    )

    if not isinstance(
        current_player,
        dict
    ):

        return "no_player"

    # =========================
    # GET TEAMS
    # =========================

    teams = auction.get(
        "teams",
        []
    )

    if not isinstance(
        teams,
        list
    ):

        teams = []

    # =========================
    # FIND MANAGER TEAM
    # =========================

    team = None

    for current_team in teams:

        if not isinstance(
            current_team,
            dict
        ):

            continue

        if current_team.get(
            "manager_id"
        ) == user_id:

            team = current_team

            break

    # =========================
    # MANAGER NOT FOUND
    # =========================

    if team is None:

        return "not_manager"

    # =========================
    # SAME TEAM CHECK
    # =========================

    if (
        auction.get(
            "leading_team"
        )
        == team.get(
            "name"
        )
    ):

        return "already_leading"

    # =========================
    # GET SQUAD
    # =========================

    squad = team.get(
        "players",
        []
    )

    if not isinstance(
        squad,
        list
    ):

        squad = []

    # =========================
    # SQUAD MAXIMUM
    # =========================

    squad_max = auction.get(
        "squad_max",
        25
    )

    try:

        squad_max = int(
            squad_max
        )

    except (
        TypeError,
        ValueError
    ):

        squad_max = 25

    if len(squad) >= squad_max:

        return "squad_full"

    # =========================
    # OVERSEAS LIMIT
    # =========================

    player_is_overseas = (
        current_player.get(
            "overseas",
            False
        )
        is True
    )

    if player_is_overseas:

        overseas_count = 0

        for squad_player in squad:

            if not isinstance(
                squad_player,
                dict
            ):

                continue

            if squad_player.get(
                "overseas",
                False
            ) is True:

                overseas_count += 1

        os_limit = auction.get(
            "os_limit",
            8
        )

        try:

            os_limit = int(
                os_limit
            )

        except (
            TypeError,
            ValueError
        ):

            os_limit = 8

        if overseas_count >= os_limit:

            return "os_limit_reached"

    # =========================
    # CHECK TEAM PURSE
    # =========================

    try:

        purse = float(
            team.get(
                "purse",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        purse = 0.0

    if bid_amount > purse:

        return "insufficient_purse"

    # =========================
    # ACCEPT BID
    # =========================

    auction["current_bid"] = (
        bid_amount
    )

    auction["leading_team"] = (
        team.get(
            "name"
        )
    )

    auction["leading_manager_id"] = (
        user_id
    )

    # =========================
    # RESET TIMER
    # =========================

    auction["timer"] = 20

    # =========================
    # UPDATE TIMER VERSION
    # =========================

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    # =========================
    # SAVE BID
    # =========================

    save_auction(
        auction
    )

    # =========================
    # RETURN BID RESULT
    # =========================

    return {
        "success": True,

        "team": team.get(
            "name"
        ),

        "bid": bid_amount
    }




#===== PAUSE AUCTION ========

def pause_auction(chat_id):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    if auction.get("status") != "RUNNING":
        return "not_running"

    if not auction.get("current_player"):
        return "no_player"

    auction["status"] = "PAUSED"

    save_auction(
        auction
    )

    return auction


#===== RESUME AUCTION ========

def resume_auction(chat_id):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    if auction.get("status") != "PAUSED":
        return "not_paused"

    if not auction.get("current_player"):
        return "no_player"

    timer = auction.get(
        "timer",
        0
    )

    if timer <= 0:
        return "time_over"

    auction["status"] = "RUNNING"

    auction["timer_version"] = (
        auction.get(
            "timer_version",
            0
        ) + 1
    )

    save_auction(
        auction
    )

    return auction

    
# ====== COMPLETE SOLD PLAYER ======

def complete_sold_player(chat_id):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    player = auction.get(
        "current_player"
    )

    if not player:
        return "no_player"

    winning_team_name = auction.get(
        "leading_team"
    )

    if not winning_team_name:
        return "no_winner"

    bid_amount = float(
        auction.get(
            "current_bid",
            0
        )
    )

    teams = auction.get(
        "teams",
        []
    )

    winning_team = None

    for team in teams:

        if (
            str(
                team.get(
                    "name",
                    ""
                )
            ).lower()
            ==
            str(
                winning_team_name
            ).lower()
        ):

            winning_team = team
            break

    if winning_team is None:
        return "team_not_found"

    purse = float(
        winning_team.get(
            "purse",
            0
        )
    )

    if bid_amount > purse:
        return "insufficient_purse"

    # =========================
    # CREATE SQUAD PLAYER
    # =========================

    squad_player = {
        "id": player.get(
            "id"
        ),
        "name": player.get(
            "name",
            "Unknown"
        ),
        "country": player.get(
            "country",
            "Unknown"
        ),
        "overseas": player.get(
            "overseas",
            False
        ),
        "base_price": player.get(
            "base_price",
            0
        ),
        "sold_price": bid_amount,
        "price": bid_amount
    }

    # =========================
    # ADD TO SQUAD
    # =========================

    players = winning_team.get(
        "players",
        []
    )

    if not isinstance(
        players,
        list
    ):

        players = []

    players.append(
        squad_player
    )

    winning_team["players"] = (
        players
    )

    # =========================
    # DEDUCT PURSE
    # =========================

    winning_team["purse"] = (
        purse - bid_amount
    )

    # =========================
    # SOLD HISTORY
    # =========================

    sold_players = auction.get(
        "sold_players",
        []
    )

    if not isinstance(
        sold_players,
        list
    ):

        sold_players = []

    sold_players.append({
        "id": player.get(
            "id"
        ),
        "name": player.get(
            "name",
            "Unknown"
        ),
        "team": winning_team.get(
            "name",
            winning_team_name
        ),
        "price": bid_amount
    })

    auction["sold_players"] = (
        sold_players
    )

    auction["teams"] = teams

    # =========================
    # CLEAR CURRENT PLAYER
    # =========================

    auction["current_player"] = None

    auction["current_bid"] = 0

    auction["leading_team"] = None

    auction["leading_manager_id"] = None

    # =========================
    # SAVE
    # =========================

    save_auction(
        auction
    )

    return {
        "success": True,
        "team": winning_team.get(
            "name",
            winning_team_name
        ),
        "player": player.get(
            "name",
            "Unknown"
        ),
        "price": bid_amount,
        "remaining_purse": winning_team.get(
            "purse",
            0
        )
    }
    
                            
#===== GET TEAM SQUAD =====

def get_team_squad(chat_id, team_name):

    auction = get_auction(chat_id)

    if not auction:
        return None

    teams = auction.get(
        "teams",
        []
    )

    for team in teams:

        if team.get("name", "").lower() == team_name.lower():

            return team

    return None
    
            
#===== SET SQUAD LIMITS =====

def set_squad_limits(
    chat_id,
    min_squad,
    max_squad,
    os_limit
):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    if auction.get("status") in [
        "ENDED",
        "CANCELLED"
    ]:
        return "auction_ended"

    if auction.get(
        "squad_settings_locked",
        False
    ):
        return "already_locked"

    try:

        min_squad = int(
            min_squad
        )

        max_squad = int(
            max_squad
        )

        os_limit = int(
            os_limit
        )

    except (
        TypeError,
        ValueError
    ):

        return "invalid"

    if min_squad < 1:
        return "invalid_min"

    if max_squad < min_squad:
        return "invalid_max"

    if os_limit < 0:
        return "invalid_os"

    if os_limit > max_squad:
        return "invalid_os"

    auction["squad_min"] = min_squad
    auction["squad_max"] = max_squad
    auction["os_limit"] = os_limit

    auction["squad_settings_locked"] = True
    auction["squad_setup_started"] = True

    save_auction(
        auction
    )

    return auction


#===== APPLY DEFAULT SQUAD LIMITS =====

def apply_default_squad_limits(
    chat_id
):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return "no_auction"

    if auction.get(
        "squad_settings_locked",
        False
    ):
        return auction

    auction["squad_min"] = (
        DEFAULT_MIN_SQUAD
    )

    auction["squad_max"] = (
        DEFAULT_MAX_SQUAD
    )

    auction["os_limit"] = (
        DEFAULT_OS_LIMIT
    )

    auction["squad_settings_locked"] = True
    auction["squad_setup_started"] = True

    save_auction(
        auction
    )

    return auction


#===== GET SQUAD LIMITS =====

def get_squad_limits(
    chat_id
):

    auction = get_auction(
        chat_id
    )

    if not auction:
        return None

    return {
        "min": auction.get(
            "squad_min"
        ),

        "max": auction.get(
            "squad_max"
        ),

        "os": auction.get(
            "os_limit"
        ),

        "locked": auction.get(
            "squad_settings_locked",
            False
        )
    }


#===== CHECK PLAYER SQUAD LIMIT =====

def check_player_limits(
    team,
    player
):

    squad_max = team.get(
        "_squad_max"
    )

    os_limit = team.get(
        "_os_limit"
    )

    players = team.get(
        "players",
        []
    )

    if squad_max is not None:

        if len(players) >= int(
            squad_max
        ):

            return "squad_full"

    #===== CHECK OVERSEAS =====

    if player.get(
        "overseas",
        False
    ):

        overseas_count = 0

        for existing_player in players:

            if existing_player.get(
                "overseas",
                False
            ):

                overseas_count += 1

        if (
            os_limit is not None
            and overseas_count >= int(
                os_limit
            )
        ):

            return "os_full"

    return True

    # =========================
    # SAVE SOLD PLAYER HISTORY
    # =========================

    sold_players = auction.get(
        "sold_players",
        []
    )

    sold_players.append({

        "id": player.get(
            "id"
        ),

        "name": player.get(
            "name"
        ),

        "team": winning_team.get(
            "name"
        ),

        "price": bid_amount
    })

    auction["sold_players"] = (
        sold_players
    )

    # =========================
    # SAVE TEAMS
    # =========================

    auction["teams"] = teams

    # =========================
    # SAVE AUCTION
    # =========================

    save_auction(
        auction
    )

    # =========================
    # RETURN SOLD RESULT
    # =========================

    return {

        "success": True,

        "team": winning_team.get(
            "name"
        ),

        "player": player.get(
            "name"
        ),

        "price": bid_amount,

        "remaining_purse": (
            winning_team.get(
                "purse"
            )
        )
    }



#===== SAVE RESTORE SNAPSHOT =====

def save_restore_snapshot(
    auction
):

    if not isinstance(
        auction,
        dict
    ):

        return False

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        auctions = []

    snapshot = dict(
        auction
    )

    snapshot["restore_saved_at"] = (
        __import__("time").time()
    )

    snapshot["restore_available_until"] = (
        __import__("time").time()
        + (2 * 60 * 60)
    )

    snapshot["status"] = "ENDED"

    auction_id = snapshot.get(
        "auction_id"
    )

    if not auction_id:

        return False

    # Remove old snapshot of same auction
    auctions = [
        item
        for item in auctions
        if not isinstance(item, dict)
        or item.get("auction_id") != auction_id
    ]

    auctions.append(
        snapshot
    )

    save_json(
        AUCTIONS_FILE,
        auctions
    )

    return True
    

#===== RESTORE AUCTION =====

def restore_auction(
    auction_id,
    host_id
):

    auctions = load_json(
        AUCTIONS_FILE
    )

    if not isinstance(
        auctions,
        list
    ):

        return "not_found"

    import time

    for snapshot in auctions:

        if not isinstance(
            snapshot,
            dict
        ):

            continue

        if snapshot.get(
            "auction_id"
        ) != auction_id:

            continue

        #===== ORIGINAL HOST ONLY =====

        if snapshot.get(
            "host_id"
        ) != host_id:

            return "not_host"

        #===== CHECK RESTORE WINDOW =====

        restore_until = snapshot.get(
            "restore_available_until"
        )

        if not restore_until:

            return "expired"

        if time.time() > float(
            restore_until
        ):

            return "expired"

        #===== RESTORE FULL DATA =====

        restored = dict(
            snapshot
        )

        restored["status"] = "WAITING"

        restored.pop(
            "restore_saved_at",
            None
        )

        restored.pop(
            "restore_available_until",
            None
        )

        #===== SAVE LIVE AUCTION =====

        save_auction(
            restored
        )

        return restored

    return "not_found"
    
        
                
        
                
# ====== COMPLETE UNSOLD PLAYER ======

def complete_unsold_player(
    chat_id
):

    # =========================
    # GET AUCTION
    # =========================

    auction = get_auction(
        chat_id
    )

    if not auction:

        return "no_auction"

    # =========================
    # GET PLAYER
    # =========================

    player = auction.get(
        "current_player"
    )

    if not player:

        return "no_player"

    # =========================
    # SAVE UNSOLD HISTORY
    # =========================

    unsold_players = auction.get(
        "unsold_players",
        []
    )

    unsold_players.append({

        "id": player.get(
            "id"
        ),

        "name": player.get(
            "name"
        ),

        "base_price": player.get(
            "base_price"
        )
    })

    auction["unsold_players"] = (
        unsold_players
    )

    # =========================
    # SAVE
    # =========================

    save_auction(
        auction
    )

    return {
        "success": True,

        "player": player.get(
            "name"
        )
    }