# 🐾 IoT Pet Feeder — Prototipe Sistem Pemberi Makan Kucing

Sistem IoT pemberi makan hewan peliharaan dengan kontrol jarak jauh melalui web app.

## Arsitektur Sistem

```
┌─────────────────┐     MQTT      ┌──────────────────┐     REST API / SSE     ┌────────────────┐
│  ESP32 Firmware │ ◄───────────► │  FastAPI Backend  │ ◄─────────────────►  │   Web App      │
│  (+ Simulator)  │               │  (Python Server)  │                        │   Dashboard    │
└─────────────────┘               └──────────────────┘                        └────────────────┘
```

## Struktur Project

```
petfeeder/
├── esp32_petfeeder/
│   ├── petfeeder_firmware.ino   # Kode Arduino untuk ESP32
│   └── device_simulator.py     # Simulator Python (tanpa hardware)
├── backend/
│   ├── main.py                 # FastAPI server utama
│   ├── mqtt_client.py          # MQTT bridge
│   ├── scheduler.py            # Jadwal otomatis
│   ├── database.py             # Penyimpanan JSON
│   └── requirements.txt
└── frontend/
    ├── index.html              # Dashboard web
    ├── style.css               # Desain premium dark mode
    └── app.js                  # Logika aplikasi
```

## Cara Menjalankan

### 1. Install Dependencies

```bash
# Backend Python
cd petfeeder/backend
pip install -r requirements.txt

# MQTT Broker (Mosquitto)
# Download: https://mosquitto.org/download/
# Windows: jalankan sebagai service atau: mosquitto -v
```

### 2. Jalankan MQTT Broker (Terminal 1)

```bash
mosquitto -v
```

### 3. Jalankan Device Simulator (Terminal 2)

```bash
cd petfeeder/esp32_petfeeder
python device_simulator.py
```

### 4. Jalankan Backend Server (Terminal 3)

```bash
cd petfeeder/backend
python main.py
# Atau: uvicorn main:app --reload --port 8000
```

### 5. Buka Web App (Browser)

- **Langsung buka file:** `petfeeder/frontend/index.html`
- **Atau via server:** http://localhost:8000/app

## Fitur Web App

| Fitur | Deskripsi |
|-------|-----------|
| 🟢 Status Live | Status online/offline perangkat real-time |
| 📊 Food Level Gauge | Indikator sisa makanan dengan peringatan |
| 🐱 Beri Makan Manual | Trigger feeding dengan porsi yang bisa diatur |
| 📅 Jadwal Otomatis | Tambah/hapus jadwal harian/mingguan |
| 📋 Riwayat | Log seluruh aktivitas pemberian makan |
| 🔴 Real-time SSE | Update otomatis tanpa refresh halaman |

## MQTT Topics

| Topic | Arah | Deskripsi |
|-------|------|-----------|
| `petfeeder/command` | Server → Device | Perintah (feed, status, calibrate) |
| `petfeeder/status` | Device → Server | Status perangkat |
| `petfeeder/foodlevel` | Device → Server | Level makanan saja |
| `petfeeder/log` | Device → Server | Log aktivitas |

## REST API Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/status` | Status perangkat |
| POST | `/api/feed/now` | Beri makan manual |
| GET | `/api/schedule` | Daftar jadwal |
| POST | `/api/schedule` | Tambah jadwal |
| DELETE | `/api/schedule/{id}` | Hapus jadwal |
| GET | `/api/history` | Riwayat feeding |
| GET | `/api/events` | SSE real-time stream |

## 📱 Aplikasi Mobile (PWA)

Aplikasi ini adalah **Progressive Web App (PWA)**, bisa digunakan di smartphone seperti native app!

### Setup Icons (Penting untuk PWA)

1. **Buka** `frontend/icons/icon-generator.html` di browser
2. **Download** icon 192×192 dan 512×512
3. **Simpan** sebagai `icon-192.png` dan `icon-512.png` di folder `icons/`

Atau gunakan online icon generator: https://www.favicon-generator.org/

### Install di Smartphone

**Android (Chrome, Edge, Firefox):**
- Buka app di browser: `http://[IP-SERVER]:8000/app`
- Tap banner **"Pasang di Layar Utama"** atau menu ⋮ → **"Install app"**

**iPhone/iPad (Safari):**
- Buka app di Safari
- Tap Share → **"Add to Home Screen"**

### Fitur Mobile

✅ **Offline Support** — Bekerja tanpa internet (cached assets)  
✅ **Real-time Updates** — SSE streaming dari server  
✅ **Touch Optimized** — Tombol besar, haptic feedback  
✅ **Pull-to-Refresh** — Tarik dari atas untuk refresh status  
✅ **Notch Support** — Aman untuk iPhone X, Pixel, dll  

📖 **Lihat [MOBILE_GUIDE.md](MOBILE_GUIDE.md) untuk panduan lengkap!**

## Hardware (untuk ESP32 Nyata)

- ESP32 Development Board
- Servo Motor SG90 / MG995 (pin 18)
- Load Cell + HX711 (pin 21, 22)
- Buzzer (pin 23)
- Kontainer makanan kucing

Ubah `WIFI_SSID`, `WIFI_PASSWORD`, dan `MQTT_BROKER` di `petfeeder_firmware.ino`.
