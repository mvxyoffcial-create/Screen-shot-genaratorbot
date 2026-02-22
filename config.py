import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Telegram ──────────────────────────────────────────────────────────────
    API_ID    = 20288994
    API_HASH  = "d702614912f1ad370a0d18786002adbf"
    BOT_TOKEN = "8246495508:AAHiNBoeiZCbK0Ozrq5b7LeZP3q0vAnA1r4"

    # ── Admins (comma-separated Telegram user IDs) ────────────────────────────
    ADMIN_IDS = [8108646188]

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGO_URI = "mongodb+srv://Zerobothost:zero8907@cluster0.szwdcyb.mongodb.net/?appName=Cluster0"
    DB_NAME   = "screenshot_bot"

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
    FFMPEG_PATH  = "ffmpeg"
    FFPROBE_PATH = "ffprobe"

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
    TEMP_DIR = "/tmp/ss_bot"

    # ── Watermark text ────────────────────────────────────────────────────────
    WATERMARK_TEXT = "@zerodev2"

    # ── Max watermark text length ─────────────────────────────────────────────
    WATERMARK_MAX_LEN = 32
