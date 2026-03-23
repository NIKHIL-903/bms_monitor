import logging
import os
from dotenv import load_dotenv

load_dotenv()  # optional (for local only)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")
ALLOWED_USERS = [u.strip() for u in ALLOWED_USERS.split(",") if u.strip()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger(__name__)