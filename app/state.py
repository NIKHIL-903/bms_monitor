user_cfg = {}
user_state = {}
user_setup = {}


def default_cfg():
    return {
        "movie_slug": None,
        "event_code": None,
        "region": "hyderabad",
        "target_date": None,
        "venue_code": None,
        "target_show": None,
        "target_seats": [],
        "freq_l1": 60,
        "freq_l2": 30,
        "freq_l3": 2,
    }


def default_state():
    return {
        "level1_done": False,
        "venue_notified": False,
        "level2_done": False,
        "level3_done": False,
        "session_id": None,
        "venue_name": None,
        "running": False,
    }


def default_setup():
    return {
        "active": False,
        "step": 0,
    }


def get_cfg(uid):
    if uid not in user_cfg:
        user_cfg[uid] = default_cfg()
    return user_cfg[uid]


def get_state(uid):
    if uid not in user_state:
        user_state[uid] = default_state()
    return user_state[uid]


def get_setup(uid):
    if uid not in user_setup:
        user_setup[uid] = default_setup()
    return user_setup[uid]


STEPS = [
    ("movie_slug", "🎬 Enter movie slug:\n(e.g. project-hail-mary)"),
    ("event_code", "🔑 Enter event code:\n(e.g. ET00492371)"),
    ("target_date", "📅 Enter target date:\n(format: YYYYMMDD e.g. 20260401)"),
    ("venue_code", "🎭 Enter venue code (or /skip):\n(e.g. ALUC)"),
    ("target_show", "⏰ Enter show time (or /skip):\n(e.g. 02:45 PM)"),
    ("target_seats", "💺 Enter seats comma separated (or /skip):\n(e.g. D5, D6)"),
    ("freq_l1", "⏱ Level 1 frequency in minutes:\n(date check, e.g. 60)"),
    ("freq_l2", "⏱ Level 2 frequency in minutes:\n(venue/show check, e.g. 30)"),
    ("freq_l3", "⏱ Level 3 frequency in minutes:\n(seat check, e.g. 2)"),
]
