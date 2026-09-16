#===== IMPORTS =====

import os


#===== BOT TOKEN =====

BOT_TOKEN = os.getenv("BOT_TOKEN")

#===== ADMIN IDS =====

ADMIN_IDS = [
    2079655933
]


#===== BASE DIRECTORY =====

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


#===== DATA FOLDER =====

DATA_FOLDER = os.path.join(
    BASE_DIR,
    "data"
)


#===== MAIN DATA FILES =====

PLAYERS_FILE = os.path.join(
    DATA_FOLDER,
    "players.json"
)

TOURNAMENTS_FILE = os.path.join(DATA_FOLDER, "tournaments.json")




TOURSETS_FOLDER = os.path.join(
    DATA_FOLDER,
    "toursets"
)

TEAMS_FILE = os.path.join(
    DATA_FOLDER,
    "teams.json"
)

AUCTION_FILE = os.path.join(
    DATA_FOLDER,
    "auction.json"
)

BIDS_FILE = os.path.join(
    DATA_FOLDER,
    "bids.json"
)

SOLD_FILE = os.path.join(
    DATA_FOLDER,
    "sold.json"
)

SETTINGS_FILE = os.path.join(
    DATA_FOLDER,
    "settings.json"
)


#===== PLAYER SETS =====

PLAYER_SETS_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "mega_auction_sets",
    "players_sets"
)


#===== PATH CHECK =====

print(
    "===== PATH CHECK ====="
)

print(
    "CONFIG FILE:",
    os.path.abspath(__file__)
)

print(
    "BASE DIR:",
    BASE_DIR
)

print(
    "DATA FOLDER:",
    DATA_FOLDER
)

print(
    "PLAYER SETS FOLDER:",
    PLAYER_SETS_FOLDER
)

print(
    "PLAYER SETS EXISTS:",
    os.path.exists(
        PLAYER_SETS_FOLDER
    )
)

print(
    "======================"
)
