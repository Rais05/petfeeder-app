# 🎨 PetFeeder Icons

Folder ini berisi icon files untuk aplikasi PWA.

## Files

- **icon-192.svg** — Vector icon 192×192px
- **icon-512.svg** — Vector icon 512×512px
- **icon-192.png** — PNG icon 192×192px (placeholder, perlu di-generate)
- **icon-512.png** — PNG icon 512×512px (placeholder, perlu di-generated)
- **icon-generator.html** — Tool untuk generate PNG dari canvas

## Setup Icons (PENTING untuk PWA)

### Option 1: Convert SVG → PNG (Rekomendasi)

**Tool Online:**
1. Buka: https://convertio.co/svg-png/ atau https://cloudconvert.com/svg-to-png
2. Upload `icon-192.svg`
3. Download hasil as `icon-192.png` → save ke folder ini
4. Repeat untuk `icon-512.svg` → `icon-512.png`

### Option 2: Generate dengan HTML Tool

1. Buka `icon-generator.html` di browser
2. Klik **"📥 Download 192x192"**
3. Save sebagai `icon-192.png` di folder ini
4. Klik **"📥 Download 512x512"**
5. Save sebagai `icon-512.png` di folder ini

### Option 3: Gunakan Tool Lain

Beberapa tool yang bisa digunakan:
- **GIMP** — Open SVG, export as PNG
- **Inkscape** — SVG editor, export PNG
- **ImageMagick** (CLI): `convert icon-192.svg icon-192.png`
- **FFmpeg** (CLI): `ffmpeg -i icon-192.svg icon-192.png`

---

## Verify Icons

Setelah PNG files ada, cek:
1. File size: ~5-10KB untuk 192px, ~20-30KB untuk 512px
2. Buka file di browser — seharusnya muncul paw design dengan gradient
3. Buka `../index.html` → PWA install banner seharusnya muncul

---

## Spec

| Icon | Ukuran | Format | Usage |
|------|--------|--------|-------|
| icon-192 | 192×192px | PNG | Home screen icon, browser tab |
| icon-512 | 512×512px | PNG | Splash screen, app drawer |

**Format wajib:** PNG dengan transparent background (optional) atau solid background.

---

Setelah icon PNG tersedia, aplikasi PWA siap di-install di smartphone! 🐾
