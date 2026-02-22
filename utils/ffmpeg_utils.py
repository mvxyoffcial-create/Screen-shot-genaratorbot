"""
utils/ffmpeg_utils.py
All FFmpeg / FFprobe operations:
  - get_media_info
  - take_screenshots (even or random timestamps)
  - make_tile_collage
  - trim_video
  - generate_sample
  - extract_thumbnails
  - add_video_watermark
"""
import asyncio
import json
import math
import os
import random
import uuid
from pathlib import Path
from typing import List, Tuple

from config import Config


# ─────────────────────────── internal helpers ─────────────────────────────────

def _tmpdir() -> Path:
    d = Path(Config.TEMP_DIR) / str(uuid.uuid4())
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _run(cmd: List[str]) -> Tuple[str, str, int]:
    """Run subprocess asynchronously and return (stdout, stderr, returncode)."""
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
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ─────────────────────────── media info ───────────────────────────────────────

async def get_media_info(file_path: str) -> dict:
    """Return parsed media metadata dict."""
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
        "fps":       "N/A",
        "vcodec":    "N/A",
        "acodec":    "N/A",
        "abitrate":  "N/A",
        "vbitrate":  "N/A",
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
                num, den = rfr.split("/")
                info["fps"] = f"{int(num) / max(int(den), 1):.3f}"
            except Exception:
                info["fps"] = rfr
        elif ctype == "audio" and info["acodec"] == "N/A":
            info["acodec"]  = stream.get("codec_name", "N/A")
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


# ─────────────────────────── screenshots ──────────────────────────────────────

async def take_screenshots(
    file_path: str,
    count: int,
    mode: str = "even",          # "even" | "random"
    watermark: bool = False,
    watermark_text: str = Config.WATERMARK_TEXT,
) -> List[str]:
    """Extract `count` frames and return list of PNG paths."""
    info = await get_media_info(file_path)
    duration = float(info.get("duration", 0))
    if duration < 1:
        raise ValueError("Video duration is too short or unreadable.")

    out_dir = _tmpdir()

    # Compute timestamps
    if mode == "random":
        timestamps = sorted(random.uniform(0.5, duration - 0.5) for _ in range(count))
    else:
        step = duration / (count + 1)
        timestamps = [step * (i + 1) for i in range(count)]

    paths: List[str] = []
    for i, ts in enumerate(timestamps):
        out_path = str(out_dir / f"ss_{i+1:03d}.png")
        cmd = [
            Config.FFMPEG_PATH,
            "-ss", f"{ts:.3f}",
            "-i", file_path,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            out_path,
        ]
        _, _, rc = await _run(cmd)
        if rc == 0 and os.path.isfile(out_path):
            if watermark:
                out_path = await _watermark_photo(out_path, watermark_text)
            paths.append(out_path)

    return paths


async def _watermark_photo(image_path: str, text: str) -> str:
    """Burn text watermark onto a PNG using ffmpeg drawtext."""
    out_path = image_path.replace(".png", "_wm.png")
    cmd = [
        Config.FFMPEG_PATH,
        "-i", image_path,
        "-vf",
        (
            f"drawtext=text='{text}':fontsize=28:fontcolor=white@0.75:"
            "x=w-tw-12:y=h-th-12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        ),
        "-y", out_path,
    ]
    _, _, rc = await _run(cmd)
    return out_path if rc == 0 and os.path.isfile(out_path) else image_path


async def make_tile_collage(image_paths: List[str]) -> str:
    """Combine screenshots into a grid collage using Pillow."""
    from PIL import Image

    count = len(image_paths)
    cols  = 2 if count <= 4 else 3
    rows  = math.ceil(count / cols)

    images  = [Image.open(p).convert("RGB") for p in image_paths]
    cell_w  = max(im.width  for im in images)
    cell_h  = max(im.height for im in images)
    padding = 6

    canvas_w = cols * cell_w + (cols + 1) * padding
    canvas_h = rows * cell_h + (rows + 1) * padding
    canvas   = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 20))

    for idx, im in enumerate(images):
        row, col = divmod(idx, cols)
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + padding)
        canvas.paste(im.resize((cell_w, cell_h), Image.LANCZOS), (x, y))

    out_path = str(Path(image_paths[0]).parent / "collage.jpg")
    canvas.save(out_path, "JPEG", quality=92)
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

    vf_filters = []
    if watermark:
        vf_filters.append(
            f"drawtext=text='{watermark_text}':fontsize=28:fontcolor=white@0.7:"
            "x=w-tw-12:y=12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )

    cmd = [
        Config.FFMPEG_PATH,
        "-i", file_path,
        "-ss", start,
        "-to", end,
    ]

    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]

    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", out_path,
    ]

    _, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"FFmpeg trim failed:\n{stderr}")
    return out_path


# ─────────────────────────── sample video ─────────────────────────────────────

async def generate_sample(
    file_path: str,
    duration: int = 30,
    watermark: bool = False,
    watermark_text: str = Config.WATERMARK_TEXT,
) -> str:
    """Cut a sample clip from the middle of the video."""
    info       = await get_media_info(file_path)
    total_dur  = float(info.get("duration", 0))
    if total_dur < duration:
        raise ValueError("Video is shorter than sample duration.")

    mid   = total_dur / 2
    start = max(0, mid - duration / 2)

    out_dir  = _tmpdir()
    ext      = Path(file_path).suffix or ".mp4"
    out_path = str(out_dir / f"sample{ext}")

    vf_filters = []
    if watermark:
        vf_filters.append(
            f"drawtext=text='{watermark_text}':fontsize=28:fontcolor=white@0.7:"
            "x=w-tw-12:y=12:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )

    cmd = [
        Config.FFMPEG_PATH,
        "-ss", f"{start:.3f}",
        "-i", file_path,
        "-t", str(duration),
    ]

    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]

    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", out_path,
    ]

    _, stderr, rc = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"FFmpeg sample failed:\n{stderr}")
    return out_path


# ─────────────────────────── thumbnails ───────────────────────────────────────

async def extract_thumbnails(
    file_path: str,
    count: int = 4,
) -> List[str]:
    """Extract `count` evenly-spaced thumbnail frames."""
    return await take_screenshots(file_path, count, mode="even", watermark=False)
