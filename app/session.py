import json
import os
import logging

log = logging.getLogger(__name__)

SESSION_DIR = os.getenv("SESSION_DIR", "sessions")


def _ensure_dir():
    os.makedirs(SESSION_DIR, exist_ok=True)


def _path(uid):
    return os.path.join(SESSION_DIR, f"session_{uid}.json")


def save_session(uid, cfg):
    """Save user config to JSON file."""
    _ensure_dir()
    try:
        with open(_path(uid), "w") as f:
            json.dump(cfg, f, indent=2)
        log.info(f"[{uid}] Session saved")
    except Exception as e:
        log.error(f"[{uid}] Failed to save session: {e}")


def delete_session(uid):
    """Delete user session file."""
    try:
        path = _path(uid)
        if os.path.exists(path):
            os.remove(path)
            log.info(f"[{uid}] Session deleted")
    except Exception as e:
        log.error(f"[{uid}] Failed to delete session: {e}")


def load_all_sessions():
    """
    Load all saved sessions on startup.
    Returns list of (uid, cfg) tuples.
    """
    _ensure_dir()
    sessions = []
    try:
        for filename in os.listdir(SESSION_DIR):
            if filename.startswith("session_") and filename.endswith(".json"):
                uid  = filename.replace("session_", "").replace(".json", "")
                path = os.path.join(SESSION_DIR, filename)
                try:
                    with open(path) as f:
                        cfg = json.load(f)
                    sessions.append((uid, cfg))
                    log.info(f"[{uid}] Session loaded")
                except Exception as e:
                    log.error(f"[{uid}] Failed to load session: {e}")
    except Exception as e:
        log.error(f"Failed to scan sessions dir: {e}")
    return sessions
