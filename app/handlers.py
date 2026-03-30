
import re

from telegram import Update
from telegram.ext import ContextTypes

from app.scheduler import start_scheduler, stop_scheduler
from app.session import delete_session, save_session
from app.settings import ALLOWED_USERS, log
from app.state import (
    STEPS,
    default_cfg,
    default_setup,
    default_state,
    get_cfg,
    get_setup,
    get_state,
    user_cfg,
    user_setup,
    user_state,
)
from app.utils import format_date


def is_allowed(update: Update) -> bool:
    uid = str(update.message.chat_id)
    if uid not in ALLOWED_USERS:
        log.warning(f"Unauthorized access: {uid}")
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ Unauthorized.")
        return

    uid = str(update.message.chat_id)
    user_cfg[uid]             = default_cfg()
    user_state[uid]           = default_state()
    user_setup[uid]           = default_setup()
    user_setup[uid]["active"] = True
    stop_scheduler(uid)

    await update.message.reply_text(
        "👋 BMS Monitor Setup\nSend /end anytime to stop.\n\n" + STEPS[0][1]
    )


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("❌ Unauthorized.")
        return

    uid = str(update.message.chat_id)
    get_state(uid)["running"] = False
    get_setup(uid)["active"]  = False
    stop_scheduler(uid)
    delete_session(uid)  # ← remove saved session so it doesn't resume
    await update.message.reply_text("🛑 Monitor stopped.")


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    uid   = str(update.message.chat_id)
    setup = get_setup(uid)
    cfg   = get_cfg(uid)

    if not setup["active"]:
        return

    key = STEPS[setup["step"]][0]
    if key in ("venue_code", "target_show", "target_seats"):
        cfg[key] = [] if key == "target_seats" else None
        await advance_setup(update, context.bot, uid)
    else:
        await update.message.reply_text("❌ This field cannot be skipped.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    uid   = str(update.message.chat_id)
    setup = get_setup(uid)
    cfg   = get_cfg(uid)

    if not setup["active"]:
        return

    text = update.message.text.strip()
    key  = STEPS[setup["step"]][0]

    if key == "target_date":
        if not re.match(r"^\d{8}$", text):
            await update.message.reply_text("❌ Invalid date. Use YYYYMMDD e.g. 20260401")
            return
    elif key in ("freq_l1", "freq_l2", "freq_l3"):
        if not text.isdigit() or int(text) < 1:
            await update.message.reply_text("❌ Enter a valid number e.g. 60")
            return
        cfg[key] = int(text)
        await advance_setup(update, context.bot, uid)
        return
    elif key == "target_seats":
        cfg[key] = [seat.strip() for seat in text.split(",") if seat.strip()]
        await advance_setup(update, context.bot, uid)
        return

    cfg[key] = text
    await advance_setup(update, context.bot, uid)


async def advance_setup(update, bot, uid):
    setup = get_setup(uid)
    cfg   = get_cfg(uid)
    setup["step"] += 1

    if setup["step"] < len(STEPS):
        await update.message.reply_text(STEPS[setup["step"]][1])
    else:
        setup["active"]          = False
        state                    = get_state(uid)
        state["running"]         = True

        save_session(uid, cfg)  # ← persist config to file

        summary = (
            f"✅ Monitor started!\n\n"
            f"📽 {cfg['movie_slug']}\n"
            f"🔑 {cfg['event_code']}\n"
            f"📅 {format_date(cfg['target_date'])}\n"
            f"🎭 {cfg['venue_code'] or 'All theatres'}\n"
            f"⏰ {cfg['target_show'] or 'Any show'}\n"
            f"💺 {', '.join(cfg['target_seats']) if cfg['target_seats'] else 'No seat monitoring'}\n\n"
            f"⏱ L1: {cfg['freq_l1']}m | L2: {cfg['freq_l2']}m | L3: {cfg['freq_l3']}m"
        )
        await update.message.reply_text(summary)
        start_scheduler(bot, uid)
