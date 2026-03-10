"""
=============================================================
  IoT Pet Feeder - FastAPI Backend Server
  Jalankan: uvicorn main:app --reload --port 8000
=============================================================
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database
import mqtt_client as mq
import scheduler as sched

# ─── Logging Setup ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ─── FastAPI App ─────────────────────────────────────────────
app = FastAPI(
    title="IoT Pet Feeder API",
    description="Backend server untuk sistem pemberi makan hewan peliharaan IoT",
    version="1.0.0",
)

# ─── CORS (ijinkan semua origin untuk prototyping) ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── SSE Event Queue ─────────────────────────────────────────
_sse_queues: list[asyncio.Queue] = []

def _broadcast_event(event_type: str, data: dict):
    """Broadcast event ke semua SSE client yang terhubung"""
    message = {"type": event_type, "data": data, 
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    for q in _sse_queues:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass

# Register listeners untuk broadcast SSE
mq.add_status_listener(lambda d: _broadcast_event("status", d))
mq.add_log_listener(lambda l: _broadcast_event("log", l))

# ─── Startup / Shutdown ──────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("🚀 Pet Feeder Server dimulai...")
    mq.start_mqtt()
    sched.start_scheduler()
    logger.info("✅ Server siap!")

@app.on_event("shutdown")
async def shutdown():
    sched.stop_scheduler()
    logger.info("🛑 Server dihentikan")

# ─── Pydantic Models ─────────────────────────────────────────
class FeedRequest(BaseModel):
    amount: int = Field(default=50, ge=10, le=500, description="Jumlah makanan dalam gram")

class ScheduleCreate(BaseModel):
    hour  : int  = Field(..., ge=0, le=23)
    minute: int  = Field(..., ge=0, le=59)
    amount: int  = Field(default=50, ge=10, le=500)
    label : str  = Field(default="")
    days  : List[str] = Field(
        default=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        description="Hari aktif: Mon/Tue/Wed/Thu/Fri/Sat/Sun"
    )

class SettingsUpdate(BaseModel):
    pet_name       : Optional[str] = None
    default_amount : Optional[int] = None
    low_food_alert : Optional[int] = None

# ─── API Routes ──────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {"message": "🐾 IoT Pet Feeder API", "version": "1.0.0", "status": "running"}

# ── Device Status ─────────────────────────────────────────────
@app.get("/api/status", tags=["Device"])
def get_status():
    """Dapatkan status perangkat saat ini"""
    state = mq.device_state.copy()
    state["mqtt_connected"] = mq.is_connected()
    return state

# ── Manual Feed ───────────────────────────────────────────────
@app.post("/api/feed/now", tags=["Feeding"])
def feed_now(req: FeedRequest):
    """Trigger pemberian makan manual"""
    if mq.device_state.get("is_feeding"):
        raise HTTPException(status_code=409, detail="Perangkat sedang memberi makan")

    success = mq.send_feed_command(req.amount)

    if not success:
        raise HTTPException(status_code=503, detail="Gagal mengirim perintah — MQTT tidak terhubung")

    food_level_after = mq.device_state.get("food_level", 0)
    entry = database.add_history_entry(
        trigger="manual",
        amount=req.amount,
        food_level_after=food_level_after,
        success=True,
        note="Pemberian makan manual",
    )

    # Broadcast ke SSE clients
    _broadcast_event("feed", {"amount": req.amount, "trigger": "manual", "entry": entry})

    return {
        "success"  : True,
        "message"  : f"Perintah makan {req.amount}g berhasil dikirim",
        "history"  : entry,
    }

# ── Schedules ─────────────────────────────────────────────────
@app.get("/api/schedule", tags=["Schedule"])
def get_schedules():
    """Dapatkan semua jadwal pemberian makan"""
    return {"schedules": database.get_schedules()}

@app.post("/api/schedule", tags=["Schedule"])
def create_schedule(req: ScheduleCreate):
    """Tambah jadwal baru"""
    valid_days = {"Mon","Tue","Wed","Thu","Fri","Sat","Sun"}
    invalid = [d for d in req.days if d not in valid_days]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Hari tidak valid: {invalid}")

    schedule = database.add_schedule(
        hour=req.hour, minute=req.minute,
        amount=req.amount, label=req.label, days=req.days
    )
    sched.reload_schedules()  # Reload scheduler
    _broadcast_event("schedule_added", schedule)
    return {"success": True, "schedule": schedule}

@app.delete("/api/schedule/{schedule_id}", tags=["Schedule"])
def delete_schedule(schedule_id: str):
    """Hapus jadwal berdasarkan ID"""
    deleted = database.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    sched.reload_schedules()
    _broadcast_event("schedule_deleted", {"id": schedule_id})
    return {"success": True, "message": "Jadwal dihapus"}

@app.patch("/api/schedule/{schedule_id}/toggle", tags=["Schedule"])
def toggle_schedule(schedule_id: str):
    """Toggle aktif/nonaktif jadwal"""
    result = database.toggle_schedule(schedule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    sched.reload_schedules()
    return {"success": True, "schedule": result}

# ── History ───────────────────────────────────────────────────
@app.get("/api/history", tags=["History"])
def get_history(limit: int = Query(default=20, le=100)):
    """Riwayat pemberian makan"""
    return {"history": database.get_history(limit)}

# ── Device Logs ───────────────────────────────────────────────
@app.get("/api/logs", tags=["Device"])
def get_device_logs(limit: int = Query(default=20, le=50)):
    """Log aktivitas perangkat"""
    return {"logs": mq.get_device_logs(limit)}

# ── Settings ──────────────────────────────────────────────────
@app.get("/api/settings", tags=["Settings"])
def get_settings():
    return {"settings": database.get_settings()}

@app.patch("/api/settings", tags=["Settings"])
def update_settings(req: SettingsUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada data yang diperbarui")
    settings = database.update_settings(updates)
    return {"success": True, "settings": settings}

# ── SSE — Real-time Events ────────────────────────────────────
@app.get("/api/events", tags=["Events"])
async def sse_events():
    """
    Server-Sent Events endpoint untuk real-time update ke frontend.
    Frontend connect ke: EventSource('/api/events')
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_queues.append(queue)

    async def event_generator():
        # Kirim status awal
        yield f"data: {json.dumps({'type': 'connected', 'data': mq.device_state})}\n\n"
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat setiap 25 detik agar koneksi tidak drop
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _sse_queues.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

# ─── Serve Frontend Statis ────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info(f"📂 Frontend mounted di /app dari {FRONTEND_DIR}")

# ─── Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
