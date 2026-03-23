from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.monitor import check_level1, check_level2, check_level3
from app.settings import log
from app.state import get_cfg

scheduler = None


def start_scheduler(bot, uid):
    global scheduler
    cfg = get_cfg(uid)

    if scheduler is None:
        scheduler = AsyncIOScheduler()
        scheduler.start()

    for job_id in [f"l1_{uid}", f"l2_{uid}", f"l3_{uid}"]:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

    scheduler.add_job(
        check_level1,
        "interval",
        minutes=cfg["freq_l1"],
        args=[bot, uid],
        id=f"l1_{uid}",
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        check_level2,
        "interval",
        minutes=cfg["freq_l2"],
        args=[bot, uid],
        id=f"l2_{uid}",
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        check_level3,
        "interval",
        minutes=cfg["freq_l3"],
        args=[bot, uid],
        id=f"l3_{uid}",
        next_run_time=datetime.now(),
    )
    log.info(f"[{uid}] Scheduler started")


def stop_scheduler(uid):
    global scheduler
    if scheduler:
        for job_id in [f"l1_{uid}", f"l2_{uid}", f"l3_{uid}"]:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
    log.info(f"[{uid}] Scheduler stopped")
