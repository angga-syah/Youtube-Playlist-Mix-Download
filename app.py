import os
import json
import queue
import threading
import webbrowser
import re
import yt_dlp
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for

app = Flask(__name__)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

progress_queues: dict[str, queue.Queue] = {}


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_download_dir() -> str:
    return load_config().get("download_dir", "")


# ── Redirect to setup if not configured ──────────────────────────────────────

@app.before_request
def check_setup():
    if request.endpoint in ("setup", "save_settings", "static"):
        return
    if not get_download_dir():
        return redirect(url_for("setup"))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", download_dir=get_download_dir())


@app.route("/setup", methods=["GET", "POST"])
def setup():
    error = None
    if request.method == "POST":
        path = (request.form.get("download_dir") or "").strip()
        if not path:
            error = "Folder tidak boleh kosong."
        else:
            try:
                os.makedirs(path, exist_ok=True)
                save_config({"download_dir": path})
                return redirect(url_for("index"))
            except Exception as exc:
                error = f"Folder tidak bisa dibuat: {exc}"
    return render_template("setup.html", error=error,
                           suggested=os.path.join(os.path.expanduser("~"), "Downloads", "YT"))


@app.route("/settings", methods=["POST"])
def save_settings():
    data = request.json
    path = (data.get("download_dir") or "").strip()
    if not path:
        return jsonify({"error": "Path kosong"}), 400
    try:
        os.makedirs(path, exist_ok=True)
        cfg = load_config()
        cfg["download_dir"] = path
        save_config(cfg)
        return jsonify({"ok": True, "download_dir": path})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Utilities ─────────────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def _is_radio_url(url: str) -> bool:
    import urllib.parse as _up
    try:
        params = _up.parse_qs(_up.urlparse(url).query)
        list_id = (params.get("list") or [""])[0]
        return list_id.startswith("RD") or "start_radio=1" in url
    except Exception:
        return False


# ── Fetch info ────────────────────────────────────────────────────────────────

@app.route("/fetch", methods=["POST"])
def fetch():
    data = request.json
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL kosong"}), 400

    limit = data.get("limit")
    try:
        limit = int(limit) if limit else None
    except (ValueError, TypeError):
        limit = None

    is_radio = _is_radio_url(url)
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    if limit:
        ydl_opts["playlistend"] = limit

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info.get("_type") == "playlist":
            tracks = []
            for i, entry in enumerate(info.get("entries") or [], 1):
                vid_id = entry.get("id", "")
                vid_url = entry.get("url") or entry.get("webpage_url") or (
                    f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""
                )
                tracks.append({
                    "index": i, "id": vid_id, "url": vid_url,
                    "title": entry.get("title") or f"Track {i}",
                    "custom_name": entry.get("title") or f"Track {i}",
                    "duration": entry.get("duration"),
                })
            return jsonify({
                "type": "playlist",
                "title": info.get("title") or "Playlist",
                "count": len(tracks),
                "tracks": tracks,
                "is_radio": is_radio,
                "limited": limit is not None,
            })
        else:
            title = info.get("title") or "Video"
            return jsonify({
                "type": "video", "title": title, "count": 1,
                "tracks": [{
                    "index": 1, "id": info.get("id", ""), "url": url,
                    "title": title, "custom_name": title,
                    "duration": info.get("duration"),
                }],
                "is_radio": False, "limited": False,
            })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Formats ───────────────────────────────────────────────────────────────────

