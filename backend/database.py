"""
=============================================================
  IoT Pet Feeder - Database Layer (JSON-based Storage)
=============================================================
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid

DB_FILE = os.path.join(os.path.dirname(__file__), "petfeeder_db.json")

# ─── Default DB Structure ─────────────────────────────────────
DEFAULT_DB = {
    "schedules": [],
    "history"  : [],
    "settings" : {
        "device_id"    : "PF001",
        "pet_name"     : "Kucing",
        "default_amount": 50,
        "low_food_alert": 20,
    }
}

def _load_db() -> dict:
    """Load database dari file JSON"""
    if not os.path.exists(DB_FILE):
        _save_db(DEFAULT_DB)
        return DEFAULT_DB.copy()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        _save_db(DEFAULT_DB)
        return DEFAULT_DB.copy()

def _save_db(data: dict):
    """Simpan database ke file JSON"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─── Schedule CRUD ────────────────────────────────────────────
def get_schedules() -> List[Dict]:
    db = _load_db()
    return db.get("schedules", [])

def add_schedule(hour: int, minute: int, amount: int, label: str = "", days: List[str] = None) -> Dict:
    """Tambah jadwal pemberian makan"""
    db = _load_db()
    schedule = {
        "id"       : str(uuid.uuid4())[:8],
        "hour"     : hour,
        "minute"   : minute,
        "amount"   : amount,
        "label"    : label or f"Jadwal {hour:02d}:{minute:02d}",
        "days"     : days or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "enabled"  : True,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    db["schedules"].append(schedule)
    _save_db(db)
    return schedule

def delete_schedule(schedule_id: str) -> bool:
    """Hapus jadwal berdasarkan ID"""
    db = _load_db()
    original_count = len(db["schedules"])
    db["schedules"] = [s for s in db["schedules"] if s["id"] != schedule_id]
    _save_db(db)
    return len(db["schedules"]) < original_count

def toggle_schedule(schedule_id: str) -> Optional[Dict]:
    """Toggle aktif/nonaktif jadwal"""
    db = _load_db()
    for s in db["schedules"]:
        if s["id"] == schedule_id:
            s["enabled"] = not s["enabled"]
            _save_db(db)
            return s
    return None

# ─── History CRUD ─────────────────────────────────────────────
def get_history(limit: int = 50) -> List[Dict]:
    db = _load_db()
    history = db.get("history", [])
    return history[-limit:][::-1]  # Newest first

def add_history_entry(trigger: str, amount: int, food_level_after: float, success: bool = True, note: str = ""):
    """Tambah entry ke log riwayat"""
    db = _load_db()
    entry = {
        "id"              : str(uuid.uuid4())[:8],
        "timestamp"       : datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "trigger"         : trigger,   # "manual" | "schedule" | "api"
        "amount"          : amount,
        "food_level_after": round(food_level_after, 1),
        "success"         : success,
        "note"            : note,
    }
    db["history"].append(entry)
    # Keep only last 200 entries
    if len(db["history"]) > 200:
        db["history"] = db["history"][-200:]
    _save_db(db)
    return entry

# ─── Settings ─────────────────────────────────────────────────
def get_settings() -> Dict:
    db = _load_db()
    return db.get("settings", DEFAULT_DB["settings"])

def update_settings(updates: Dict) -> Dict:
    db = _load_db()
    db["settings"].update(updates)
    _save_db(db)
    return db["settings"]
