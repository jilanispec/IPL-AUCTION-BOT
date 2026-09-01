import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    2079655933
]

DATA_FOLDER = "data"

PLAYERS_FILE = f"{DATA_FOLDER}/players.json"
TEAMS_FILE = f"{DATA_FOLDER}/teams.json"
AUCTION_FILE = f"{DATA_FOLDER}/auction.json"
BIDS_FILE = f"{DATA_FOLDER}/bids.json"
SOLD_FILE = f"{DATA_FOLDER}/sold.json"
SETTINGS_FILE = f"{DATA_FOLDER}/settings.json"

# ====== PLAYER SETS ======

PLAYER_SETS_FOLDER = "data/mega_auction_sets/players_sets"