import json
import re
from datetime import datetime

from curl_cffi import requests

from app.settings import log


def format_date(date_str):
    try:
        parsed = datetime.strptime(date_str, "%Y%m%d")
        return f"{parsed.day} {parsed.strftime('%b')}"
    except Exception:
        return date_str


def fetch_initial_state(cfg):
    url = (
        f"https://in.bookmyshow.com/movies/{cfg['region']}/"
        f"{cfg['movie_slug']}/buytickets/{cfg['event_code']}/{cfg['target_date']}"
    )
    try:
        res = requests.get(url, impersonate="chrome120", timeout=10)
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})(?=</script>)",
            res.text,
            re.DOTALL,
        )
        if match:
            return json.loads(match.group(1))
    except Exception as exc:
        log.error(f"Fetch error: {exc}")
    return None


def is_date_open(data, cfg):
    try:
        widgets = (
            data["showtimesByEvent"]["showDates"]
            .get(cfg["target_date"], {})
            .get("dynamic", {})
            .get("data", {})
            .get("showtimeWidgets", [])
        )
        for widget in widgets:
            if widget.get("type") != "groupList":
                continue
            for group in widget.get("data", []):
                for venue in group.get("data", []):
                    for show in venue.get("showtimes", []):
                        show_date = show.get("additionalData", {}).get("showDateCode", "")
                        if show_date == cfg["target_date"]:
                            return True
        return False
    except Exception:
        return False


async def send(bot, chat_id, message):
    await bot.send_message(chat_id=chat_id, text=message)
    log.info(f"[{chat_id}] Sent: {message[:80]}")
