"""
utils/ffmpeg_utils.py  —  SPEED OPTIMISED
• Screenshots extracted IN PARALLEL (asyncio.gather, not sequential loop)
• FFmpeg uses -threads 0 (auto), ultrafast preset, input seeking (-ss before -i)
• Collage built with Pillow (no extra FFmpeg call)
• All subprocesses share a semaphore to avoid CPU thrashing
"""
import asyncio
import json
import math
import os
import random
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from config import Config

# ── Limit concurrent FFmpeg processes (avoid CPU thrash on small containers) ──
_SEM = asyncio.Semaphore(4)


# ─────────────────────────── helpers ─────────────────────────────────────────

def _tmpdir() -> Path:
    d = Path(Config.TEMP_DIR) / str(uuid.uuid4())
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _run(cmd: List[str]) -> Tuple[str, str, int]:
    async with _SEM:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def _hms(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ─────────────────────────── media info ───────────────────────────────────────

async def get_media_info(file_path: str) -> dict:
    cmd = [
        Config.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    stdout, _, rc = await _run(cmd)
    if rc != 0:
        return {}

    data = json.loads(stdout)
    info = {
        "duration": 0.0,
        "size":     os.path.getsize(file_path),
        "resolution": "N/A",
        "fps":        "N/A",
        "vcodec":     "N/A",
        "acodec":     "N/A",
        "abitrate":   "N/A",
        "vbitrate":   "N/A",
    }

    fmt = data.get("format", {})
    info["duration"] = float(fmt.get("duration", 0))

    for stream in data.get("streams", []):
        ctype = stream.get("codec_type")
        if ctype == "video" and info["resolution"] == "N/A":
            w, h = stream.get("width", 0), stream.get("height", 0)
            info["resolution"] = f"{w}x{h}"
            info["vcodec"]     = stream.get("codec_name", "N/A")
            info["vbitrate"]   = stream.get("bit_rate", fmt.get("bit_rate", "N/A"))
            rfr = stream.get("r_frame_rate", "0/1")
            try:
                num, den   = rfr.split("/")
                info["fps"] = f"{int(num) / max(int(den), 1):.3f}"
            except Exception:
                info["fps"] = rfr
        elif ctype == "audio" and info["acodec"] == "N/A":
            info["acodec"]   = stream.get("codec_name", "N/A")
            info["abitrate"] = stream.get("bit_rate", "N/A")

    return info


def format_media_info(info: dict, file_name: str) -> str:
    dur_str  = _hms(info.get("duration", 0))
    size_str = _human_size(info.get("size", 0))

    vbr = info.get("vbitrate", "N/A")
    abr = info.get("abitrate", "N/A")
    if str(vbr).isdigit():
        vbr = f"{int(vbr) // 1000} kb/s"
    if str(abr).isdigit():
        abr = f"{int(abr) // 1000} kb/s"

    return (
        "📊 <b>Media Information</b>\n\n"
        f"🎬 <b>File:</b> <code>{file_name}</code>\n"
        f"⏱ <b>Duration:</b> <code>{dur_str}</code>\n"
        f"📐 <b>Resolution:</b> <code>{info.get('resolution', 'N/A')}</code>\n"
        f"🎞 <b>Video Codec:</b> <code>{info.get('vcodec', 'N/A')}</code>\n"
        f"🔊 <b>Audio Codec:</b> <code>{info.get('acodec', 'N/A')}</code>\n"
        f"📺 <b>FPS:</b> <code>{info.get('fps', 'N/A')}</code>\n"
        f"📦 <b>File Size:</b> <code>{size_str}</code>\n"
        f"📡 <b>Video Bitrate:</b> <code>{vbr}</code>\n"
        f"🔉 <b>Audio Bitrate:</b> <code>{abr}</code>\n"
    )


# ─────────────────────────── screenshots (parallel) ───────────────────────────

async def _extract_one_frame(
    file_path: str,
    ts: float,
    out_path: str,
    watermark: bool,
    watermark_text: str,
) -> Optional[str]:
    """Extract a single frame at timestamp `ts`. Returns path or None."""
    cmd = [
        Config.FFMPEG_PATH,
        "-ss", f"{ts:.3f}",      # ← BEFORE -i = fast input seek
        "-i", file_path,
        "-vframes", "1",
        "-q:v", "2",
        "-threads", "0",          # auto thread count
        "-y",
        out_path,
    ]
    _, _, rc = await _run(cmd)
    if rc != 0 or not os.path.isfile(out_path):
        return None
    if watermark:
        return await _watermark_photo(out_path, watermark_text)
    return out_path


async def take_screenshots(
    file_path: str,
    count: int,
    mode: str = "even",
    watermark: bool = False,
    watermark_text: str = Config.WATERMARK_TEXT,
) -> List[str]:
    """Extract `count` frames ALL IN PARALLEL. Returns list of PNG paths."""
    info = await get_media_info(file_path)
    duration = float(info.get("duration", 0))
    if duration < 1:
        raise ValueError("Video duration too short or unreadable.")

    out_dir = _tmpdir()

    # Build timestamps
    if mode == "random":
        timestamps = sorted(random.uniform(0.5, duration - 0.5) for _ in range(count))
    else:
        step = duration / (count + 1)
        timestamps = [step * (i + 1) for i in range(count)]

    # Launch ALL extractions simultaneously  ← KEY SPEED WIN
    tasks = [
        _extract_one_frame(
            file_path,
            ts,
            str(out_dir / f"ss_{i+1:03d}.png"),
            watermark,
            watermark_text,
        )
        for i, ts in enumerate(timestamps)
    ]
    results = await asyncio.gather(*tasks)
    return [p for p in results if p is not None]


async def _watermark_photo(image_path: str, text: str) -> str:
    out_path = image_path.replace(".png", "_wm.png")
    cmd = [
        Config.FFMPEG_PATH,
        "-i", image_path,
        "-vf",
        (
            f"drawtext=text='{text}':fontsize=28:fontcolor=white@0.75:"
            "x=w-tw-12:y=h-th-12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        ),
        "-threads", "0",
        "-y", out_path,
    ]
    _, _, rc = await _run(cmd)
    return out_path if rc == 0 and os.path.isfile(out_path) else image_path


async def make_tile_collage(image_paths: List[str]) -> str:
    """Build a grid collage with Pillow (fast, no extra FFmpeg call)."""
    from PIL import Image

    count  = len(image_paths)
    cols   = 2 if count <= 4 else 3
    rows   = math.ceil(count / cols)
    images = [Image.open(p).convert("RGB") for p in image_paths]

    cell_w  = max(im.width  for im in images)
    cell_h  = max(im.height for im in images)
    pad     = 4

    canvas = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad),
        (18, 18, 18),
    )
    for idx, im in enumerate(images):
        row, col = divmod(idx, cols)
        canvas.paste(
            im.resize((cell_w, cell_h), Image.LANCZOS),
            (pad + col * (cell_w + pad), pad + row * (cell_h + pad)),
        )

    out_path = str(Path(image_paths[0]).parent / "collage.jpg")
    canvas.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


# ─────────────────────────── trim ─────────────────────────────────────────────

async def trim_video(
    file_path: str,
    start: str,
    end: str,
    watermark: bool = False,
    watermark_text: str = Config.WATERMARK_TEXT,
) -> str:
    out_dir  = _tmpdir()
    ext      = Path(file_path).suffix or ".mp4"
    out_path = str(out_dir / f"trimmed{ext}")

    vf = []
    if watermark:
        vf.append(
            f"drawtext=text='{watermark_text}':fontsize=28:fontcolor=white@0.7:"
            "x=w-tw-12:y=12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )

    cmd = [
        Config.FFMPEG_PATH,
        "-ss", start,             # fast input seek
        "-i", file_path,
        "-to", end,
        "-c:v", "libx264",
        "-preset", "ultrafast",   # ← fastest encode
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "0",
        "-movflags", "+faststart",
    ]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-y", out_path]

    _, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"FFmpeg trim failed:\n{stderr[-500:]}")
    return out_path


# ─────────────────────────── sample video ─────────────────────────────────────

async def generate_sample(
    file_path: str,
    duration: int = 30,
    watermark: bool = False,
    watermark_text: str = Config.WATERMARK_TEXT,
) -> str:
    info      = await get_media_info(file_path)
    total_dur = float(info.get("duration", 0))
    if total_dur < duration:
        raise ValueError("Video is shorter than the sample duration.")

    start = max(0.0, total_dur / 2 - duration / 2)

    out_dir  = _tmpdir()
    ext      = Path(file_path).suffix or ".mp4"
    out_path = str(out_dir / f"sample{ext}")

    vf = []
    if watermark:
        vf.append(
            f"drawtext=text='{watermark_text}':fontsize=28:fontcolor=white@0.7:"
            "x=w-tw-12:y=12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )

    cmd = [
        Config.FFMPEG_PATH,
        "-ss", f"{start:.3f}",   # fast input seek
        "-i", file_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "0",
        "-movflags", "+faststart",
    ]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-y", out_path]

    _, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"FFmpeg sample failed:\n{stderr[-500:]}")
    return out_path


# ─────────────────────────── thumbnails ───────────────────────────────────────

async def extract_thumbnails(file_path: str, count: int = 4) -> List[str]:
    """Reuse take_screenshots with even spacing — already parallel."""
    return await take_screenshots(file_path, count, mode="even", watermark=False)
