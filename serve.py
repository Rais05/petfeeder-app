"""
=============================================================
  PetFeeder IoT — HTTP Server
  Menyajikan web app lewat HTTP (wajib untuk PWA & Service Worker)
  Jalankan: python serve.py
  Buka di HP: http://<IP_KOMPUTER_ANDA>:8080
=============================================================
"""

import http.server
import socketserver
import socket
import os

PORT = 8080
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """Serve frontend dengan header yang mendukung PWA & Service Worker"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        # Agar Service Worker berfungsi di semua kondisi
        self.send_header("Service-Worker-Allowed", "/")
        # Cache normal untuk assets, tapi sw.js jangan di-cache browser
        if self.path.endswith("sw.js"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        # CORS agar bisa komunikasi dengan backend
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # Hanya log request penting
        if not any(ext in args[0] for ext in [".css", ".js", ".png", ".ico"]):
            super().log_message(format, *args)

def get_local_ip():
    """Dapatkan IP lokal komputer"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "localhost"
    finally:
        s.close()

def main():
    local_ip = get_local_ip()

    print("=" * 55)
    print("  🐾 PetFeeder IoT — Web Server")
    print("=" * 55)
    print(f"\n  📱 Buka di Handphone (WiFi sama):")
    print(f"     http://{local_ip}:{PORT}")
    print(f"\n  💻 Buka di Komputer:")
    print(f"     http://localhost:{PORT}")
    print(f"\n  📲 Cara Install di HP:")
    print(f"     Android: Buka Chrome → Menu (⋮) → 'Add to Home Screen'")
    print(f"     iPhone : Buka Safari → Share (□↑) → 'Add to Home Screen'")
    print(f"\n  ⚠️  Pastikan HP dan Komputer terhubung ke WiFi yang sama!")
    print(f"\n  Tekan Ctrl+C untuk menghentikan server")
    print("=" * 55 + "\n")

    with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  Server dihentikan.")

if __name__ == "__main__":
    main()
