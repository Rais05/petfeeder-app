"""
=============================================================
  IoT Pet Feeder - Feeding Scheduler
  Menjalankan jadwal pemberian makan otomatis
=============================================================
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import database
import mqtt_client as mq

logger = logging.getLogger("scheduler")
_scheduler = BackgroundScheduler()
_loaded_job_ids: set = set()

DAY_MAP = {
    "Mon": "mon", "Tue": "tue", "Wed": "wed",
    "Thu": "thu", "Fri": "fri", "Sat": "sat", "Sun": "sun",
}

def _execute_schedule(schedule_id: str, amount: int, label: str):
    """Eksekusi jadwal pemberian makan"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    logger.info(f"⏰ Jadwal '{label}' dijalankan [{now}]")

    success = mq.send_feed_command(amount)
    food_level_after = mq.device_state.get("food_level", 0)

    database.add_history_entry(
        trigger="schedule",
        amount=amount,
        food_level_after=food_level_after,
        success=success,
        note=f"Jadwal: {label}",
    )

    if success:
        logger.info(f"✅ Jadwal berhasil dieksekusi: {label} ({amount}g)")
    else:
        logger.warning(f"⚠️  Jadwal gagal: {label} — device mungkin offline")

def load_schedules():
    """Muat semua jadwal dari database dan daftarkan ke scheduler"""
    schedules = database.get_schedules()
    current_ids = set()

    for sched in schedules:
        if not sched.get("enabled", True):
            continue

        job_id = f"schedule_{sched['id']}"
        current_ids.add(job_id)

        if job_id not in _loaded_job_ids:
            days = sched.get("days", ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
            day_of_week = ",".join(DAY_MAP[d] for d in days if d in DAY_MAP)

            try:
                _scheduler.add_job(
                    func    = _execute_schedule,
                    trigger = CronTrigger(
                        hour       = sched["hour"],
                        minute     = sched["minute"],
                        day_of_week= day_of_week,
                    ),
                    id   = job_id,
                    args = [sched["id"], sched["amount"], sched["label"]],
                    replace_existing=True,
                )
                _loaded_job_ids.add(job_id)
                logger.info(
                    f"📅 Jadwal dimuat: '{sched['label']}' — "
                    f"{sched['hour']:02d}:{sched['minute']:02d} [{day_of_week}]"
                )
            except Exception as e:
                logger.error(f"❌ Gagal menambah jadwal {job_id}: {e}")

    # Hapus job yang tidak ada di database lagi
    for job_id in list(_loaded_job_ids):
        if job_id not in current_ids:
            try:
                _scheduler.remove_job(job_id)
                _loaded_job_ids.discard(job_id)
                logger.info(f"🗑️  Jadwal dihapus: {job_id}")
            except Exception:
                pass

def reload_schedules():
    """Reload jadwal (panggil setelah add/delete schedule)"""
    load_schedules()

def start_scheduler():
    """Mulai background scheduler"""
    # Reload jadwal setiap 1 menit untuk mengambil perubahan baru
    _scheduler.add_job(
        load_schedules,
        trigger="interval",
        minutes=1,
        id="reload_schedules",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("⏱️  Scheduler dimulai")

    # Load jadwal pertama kali
    load_schedules()

def stop_scheduler():
    """Hentikan scheduler"""
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("⏱️  Scheduler dihentikan")
