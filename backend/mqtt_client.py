"""
=============================================================
  IoT Pet Feeder - MQTT Client Bridge
  Jembatan antara MQTT broker dan FastAPI server
=============================================================
"""

import paho.mqtt.client as mqtt
import json
import threading
import logging
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger("mqtt_client")

# ─── Konfigurasi ─────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883

TOPIC_COMMAND   = "petfeeder/command"
TOPIC_STATUS    = "petfeeder/status"
TOPIC_FOODLEVEL = "petfeeder/foodlevel"
TOPIC_LOG       = "petfeeder/log"

# ─── Shared Device State (diakses oleh API & scheduler) ───────
device_state = {
    "device_id"    : "PF001",
    "online"       : False,
    "food_level"   : 0,
    "feeding_count": 0,
    "last_feed"    : None,
    "is_feeding"   : False,
    "wifi_rssi"    : 0,
    "timestamp"    : None,
}

# ─── Event Listeners ──────────────────────────────────────────
_status_listeners: list[Callable] = []
_log_listeners:    list[Callable] = []

def add_status_listener(callback: Callable):
    _status_listeners.append(callback)

def add_log_listener(callback: Callable):
    _log_listeners.append(callback)

# ─── Internal log buffer (untuk SSE stream) ───────────────────
_device_logs = []

def get_device_logs(limit: int = 30):
    return _device_logs[-limit:][::-1]

# ─── MQTT Callbacks ───────────────────────────────────────────
def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("✅ MQTT Connected ke broker")
        client.subscribe(TOPIC_STATUS)
        client.subscribe(TOPIC_FOODLEVEL)
        client.subscribe(TOPIC_LOG)
        logger.info(f"📡 Subscribe: {TOPIC_STATUS}, {TOPIC_FOODLEVEL}, {TOPIC_LOG}")
    else:
        logger.error(f"❌ MQTT Connect gagal, kode: {reason_code}")

def _on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    logger.warning("⚠️  MQTT Terputus dari broker")
    device_state["online"] = False

def _on_message(client, userdata, msg):
    payload_str = msg.payload.decode("utf-8")
    topic = msg.topic

    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        return

    if topic == TOPIC_STATUS:
        # Update shared state
        device_state.update({
            "online"       : data.get("online", False),
            "food_level"   : data.get("food_level", 0),
            "feeding_count": data.get("feeding_count", 0),
            "last_feed"    : data.get("last_feed"),
            "is_feeding"   : data.get("is_feeding", False),
            "wifi_rssi"    : data.get("wifi_rssi", 0),
            "timestamp"    : data.get("timestamp"),
        })
        logger.debug(f"📥 Status update: food={device_state['food_level']}%")
        # Notify listeners
        for cb in _status_listeners:
            try: cb(device_state.copy())
            except Exception: pass

    elif topic == TOPIC_FOODLEVEL:
        device_state["food_level"] = data.get("food_level", device_state["food_level"])

    elif topic == TOPIC_LOG:
        log_entry = {
            "message"  : data.get("message", ""),
            "timestamp": data.get("timestamp", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        }
        _device_logs.append(log_entry)
        if len(_device_logs) > 100:
            _device_logs.pop(0)
        logger.info(f"📋 Device log: {log_entry['message']}")
        for cb in _log_listeners:
            try: cb(log_entry)
            except Exception: pass

# ─── MQTT Client Singleton ────────────────────────────────────
_mqtt_client: Optional[mqtt.Client] = None
_connected = False

def get_client() -> Optional[mqtt.Client]:
    return _mqtt_client

def is_connected() -> bool:
    return _mqtt_client is not None and _mqtt_client.is_connected()

def start_mqtt():
    """Mulai MQTT client di background thread"""
    global _mqtt_client

    _mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="PetFeeder_Server")
    _mqtt_client.on_connect    = _on_connect
    _mqtt_client.on_disconnect = _on_disconnect
    _mqtt_client.on_message    = _on_message

    # LWT — jika server mati, device tahu
    _mqtt_client.will_set(TOPIC_STATUS,
        json.dumps({"device_id": "PF001", "online": False}), retain=True)

    def _run():
        try:
            logger.info(f"[MQTT] Menghubungkan ke {MQTT_BROKER}:{MQTT_PORT}...")
            _mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            _mqtt_client.loop_forever()
        except Exception as e:
            logger.error(f"[MQTT] Error: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("[MQTT] Thread dimulai")

# ─── Publish Command ──────────────────────────────────────────
def send_feed_command(amount: int = 50) -> bool:
    """Kirim perintah feeding ke device"""
    if _mqtt_client is None:
        return False
    payload = json.dumps({"action": "feed", "amount": amount})
    result = _mqtt_client.publish(TOPIC_COMMAND, payload)
    success = result.rc == mqtt.MQTT_ERR_SUCCESS
    logger.info(f"📤 Feed command sent (amount={amount}g): {'OK' if success else 'FAIL'}")
    return success

def send_status_request() -> bool:
    """Minta device untuk publish status terbaru"""
    if _mqtt_client is None:
        return False
    payload = json.dumps({"action": "status"})
    result = _mqtt_client.publish(TOPIC_COMMAND, payload)
    return result.rc == mqtt.MQTT_ERR_SUCCESS
