"""Script untuk menjalankan cloudflared dan menampilkan URL lengkap"""
import subprocess
import sys
import re

CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"

print("Memulai cloudflared tunnel...")
print("Menunggu URL...\n")

proc = subprocess.Popen(
    [CLOUDFLARED, "tunnel", "--url", "http://localhost:8080"],
    stderr=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace"
)

url_found = False
try:
    for line in proc.stderr:
        line = line.strip()
        # Cari URL trycloudflare
        if "trycloudflare.com" in line:
            match = re.search(r'https://[\w\-]+\.trycloudflare\.com', line)
            if match:
                url = match.group(0)
                print("=" * 60)
                print(f"  URL APLIKASI DI HP:")
                print(f"  {url}")
                print("=" * 60)
                # Simpan ke file
                with open("cf_url.txt", "w") as f:
                    f.write(url)
                url_found = True
        # Tampilkan baris penting lainnya
        if "ERR" in line or "INF" in line:
            print(line)
except KeyboardInterrupt:
    print("\nTunnel dihentikan.")
    proc.terminate()
