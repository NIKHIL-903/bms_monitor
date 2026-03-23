import json
import re

from curl_cffi import requests

from app.settings import log
from app.state import get_cfg, get_state
from app.utils import fetch_initial_state, format_date, is_date_open, send


async def check_level1(bot, uid):
    cfg = get_cfg(uid)
    state = get_state(uid)

    if state["level1_done"] or not state["running"]:
        return
    log.info(f"[{uid}] Checking Level 1...")

    data = fetch_initial_state(cfg)
    if not data or not is_date_open(data, cfg):
        log.info(f"[{uid}] Level 1: {cfg['target_date']} not open yet")
        return

    state["level1_done"] = True
    date_str = format_date(cfg["target_date"])

    if not cfg["venue_code"]:
        await send(bot, uid, f"🟢 Bookings open for {cfg['movie_slug']} on {date_str}")
        state["level2_done"] = True
        state["level3_done"] = True
    else:
        await send(
            bot,
            uid,
            f"🟢 Bookings open for {cfg['movie_slug']} on {date_str}\n"
            f"🔍 Searching for {cfg['venue_code']}...",
        )
        await check_level2(bot, uid)


async def check_level2(bot, uid):
    cfg = get_cfg(uid)
    state = get_state(uid)

    if not state["level1_done"] or state["level2_done"] or not state["running"]:
        return
    if not cfg["venue_code"]:
        return
    log.info(f"[{uid}] Checking Level 2...")

    data = fetch_initial_state(cfg)
    if not data or not is_date_open(data, cfg):
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

        venue_name = None
        session_id = None
        venue_found = False
        show_found = False

        for widget in widgets:
            if widget.get("type") != "groupList":
                continue
            for group in widget.get("data", []):
                for venue in group.get("data", []):
                    if venue.get("additionalData", {}).get("venueCode", "") != cfg["venue_code"]:
                        continue
                    venue_found = True
                    venue_name = venue.get("additionalData", {}).get("venueName", cfg["venue_code"])

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
            state["venue_name"] = venue_name

            if show_found:
                state["session_id"] = session_id
                state["level2_done"] = True

                if not cfg["target_seats"]:
                    if cfg["target_show"]:
                        await send(
                            bot,
                            uid,
                            f"🟢 {venue_name} is open!\n"
                            f"🎬 {cfg['target_show']} show is live on {date_str}",
                        )
                    else:
                        await send(bot, uid, f"🟢 {venue_name} is open on {date_str}!")
                    state["level3_done"] = True
                else:
                    await send(
                        bot,
                        uid,
                        f"🟢 {venue_name} is open!\n"
                        f"🎬 {cfg['target_show']} show is live on {date_str}\n"
                        f"🔍 Checking seats {', '.join(cfg['target_seats'])}...",
                    )
                    await check_level3(bot, uid)
            else:
                await send(
                    bot,
                    uid,
                    f"🟢 {venue_name} is open on {date_str}!\n"
                    f"⏳ Waiting for {cfg['target_show']} show...",
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
                                state["session_id"] = session_id
                                state["level2_done"] = True

                                if not cfg["target_seats"]:
                                    await send(
                                        bot,
                                        uid,
                                        f"🟢 {state['venue_name']} - {cfg['target_show']} is now live on {date_str}!",
                                    )
                                    state["level3_done"] = True
                                else:
                                    await send(
                                        bot,
                                        uid,
                                        f"🟢 {state['venue_name']} - {cfg['target_show']} is now live on {date_str}!\n"
                                        f"🔍 Checking seats {', '.join(cfg['target_seats'])}...",
                                    )
                                    await check_level3(bot, uid)
                                return

        elif not venue_found:
            log.info(f"[{uid}] Level 2: {cfg['venue_code']} not found yet")

    except Exception as exc:
        log.error(f"[{uid}] Level 2 error: {exc}")


async def check_level3(bot, uid):
    cfg = get_cfg(uid)
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
        res = requests.get(url, impersonate="chrome120", timeout=10, allow_redirects=False)
        if res.status_code in (301, 302):
            log.info(f"[{uid}] Level 3: Redirected - not available yet")
            await send(
                bot,
                uid,
                f"🟡 {state['venue_name']} • {cfg['target_show']} is live on {date_str}\n"
                f"💺 Seats {', '.join(cfg['target_seats'])} not available yet\n"
                f"🔄 Checking every {cfg['freq_l3']} mins...",
            )
            return

        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})(?=</script>)",
            res.text,
            re.DOTALL,
        )
        if not match:
            log.info(f"[{uid}] Level 3: Could not parse seat layout")
            return

        layout_str = json.dumps(json.loads(match.group(1)))
        found = [seat for seat in cfg["target_seats"] if seat in layout_str]
        missing = [seat for seat in cfg["target_seats"] if seat not in layout_str]
        show_part = f" • {cfg['target_show']}" if cfg["target_show"] else ""

        if found and not missing:
            state["level3_done"] = True
            await send(
                bot,
                uid,
                f"🟢 {state['venue_name']}{show_part} on {date_str}\n"
                f"💺 Seats {', '.join(found)} are available!\n"
                f"🔗 {url}",
            )
        elif found:
            await send(
                bot,
                uid,
                f"🟡 {state['venue_name']}{show_part} on {date_str}\n"
                f"💺 {', '.join(found)} available | {', '.join(missing)} not yet\n"
                f"🔗 {url}",
            )
        else:
            await send(
                bot,
                uid,
                f"🟡 {state['venue_name']}{show_part} is live on {date_str}\n"
                f"💺 Seats {', '.join(cfg['target_seats'])} not available yet\n"
                f"🔄 Checking every {cfg['freq_l3']} mins...",
            )

    except Exception as exc:
        log.error(f"[{uid}] Level 3 error: {exc}")
