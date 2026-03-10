# 📱 PetFeeder IoT - Mobile App Guide

Panduan lengkap untuk menggunakan PetFeeder IoT di smartphone Anda sebagai Progressive Web App (PWA).

## 🚀 Cara Install di Smartphone

### **Android**

#### **Chrome / Edge / Samsung Internet**
1. Buka aplikasi di browser: `http://[your-server]:8000/app` atau buka file `index.html`
2. Tunggu sampai muncul banner **"Pasang di Layar Utama?"** (atau akses menu)
3. Klik **"Pasang"** untuk install
4. Aplikasi akan muncul di layar utama (seperti app biasa)
5. Buka aplikasi dengan tap icon di layar utama

**Jika banner tidak muncul:**
- Tap menu ⋮ (tiga titik) → **"Install app"** atau **"Add to Home screen"**

#### **Firefox**
- Open menu (≡) → **"Add to Home screen"**

---

### **iPhone / iPad (iOS)**

**iPhone tidak punya "Install" seperti Android, tapi bisa di-bookmark ke home screen:**

1. Buka aplikasi di Safari
2. Tap tombol **Share** (kotak dengan panah)
3. Pilih **"Add to Home Screen"**
4. Berikan nama (contoh: "PetFeeder")
5. Tap **"Add"**
6. Aplikasi akan muncul di home screen seperti app biasa

---

## 📲 Fitur Mobile

### **Offline Support**
- Jika koneksi terputus, banner merah **"Anda sedang offline"** muncul
- Aplikasi tetap bisa digunakan (tapi hanya fitur yang sudah di-cache)
- Otomatis tersambung kembali saat koneksi aktif

### **Pull-to-Refresh**
- Tarik layar dari atas sambil scroll di paling atas
- Aplikasi akan refresh status perangkat
- Toast notifikasi menunjukkan status refresh

### **Touch Feedback**
- Setiap kali klik tombol, smartphone akan bergetar (haptic feedback)
- Icons dan UI responsif terhadap sentuhan dengan tap target yang besar

### **Virtual Keyboard**
- Saat input form (tambah jadwal), keyboard terbuka otomatis
- Layar scroll agar input tidak tertutup keyboard

### **Notch/Safe Area Support**
- Otomatis menghindari notch (iPhone X, Pixel 3 XL, dll)
- Aman untuk semua smartphone modern

---

## 🎯 Menggunakan Aplikasi di HP

### **Dashboard**
- **Status Perangkat**: Online/Offline indicator
- **Level Makanan**: Gauge visual dengan warna status
- **Stat Cards**: Quick view feeding count, last feed time, WiFi signal

### **Beri Makan Manual**
1. Pilih porsi (25g, 50g, 100g, 150g) atau gunakan slider
2. Tap tombol **"Beri Makan!"** dengan icon 🍽️
3. Tunggu overlay animasi selesai (±3-5 detik)
4. Toast notifikasi menunjukkan hasil (success/error)

### **Jadwal Otomatis**
1. Tap card **"Jadwal Pemberian Makan"**
2. Form muncul untuk input:
   - **Jam** (0-23)
   - **Menit** (0-59)
   - **Porsi** (gram)
   - **Label** (nama jadwal, opsional)
   - **Hari Aktif** (pilih hari M-S)
3. Tap **"Simpan Jadwal"**
4. Jadwal muncul di list bawah

### **Riwayat Pemberian**
1. Scroll ke bawah di halaman kanan
2. Lihat **"Riwayat Pemberian Makan"** dengan:
   - Waktu pemberian
   - Porsi
   - Tipe trigger (manual/jadwal)
   - Kondisi (success/failed)

### **Settings**
Di section settings, atur:
- **Nama Hewan Peliharaan** (digunakan di UI)
- **Porsi Default** (gram)
- **Alert Level** (kapan warning muncul, % makanan)

---

## 🔧 Network/Connection Requirements

