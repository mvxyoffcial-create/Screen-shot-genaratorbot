# ─────────────────────────────────────────────────────────────────────────────
# Video Screenshot Bot – Dockerfile
# Compatible with: Koyeb, Railway, Render, Fly.io, VPS (any Docker host)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System dependencies (FFmpeg + build tools) ────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        gcc \
        libffi-dev \
        libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies (cached layer) ────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy project files ────────────────────────────────────────────────────────
COPY . .

# ── Temp directory ────────────────────────────────────────────────────────────
RUN mkdir -p /tmp/ss_bot

# ── Expose port 8080 (required by Koyeb / Railway / Render) ──────────────────
EXPOSE 8080

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# ── Run ───────────────────────────────────────────────────────────────────────
CMD ["python", "bot.py"]
