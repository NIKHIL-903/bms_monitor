
from playwright.async_api import async_playwright

from app.settings import log
from app.state import get_cfg, get_state
from app.utils import fetch_initial_state, format_date, is_date_open, send


async def check_level1(bot, uid):
    cfg   = get_cfg(uid)
    state = get_state(uid)

    if state["level1_done"] or not state["running"]:
        return
    log.info(f"[{uid}] Checking Level 1...")

    data = await fetch_initial_state(cfg)
    if not data:
        log.info(f"[{uid}] Level 1: Fetch returned None")
        return

    log.info(f"[{uid}] TOP LEVEL KEYS: {list(data.keys())}")

    # DEBUG â€” log what BMS actually returned
    show_dates   = data.get("showtimesByEvent", {}).get("showDates", {})
    current_date = data.get("showtimesByEvent", {}).get("currentDateCode", "")
    log.info(f"[{uid}] DEBUG currentDateCode: {current_date}")
    log.info(f"[{uid}] DEBUG showDates keys: {list(show_dates.keys())}")

    # Check showDateCode inside shows
    for date_key, date_val in show_dates.items():
        widgets = date_val.get("dynamic", {}).get("data", {}).get("showtimeWidgets", [])
        for widget in widgets:
            if widget.get("type") != "groupList":
                continue
            for group in widget.get("data", []):
                for venue in group.get("data", []):
                    for show in venue.get("showtimes", []):
                        show_date_code = show.get("additionalData", {}).get("showDateCode", "")
                        log.info(f"[{uid}] DEBUG show: {show.get('title')} | showDateCode: {show_date_code}")

    if not is_date_open(data, cfg["target_date"]):
        log.info(f"[{uid}] Level 1: {cfg['target_date']} not open yet")
        return

    state["level1_done"] = True
    date_str = format_date(cfg["target_date"])

    if not cfg["venue_code"]:
        await send(bot, uid, f"ðŸŸ¢ Bookings open for {cfg['movie_slug']} on {date_str}")
        state["level2_done"] = True
        state["level3_done"] = True
    else:
        await send(
            bot,
            uid,
            f"ðŸŸ¢ Bookings open for {cfg['movie_slug']} on {date_str}\n"
            f"ðŸ” Searching for {cfg['venue_code']}...",
        )
        await check_level2(bot, uid)