### **Home Network (Recommended)**
- Server & smartphone di **network yang sama (WiFi)**
- IP perangkat: `192.168.x.x` atau `localhost`
- **No internet required**, hanya network lokal

**Setup:**
```bash
# Di PC/server
python backend/main.py  # port 8000 default

# Di HP
# Buka: http://[IP-PC]:8000/app
# Contoh: http://192.168.1.100:8000/app
```

### **Remote Access (CloudFlare Tunnel / Ngrok)**
Jika ingin akses dari luar rumah:

**Option A: CloudFlare Tunnel**
```bash
# Di folder project
python get_tunnel_url.py
# Copy URL dan buka di HP dari mana saja
```

**Option B: Ngrok**
```bash
ngrok http 8000
# Copy forwarding URL dan gunakan di HP
```

⚠️ **Caution**: Pastikan password/auth jika expose ke internet!

---

## 📊 Best Practices

### **Performance**
- Aplikasi disimpan di cache, loading cepat meskipun offline
- Update real-time via SSE (Server-Sent Events)
- Polling fallback setiap 10 detik

### **Battery Usage**
- SSE connection tetap terbuka → normal battery usage
- Jika ingin hemat, kontrol manual saja (tidak perlu monitor real-time)
- Vibration hanya aktif saat interaksi user (bukan background)

### **Data Usage**
- SSE streaming minimal (hanya kirim delta changes)
- Static assets (HTML/CSS/JS) di-cache, tidak re-download
- Estimasi: **<5MB/hari** untuk usage normal

### **Screen Size Optimization**
- **Smartphone Portrait**: Optimal display untuk semua fitur
- **Tablet Landscape**: Grid 2 columns, lebih spacious
- **Very Small Screen (< 380px)**: Status cards 1 column

---

## 🐛 Troubleshooting

### **Aplikasi tidak install di home screen?**
- Pastikan browser support PWA (Chrome, Edge, Firefox, Samsung Internet)
- Install banner hanya muncul jika app diakses via HTTPS atau localhost
- Coba refresh halaman atau restart browser

### **Tidak bisa connect ke server?**
- Pastikan server backend sedang jalan: `python backend/main.py`
- Check IP/URL: buka browser, coba akses langsung API
- Cek firewall: port 8000 harus accessible dari HP

### **Offline banner muncul tapi sebenarnya online?**
- Check status bar → apakah WiFi/data aktif?
- Restart browser atau clear cache:
  - **Devtools** → **Application** → **Clear All** → Refresh

### **Vibration tidak bekerja?**
- Bukan semua browser/HP support vibration API
- iPhone tidak punya vibration untuk PWA (hanya via native app)
- Check settings HP: vibration aktif di settings?

### **Feed button disabled?**
- Device sedang offline (lihat badge status)
- Device sedang feeding (tunggu selesai ±3-5 detik)
- Backend tidak jalan

---

## 📚 Technical Details

### **PWA Features**
- ✅ **Installable**: Add to home screen (Android) / Safari (iOS)
- ✅ **Offline-First**: Service worker + cache strategy
- ✅ **Responsive**: Mobile-first design, notch support
- ✅ **Real-time**: SSE untuk live updates
- ✅ **Touch**: Swipe, pull-to-refresh, haptic feedback

### **Browser Support**
| Feature | Chrome | Firefox | Safari (iOS) | Edge |
|---------|--------|---------|--------------|------|
| PWA Install | ✅ | ❌ | Via bookmark | ✅ |
| Service Worker | ✅ | ✅ | ✅ (iOS 16+) | ✅ |
| Vibration | ✅ | ✅ | ❌ | ✅ |
| SSE | ✅ | ✅ | ✅ | ✅ |
| Storage | ✅ | ✅ | ✅ | ✅ |

---

## 📞 Support

Jika ada issue:
1. Check browser console (F12 → Console) untuk error
2. Cek backend logs (terminal server)
3. Try clear cache & reload
4. Restart server & app

---

**Selamat menggunakan PetFeeder IoT di smartphone Anda! 🐾📱**
