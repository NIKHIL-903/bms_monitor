from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


from app.handlers import cmd_end, cmd_skip, cmd_start, handle_message
from app.scheduler import start_scheduler
from app.session import load_all_sessions
from app.settings import ALLOWED_USERS, BOT_TOKEN, log
from app.state import default_state, user_cfg, user_state


async def on_startup(app):
    """Auto-resume all saved sessions on bot startup."""
    sessions = load_all_sessions()
    if not sessions:
        log.info("No saved sessions found — waiting for /start")
        return

    for uid, cfg in sessions:
        if uid not in ALLOWED_USERS:
            log.warning(f"[{uid}] Skipping session — user no longer in ALLOWED_USERS")
            continue

        # Restore config and state
        user_cfg[uid]              = cfg
        user_state[uid]            = default_state()
        user_state[uid]["running"] = True

        # Resume scheduler
        start_scheduler(app.bot, uid)

        # Notify user
        try:
            await app.bot.send_message(
                chat_id=uid,
                text=(
                    f"🔄 Monitor resumed after restart!\n\n"
                    f"📽 {cfg['movie_slug']}\n"
                    f"📅 {cfg['target_date']}\n"
                    f"🎭 {cfg.get('venue_code') or 'All theatres'}\n"
                    f"⏰ {cfg.get('target_show') or 'Any show'}\n"
                    f"💺 {', '.join(cfg['target_seats']) if cfg.get('target_seats') else 'No seat monitoring'}"
                )
            )
        except Exception as e:
            log.error(f"[{uid}] Failed to send resume message: {e}")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env")
    if not ALLOWED_USERS:
        raise ValueError("ALLOWED_USERS not set in .env")

    log.info(f"Starting BMS Monitor — allowed users: {ALLOWED_USERS}")

    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("end",   cmd_end))
    app.add_handler(CommandHandler("skip",  cmd_skip))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot running — send /start to begin setup")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
