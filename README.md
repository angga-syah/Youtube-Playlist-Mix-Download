# ▶ YT Downloader

Aplikasi web lokal untuk download video & playlist YouTube dengan fitur rename sebelum download, pilih format/kualitas, dan subfolder otomatis.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=flat-square)
![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-red?style=flat-square)

---

## Fitur

- **Video & Playlist** — download satu video atau seluruh playlist sekaligus
- **Rename massal** — beri prefix otomatis: `DJ` → `DJ 1`, `DJ 2`, `DJ 3`, ...
- **Rename individual** — edit nama tiap track langsung di UI sebelum download
- **Subfolder otomatis** — playlist langsung dibuatkan folder tersendiri
- **Pilih format** — MP4, MP3 (audio only), WebM
- **Pilih kualitas** — Best / 1080p / 720p / 480p / 360p
- **Progress bar realtime** — status per-track via Server-Sent Events
- **YouTube Radio/Mix** — deteksi otomatis + batas jumlah track
- **Setup folder** — pilih lokasi simpan saat pertama kali buka, bisa diubah kapan saja

---

## Persyaratan

| Software | Keterangan |
|---|---|
| **Python 3.10+** | Runtime utama |
| **FFmpeg** | Untuk MP3 & video 1080p+ (opsional tapi direkomendasikan) |

---

## Instalasi

### 1. Clone repo

```bash
git clone https://github.com/username/yt-downloader.git
cd yt-downloader
```

### 2. Install FFmpeg (direkomendasikan)

```bash
winget install ffmpeg
```

Atau download manual dari [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) dan tambahkan ke PATH.

### 3. Jalankan

**Windows** — double-click `start.bat`

```
start.bat akan otomatis:
- Install dependencies (flask, yt-dlp)
- Membuka browser ke http://localhost:5000
```

**Manual:**

```bash
pip install -r requirements.txt
python app.py
```

---

## Penggunaan

1. **Buka** `http://localhost:5000` di browser
2. **Setup** — pilih folder penyimpanan (hanya sekali, bisa diubah via ⚙)
3. **Tempel URL** YouTube (video atau playlist) → klik **Ambil Info**
4. **Edit nama** track jika perlu (individual atau bulk rename)
5. **Pilih** format & kualitas
6. **Download** — progress tampil realtime per track

### Bulk Rename

Isi prefix di kolom **Bulk Rename**, klik **Apply**:

```
Prefix: "DJ"  →  DJ 1, DJ 2, DJ 3, ... DJ 25
```

### YouTube Radio/Mix

Link dengan `list=RD...` terdeteksi otomatis. Batas track default **25** untuk menghindari fetch ribuan entry.

---

## Struktur File

```
yt-downloader/
├── app.py              # Backend Flask
├── requirements.txt    # Dependencies
├── start.bat           # Launcher Windows
├── PANDUAN.html        # Panduan offline (buka di browser)
├── config.json         # Dibuat otomatis saat setup pertama
└── templates/
    ├── index.html      # Halaman utama
    └── setup.html      # Halaman setup pertama kali
```

---

## Stack

- **Backend** — Python + Flask
- **Downloader** — [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Frontend** — Vanilla HTML/CSS/JS (dark theme, tanpa framework)
- **Realtime** — Server-Sent Events (SSE)

---

## Catatan

- File disimpan ke folder yang dipilih saat setup (bisa diubah via ⚙ di topbar)
- Tanpa FFmpeg: download tetap berjalan untuk 360p–720p MP4
- Untuk update yt-dlp jika tiba-tiba banyak error: `pip install -U yt-dlp`
