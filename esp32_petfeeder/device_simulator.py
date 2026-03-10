"""
=============================================================
  IoT Pet Feeder - Device Simulator (Emulasi ESP32)
  Menggantikan hardware ESP32 nyata untuk prototyping
=============================================================
  Jalankan: python device_simulator.py
  
  MQTT Topics:
    Subscribe: petfeeder/command
    Publish:   petfeeder/status, petfeeder/foodlevel, petfeeder/log
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import threading
from datetime import datetime

# ─── Konfigurasi ─────────────────────────────────────────────
MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
DEVICE_ID     = "PF001"
CLIENT_ID     = "PetFeeder_Simulator_001"

TOPIC_COMMAND   = "petfeeder/command"
TOPIC_STATUS    = "petfeeder/status"
TOPIC_FOODLEVEL = "petfeeder/foodlevel"
TOPIC_LOG       = "petfeeder/log"

# ─── State Simulator ──────────────────────────────────────────
device_state = {
    "device_id"    : DEVICE_ID,
    "online"       : True,
    "food_level"   : 80,       # % makanan tersisa (0-100)
    "feeding_count": 0,
    "last_feed"    : None,
    "is_feeding"   : False,
    "wifi_rssi"    : -42,      # Simulasi sinyal WiFi
}

# ─── MQTT Client ─────────────────────────────────────────────
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[Simulator] ✅ Terhubung ke MQTT Broker ({MQTT_BROKER}:{MQTT_PORT})")
        client.subscribe(TOPIC_COMMAND)
        print(f"[Simulator] 📡 Subscribe ke: {TOPIC_COMMAND}")
        publish_status()
    else:
        print(f"[Simulator] ❌ Gagal connect, kode: {reason_code}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print("[Simulator] ⚠️  Terputus dari broker, mencoba reconnect...")

def on_message(client, userdata, msg):
    """Terima perintah dari server/aplikasi"""
    topic   = msg.topic
    payload = msg.payload.decode("utf-8")
    print(f"\n[Simulator] 📥 Perintah diterima [{topic}]: {payload}")

    try:
        data = json.loads(payload)
        action = data.get("action", "")

        if action == "feed":
            amount = data.get("amount", 50)
            threading.Thread(
                target=simulate_feeding,
                args=(amount,),
                daemon=True
            ).start()

        elif action == "status":
            publish_status()
            publish_food_level()

        elif action == "calibrate":
            print("[Simulator] 🔧 Kalibrasi sensor dimulai...")
            time.sleep(2)
            publish_log("Kalibrasi sensor selesai")
            print("[Simulator] 🔧 Kalibrasi selesai")

    except json.JSONDecodeError:
        print("[Simulator] ❌ Format JSON tidak valid")

# ─── Simulasi Proses Feeding ──────────────────────────────────
def simulate_feeding(amount_grams: int):
    """Simulasi servo membuka dan menutup untuk memberi makan"""
    if device_state["is_feeding"]:
        print("[Simulator] ⚠️  Sedang memberi makan, perintah diabaikan")
        return

    device_state["is_feeding"] = True

    print(f"\n[Simulator] 🐱 ─── Mulai Memberi Makan ───")
    print(f"[Simulator] ⚙️  Servo: BUKA (90°) — Porsi: {amount_grams}g")

    # Durasi buka servo proporsional dengan jumlah makanan
    duration = max(1.0, amount_grams / 25.0)
    time.sleep(duration)

    print(f"[Simulator] ⚙️  Servo: TUTUP (0°)")

    # Update state
    device_state["feeding_count"] += 1
    device_state["last_feed"]   = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    food_consumed                = (amount_grams / 500.0) * 100
    device_state["food_level"]  = max(0, device_state["food_level"] - food_consumed)
    device_state["is_feeding"]  = False

    print(f"[Simulator] ✅ Selesai! Sisa makanan: {device_state['food_level']:.1f}%")
    print(f"[Simulator] 🐱 ─────────────────────────────\n")

    # Publish update
    publish_status()
    publish_food_level()
    publish_log(f"Pemberian makan selesai: {amount_grams}g pada {device_state['last_feed']}")

    # Warning jika makanan hampir habis
    if device_state["food_level"] < 20:
        publish_log(f"⚠️ PERINGATAN: Makanan hampir habis! ({device_state['food_level']:.0f}%)")
        print(f"[Simulator] ⚠️  PERINGATAN: Makanan hampir habis!")

# ─── Publish Functions ────────────────────────────────────────
def publish_status():
    payload = {
        **device_state,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "food_level": round(device_state["food_level"], 1),
    }
    client.publish(TOPIC_STATUS, json.dumps(payload), retain=True)
    print(f"[Simulator] 📤 Status dipublikasikan | Food: {payload['food_level']}%")

def publish_food_level():
    payload = {
        "device_id" : DEVICE_ID,
        "food_level": round(device_state["food_level"], 1),
        "timestamp" : datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    client.publish(TOPIC_FOODLEVEL, json.dumps(payload))

def publish_log(message: str):
    payload = {
        "device_id": DEVICE_ID,
        "message"  : message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    client.publish(TOPIC_LOG, json.dumps(payload))

# ─── Drift Simulator (Natural food level decrease) ───────────
def natural_drift():
    """Simulasi penurunan makanan secara alami (bergerak ± sedikit)"""
    while True:
        time.sleep(60)  # Setiap 1 menit
        if not device_state["is_feeding"] and device_state["food_level"] > 0:
            device_state["food_level"] = max(
                0,
                device_state["food_level"] - random.uniform(0.1, 0.3)
            )
            # Simulasi fluktuasi sinyal WiFi
            device_state["wifi_rssi"] = random.randint(-65, -35)
            publish_food_level()

# ─── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  🐾 IoT Pet Feeder - Device Simulator")
    print(f"  Device ID : {DEVICE_ID}")
    print(f"  Broker    : {MQTT_BROKER}:{MQTT_PORT}")
    print("=" * 55)
    print("\n[Simulator] Menghubungkan ke MQTT broker...")

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    # LWT (offline message jika simulator mati tiba-tiba)
    lwt_payload = json.dumps({"device_id": DEVICE_ID, "online": False})
    client.will_set(TOPIC_STATUS, lwt_payload, retain=True)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except ConnectionRefusedError:
        print("\n❌ MQTT Broker tidak ditemukan!")
        print("   Pastikan Mosquitto broker sedang berjalan.")
        print("   Install: pip install paho-mqtt")
        print("   Broker : https://mosquitto.org/download/\n")
        return

    # Jalankan drift simulator di background
    drift_thread = threading.Thread(target=natural_drift, daemon=True)
    drift_thread.start()

    print("\n[Simulator] 🟢 Simulator berjalan. Tekan Ctrl+C untuk berhenti.\n")

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[Simulator] Simulator dihentikan.")
        device_state["online"] = False
        publish_status()
        client.disconnect()

if __name__ == "__main__":
    main()
