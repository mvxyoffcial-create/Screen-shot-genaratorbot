import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Telegram ──────────────────────────────────────────────────────────────
    API_ID    = int(os.environ.get("API_ID", 0))
    API_HASH  = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # ── Admins (comma-separated Telegram user IDs) ────────────────────────────
    ADMIN_IDS = list(
        map(int, filter(None, os.environ.get("ADMIN_IDS", "").split(",")))
    )

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME   = os.environ.get("DB_NAME", "screenshot_bot")

    # ── Force Subscribe channels (username WITHOUT @) ─────────────────────────
    FSUB_CHANNELS = ["zerodev2", "mvxyoffcail"]

    # ── Force-sub banner image ────────────────────────────────────────────────
    FSUB_IMAGE = "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"

    # ── Owner / branding ──────────────────────────────────────────────────────
    OWNER_USERNAME = "Venuboyy"
    UPDATE_CHANNEL = "zerodev2"

    # ── Welcome sticker file_id ───────────────────────────────────────────────
    WELCOME_STICKER = (
        "CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgAC"
        "tCMAAphLKUjeub7NKlvk2TgE"
    )

    # ── Wallpaper API ─────────────────────────────────────────────────────────
    WALLPAPER_API = "https://api.aniwallpaper.workers.dev/random?type=girl"

    # ── Web server port (Koyeb / Railway / Render) ────────────────────────────
    PORT = int(os.environ.get("PORT", 8080))

    # ── FFmpeg paths ──────────────────────────────────────────────────────────
    FFMPEG_PATH  = os.environ.get("FFMPEG_PATH", "ffmpeg")
    FFPROBE_PATH = os.environ.get("FFPROBE_PATH", "ffprobe")

    # ── Max upload size ───────────────────────────────────────────────────────
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB

    # ── Default per-user settings ─────────────────────────────────────────────
    DEFAULT_SETTINGS = {
        "upload_mode":     "tile",   # "tile" | "separate"
        "sample_duration": 30,       # seconds
        "screenshot_mode": "even",   # "even" | "random"
        "watermark_video": False,
        "watermark_photo": False,
    }

    # ── Supported video extensions ────────────────────────────────────────────
    VIDEO_EXTENSIONS = {
        ".mp4", ".mkv", ".avi", ".mov",
        ".webm", ".flv", ".mpeg", ".mpg",
    }

    # ── Temp working directory ────────────────────────────────────────────────
    TEMP_DIR = os.environ.get("TEMP_DIR", "/tmp/ss_bot")

    # ── Watermark text ────────────────────────────────────────────────────────
    WATERMARK_TEXT = "@zerodev2"
