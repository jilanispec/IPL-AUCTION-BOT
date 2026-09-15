#===== IMPORTS =====

from aiogram.types import Message

from config import ADMIN_IDS

# ====== ADMIN CHECK ======

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
    
#===== GROUP CHECK =====

def is_group(message):
    return message.chat.type in ("group", "supergroup")