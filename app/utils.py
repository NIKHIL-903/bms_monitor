from datetime import datetime
from playwright.async_api import async_playwright

from app.settings import log


# âœ… Format date for messages
def format_date(date_str):
    try:
        parsed = datetime.strptime(date_str, "%Y%m%d")
        return f"{parsed.day} {parsed.strftime('%b')}"
    except Exception:
        return date_str


# âœ… Fetch BMS page using async Playwright (Cloudflare bypass)
async def fetch_initial_state(cfg):
    url = (
        f"https://in.bookmyshow.com/movies/{cfg['region']}/"
        f"{cfg['movie_slug']}/buytickets/{cfg['event_code']}/{cfg['target_date']}"
    )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like       Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_function(
                "window.__INITIAL_STATE__ !== undefined",
                timeout=15000
            )
            data = await page.evaluate("window.__INITIAL_STATE__")
            await browser.close()

        return data

    except Exception as exc:
        log.error(f"Fetch error: {exc}")
        return None


# âœ… Check if correct date is actually open
def is_date_open(data, target_date):
    try:
        show_dates = data.get("showtimesByEvent", {}).get("showDates", {})
        return target_date in show_dates

    except Exception as e:
        log.error(f"is_date_open error: {e}")
        return False


# âœ… Send message wrapper (used everywhere)
async def send(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        log.error(f"Send error: {e}")