async def check_level2(bot, uid):
    cfg   = get_cfg(uid)
    state = get_state(uid)

    if not state["level1_done"] or state["level2_done"] or not state["running"]:
        return
    if not cfg["venue_code"]:
        return
    log.info(f"[{uid}] Checking Level 2...")

    data = await fetch_initial_state(cfg)
    if not data or not is_date_open(data, cfg["target_date"]):
        return

    date_str = format_date(cfg["target_date"])

    try:
        widgets = (
            data["showtimesByEvent"]["showDates"]
            .get(cfg["target_date"], {})
            .get("dynamic", {})
            .get("data", {})
            .get("showtimeWidgets", [])
        )

        venue_name  = None
        session_id  = None
        venue_found = False
        show_found  = False

        for widget in widgets:
            if widget.get("type") != "groupList":
                continue
            for group in widget.get("data", []):
                for venue in group.get("data", []):
                    if venue.get("additionalData", {}).get("venueCode", "") != cfg["venue_code"]:
                        continue
                    venue_found = True
                    venue_name  = venue.get("additionalData", {}).get("venueName", cfg["venue_code"])

                    if not cfg["target_show"]:
                        show_found = True
                        break

                    for show in venue.get("showtimes", []):
                        if show.get("additionalData", {}).get("showDateCode", "") != cfg["target_date"]:
                            continue
                        if show.get("title", "").strip() == cfg["target_show"].strip():
                            session_id = show.get("additionalData", {}).get("sessionId")
                            show_found = True
                            break
                    break
                if venue_found:
                    break

        if venue_found and not state["venue_notified"]:
            state["venue_notified"] = True
            state["venue_name"]     = venue_name

            if show_found:
                state["session_id"]  = session_id
                state["level2_done"] = True

                if not cfg["target_seats"]:
                    if cfg["target_show"]:
                        await send(
                            bot, uid,
                            f"ðŸŸ¢ {venue_name} is open!\n"
                            f"ðŸŽ¬ {cfg['target_show']} show is live on {date_str}",
                        )
                    else:
                        await send(bot, uid, f"ðŸŸ¢ {venue_name} is open on {date_str}!")
                    state["level3_done"] = True
                else:
                    await send(
                        bot, uid,
                        f"ðŸŸ¢ {venue_name} is open!\n"
                        f"ðŸŽ¬ {cfg['target_show']} show is live on {date_str}\n"
                        f"ðŸ” Checking seats {', '.join(cfg['target_seats'])}...",
                    )
                    await check_level3(bot, uid)
            else:
                await send(
                    bot, uid,
                    f"ðŸŸ¢ {venue_name} is open on {date_str}!\n"
                    f"â³ Waiting for {cfg['target_show']} show...",
                )

        elif venue_found and state["venue_notified"] and not state["level2_done"]:
            for widget in widgets:
                if widget.get("type") != "groupList":
                    continue
                for group in widget.get("data", []):
                    for venue in group.get("data", []):
                        if venue.get("additionalData", {}).get("venueCode", "") != cfg["venue_code"]:
                            continue
                        for show in venue.get("showtimes", []):
                            if show.get("additionalData", {}).get("showDateCode", "") != cfg["target_date"]:
                                continue
                            if show.get("title", "").strip() == cfg["target_show"].strip():
                                session_id = show.get("additionalData", {}).get("sessionId")
                                state["session_id"]  = session_id
                                state["level2_done"] = True

                                if not cfg["target_seats"]:
                                    await send(
                                        bot, uid,
                                        f"ðŸŸ¢ {state['venue_name']} - {cfg['target_show']} is now live on {date_str}!",
                                    )
                                    state["level3_done"] = True
                                else:
                                    await send(
                                        bot, uid,
                                        f"ðŸŸ¢ {state['venue_name']} - {cfg['target_show']} is now live on {date_str}!\n"
                                        f"ðŸ” Checking seats {', '.join(cfg['target_seats'])}...",
                                    )
                                    await check_level3(bot, uid)
                                return

        elif not venue_found:
            log.info(f"[{uid}] Level 2: {cfg['venue_code']} not found yet")

    except Exception as exc:
        log.error(f"[{uid}] Level 2 error: {exc}")


async def check_level3(bot, uid):
    cfg   = get_cfg(uid)
    state = get_state(uid)

    if not state["level2_done"] or state["level3_done"] or not state["running"]:
        return
    if not cfg["target_seats"] or not state["session_id"]:
        return
    log.info(f"[{uid}] Checking Level 3...")

    date_str = format_date(cfg["target_date"])
    url = (
        f"https://in.bookmyshow.com/movies/{cfg['region']}/seat-layout/"
        f"{cfg['event_code']}/{cfg['venue_code']}/{state['session_id']}/{cfg['target_date']}"
    )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_function(
                "window.__INITIAL_STATE__ !== undefined",
                timeout=15000
            )
            layout_data = await page.evaluate("window.__INITIAL_STATE__")
            await browser.close()

        if not layout_data:
            log.info(f"[{uid}] Level 3: Could not load seat layout")
            return

        layout_str = str(layout_data)
        found      = [seat for seat in cfg["target_seats"] if seat in layout_str]
        missing    = [seat for seat in cfg["target_seats"] if seat not in layout_str]
        show_part  = f" â€¢ {cfg['target_show']}" if cfg["target_show"] else ""

        if found and not missing:
            state["level3_done"] = True
            await send(
                bot, uid,
                f"ðŸŸ¢ {state['venue_name']}{show_part} on {date_str}\n"
                f"ðŸ’º Seats {', '.join(found)} are available!\n"
                f"ðŸ”— {url}",
            )
        elif found:
            await send(
                bot, uid,
                f"ðŸŸ¡ {state['venue_name']}{show_part} on {date_str}\n"
                f"ðŸ’º {', '.join(found)} available | {', '.join(missing)} not yet\n"
                f"ðŸ”— {url}",
            )
        else:
            await send(
                bot, uid,
                f"ðŸŸ¡ {state['venue_name']}{show_part} is live on {date_str}\n"
                f"ðŸ’º Seats {', '.join(cfg['target_seats'])} not available yet\n"
                f"ðŸ”„ Checking every {cfg['freq_l3']} mins...",
            )

    except Exception as exc:
        log.error(f"[{uid}] Level 3 error: {exc}")
