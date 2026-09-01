# ====== IMPORTS ======

from config import ADMIN_IDS

# ====== ADMIN CHECK ======

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
    
# ====== GROUP CHECK ======

def is_group(chat_type: str) -> bool:
    return chat_type in ["group", "supergroup"]