@app.route("/formats", methods=["POST"])
def get_formats():
    url = ((request.json or {}).get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL kosong"}), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        video_map: dict = {}   # height → best entry
        audio_map: dict = {}   # (ext, bitrate_bucket) → best entry

        for f in (info.get("formats") or []):
            vc  = f.get("vcodec") or "none"
            ac  = f.get("acodec") or "none"
            has_v = vc != "none"
            has_a = ac != "none"
            fid   = f.get("format_id", "")
            ext   = f.get("ext", "")
            size  = f.get("filesize") or f.get("filesize_approx")
            tbr   = f.get("tbr") or 0

            if has_v:
                h = f.get("height") or 0
                combined = has_a
                cur = video_map.get(h)
                # Prefer combined > video-only; within same type prefer higher tbr
                if cur is None or (combined and not cur["combined"]) or \
                   (combined == cur["combined"] and tbr > cur["tbr"]):
                    video_map[h] = {
                        "height": h, "ext": ext, "combined": combined,
                        "size": size, "tbr": tbr, "format_id": fid, "vcodec": vc,
                    }
            elif has_a:
                abr    = f.get("abr") or 0
                bucket = round(abr / 16) * 16   # group nearby bitrates
                key    = (ext, bucket)
                cur = audio_map.get(key)
                if cur is None or abr > cur["abr"]:
                    audio_map[key] = {
                        "ext": ext, "abr": abr,
                        "size": size, "format_id": fid,
                    }

        video_list = sorted(video_map.values(),
                            key=lambda x: x["height"], reverse=True)
        audio_list = sorted(audio_map.values(),
                            key=lambda x: x["abr"], reverse=True)
        # MP3 option (always last, needs FFmpeg)
        audio_list.append({"ext": "mp3", "abr": 192, "size": None,
                           "format_id": "mp3", "needs_ffmpeg": True})

        return jsonify({"video": video_list, "audio": audio_list})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Download ──────────────────────────────────────────────────────────────────

@app.route("/download", methods=["POST"])
def download():
    data       = request.json
    tracks     = data.get("tracks") or []
    session_id = data.get("session_id", "default")
    subfolder  = sanitize_filename(data.get("subfolder") or "")

    # Format selection — new (format_id) or legacy (format+quality)
    format_id   = data.get("format_id")      # e.g. "137", "140", "mp3"
    needs_merge = data.get("needs_merge", False)
    target_ext  = data.get("ext", "mp4")

    # Legacy fallback
    fmt     = data.get("format", "mp4")
    quality = data.get("quality", "best")

    base = get_download_dir()
    target_dir = os.path.join(base, subfolder) if subfolder else base
    os.makedirs(target_dir, exist_ok=True)

    if session_id not in progress_queues:
        progress_queues[session_id] = queue.Queue()
    q = progress_queues[session_id]

    def build_opts(safe_name: str) -> dict:
        outtmpl = os.path.join(target_dir, f"{safe_name}.%(ext)s")

        # ── New: specific format_id ──
        if format_id:
            if format_id == "mp3":
                return {
                    "format": "bestaudio/best", "outtmpl": outtmpl,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3", "preferredquality": "192",
                    }],
                    "quiet": True,
                }
            if needs_merge:
                return {
                    "format": f"{format_id}+bestaudio/{format_id}",
                    "merge_output_format": target_ext,
                    "outtmpl": outtmpl,
                    "quiet": True,
                }
            return {"format": format_id, "outtmpl": outtmpl, "quiet": True}

        # ── Legacy: format + quality dropdowns ──
        if fmt == "mp3":
            return {
                "format": "bestaudio/best", "outtmpl": outtmpl,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3", "preferredquality": "192",
                }],
                "quiet": True,
            }
        h = "" if quality == "best" else f"[height<={quality}]"
        return {
            "format": f"bestvideo{h}+bestaudio/best{h}/best",
            "merge_output_format": fmt,
            "outtmpl": outtmpl, "quiet": True,
        }

    def do_download():
        total = len(tracks)
        for idx, track in enumerate(tracks, 1):
            name = track.get("custom_name") or f"Track {idx}"
            safe = sanitize_filename(name)
            url  = track.get("url", "")

            q.put({"type": "progress", "current": idx, "total": total,
                   "name": name, "status": "downloading"})
            try:
                with yt_dlp.YoutubeDL(build_opts(safe)) as ydl:
                    ydl.download([url])
                q.put({"type": "progress", "current": idx, "total": total,
                       "name": name, "status": "done"})
            except Exception as exc:
                q.put({"type": "progress", "current": idx, "total": total,
                       "name": name, "status": "error", "error": str(exc)})

        q.put({"type": "complete", "target_dir": target_dir})

    threading.Thread(target=do_download, daemon=True).start()
    return jsonify({"status": "started"})


# ── SSE progress ──────────────────────────────────────────────────────────────

@app.route("/progress/<session_id>")
def progress_stream(session_id):
    if session_id not in progress_queues:
        progress_queues[session_id] = queue.Queue()
    q = progress_queues[session_id]

    def generate():
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") == "complete":
                    progress_queues.pop(session_id, None)
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    addr = "http://localhost:5000"
    threading.Timer(1.2, lambda: webbrowser.open(addr)).start()
    print(f"\n  YT Downloader → {addr}\n  Ctrl+C untuk berhenti.\n")
    app.run(debug=False, port=5000, threaded=True)
