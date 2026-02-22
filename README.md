# 🎬 Video Screenshot Generator Bot

A professional Telegram bot built with **Pyrogram** + **FFmpeg** supporting files up to **4 GB**.  
Runs a built-in **HTTP server on port 8080** for one-click deployment to **Koyeb**, **Railway**, **Render**, **Fly.io**, or any VPS.

> **Developer:** [@Venuboyy](https://t.me/Venuboyy) · **Updates:** [@zerodev2](https://t.me/zerodev2)

---

## ✨ Features

| Feature | Details |
|---|---|
| 📸 Auto Screenshots | 2–10 frames, even or random timestamps |
| ✏️ Manual Screenshots | User-defined `HH:MM:SS` timestamps |
| ✂️ Trim Video | Cut any segment by start/end time |
| 🎬 Sample Video | 30-second preview from the middle |
| 📊 Media Info | Resolution, codec, FPS, bitrate, size |
| 🖼 Thumbnails | Extract 1–10 thumbnail frames |
| 💧 Watermark | Optional watermark on videos & photos |
| 🗂 Tile Collage | Grid layout OR separate photo upload |
| ⚙️ Per-user Settings | Persisted in MongoDB |
| 🔐 Force Subscribe | Block until both channels are joined |
| 📡 Broadcast | Admin: message all users at once |
| 📊 Stats | Admin: usage counters from MongoDB |
| 🌐 HTTP Health Check | Port 8080 for cloud platform compatibility |

---

## 👤 User Commands

| Command | Description |
|---|---|
| `/start` | Start the bot, show welcome message |
| `/help` | How to use the bot |
| `/about` | Bot info and developer details |
| `/settings` | Open your personal settings panel |
| `/cancel` | Cancel any active operation (trim / manual SS) |

### 📹 Video Workflow
1. **Send any video file** (MP4, MKV, AVI, MOV, WEBM, FLV, MPEG — up to 4 GB)
2. Bot downloads it and shows the **action keyboard**:

```
📸 Screenshots (select count):
[ 2 ] [ 3 ] [ 4 ] [ 5 ] [ 6 ] [ 7 ] [ 8 ] [ 9 ] [ 10 ]

[ ✏️ Manual Screenshots ]  [ ✂️ Trim Video ]
[ 🎬 Sample Video ]         [ 📊 Media Info ]
[ 🖼 Get Thumbnails ]
```

3. Choose an action and follow the prompts.

### ⚙️ Settings Panel (`/settings`)

| Setting | Options |
|---|---|
| 📸 Upload Mode | ✅ Tile Collage · Separate Photos |
| ⚙️ Screenshot Mode | ✅ Even spacing · Random timestamps |
| ⏱ Sample Duration | 15s · 30s · 45s · 60s |
| 💧 Watermark on Video | ON / OFF |
| 💧 Watermark on Photos | ON / OFF |

---

## 🛡️ Admin Commands

> Admin access requires your Telegram User ID in the `ADMIN_IDS` env variable.  
> Find your ID using [@userinfobot](https://t.me/userinfobot).

| Command | Description |
|---|---|
| `/stats` | Show bot usage stats (screenshots, trims, users, etc.) |
| `/users` | Show total registered user count |
| `/broadcast` | **Reply** to any message with `/broadcast` to send it to all users |

### 📡 Broadcast Usage
```
1. Write or forward a message in bot chat
2. Reply to that message with: /broadcast
3. Bot sends it to all registered users and reports success/fail count
```

---

## 🔐 Force Subscribe

Users must join **both channels** before using the bot:

| Channel | Link |
|---|---|
| @zerodev2 | https://t.me/zerodev2 |
| @mvxyoffcail | https://t.me/mvxyoffcail |

The force-sub message shows a **custom banner image** + **Join buttons**.  
After joining, users tap **✅ I Joined – Try Again** to continue.

> ⚠️ The bot must be an **admin** in both channels to verify membership.

---

## 🚀 Deployment

### Prerequisites
- Python 3.11+
- FFmpeg installed
- MongoDB instance (local or Atlas)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 1. Local / VPS

```bash
# Clone
git clone https://github.com/yourname/tg-screenshot-bot.git
cd tg-screenshot-bot

# Install deps
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env   # Fill in API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS, MONGO_URI

# Run
python bot.py
```

---

### 2. 🐳 Docker (Local / VPS)

```bash
# Build & start (includes MongoDB container)
docker-compose up -d --build

# View logs
docker-compose logs -f bot

# Stop
docker-compose down
```

---

### 3. ☁️ Koyeb

1. Push this repo to **GitHub**
2. Go to [koyeb.com](https://koyeb.com) → **Create Service** → **GitHub**
3. Select your repository
4. Set **Build method:** `Dockerfile`
5. Set **Port:** `8080`
6. Add **Environment Variables** (from `.env`):

| Key | Value |
|---|---|
| `API_ID` | Your API ID |
| `API_HASH` | Your API Hash |
| `BOT_TOKEN` | Your Bot Token |
| `ADMIN_IDS` | Your Telegram User ID |
| `MONGO_URI` | MongoDB Atlas connection string |
| `DB_NAME` | `screenshot_bot` |
| `PORT` | `8080` |

7. Click **Deploy** ✅

> **Health check URL:** `https://your-app.koyeb.app/health`

---

### 4. 🚂 Railway

1. Push repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Add a **MongoDB** plugin from Railway dashboard
4. Set environment variables (same as Koyeb table above)
5. Railway auto-detects `Dockerfile` and sets `PORT` automatically ✅

---

### 5. 🎨 Render

1. Go to [render.com](https://render.com) → **New Web Service**
2. Connect your GitHub repo
3. Set **Runtime:** `Docker`
4. Set **Port:** `8080`
5. Add environment variables
6. Click **Create Web Service** ✅

---

### 6. ✈️ Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Launch (auto-detects Dockerfile)
flyctl launch

# Set secrets
flyctl secrets set API_ID=xxx API_HASH=xxx BOT_TOKEN=xxx MONGO_URI=xxx ADMIN_IDS=xxx

# Deploy
flyctl deploy
```

---

## 🗂 Project Structure

```
tg_screenshot_bot/
├── bot.py                  ← Entry point: starts bot + web server
├── config.py               ← All configuration & env vars
├── database.py             ← Motor async MongoDB (users, settings, stats)
├── script.py               ← All bot text constants
├── web_server.py           ← aiohttp server on port 8080
├── requirements.txt
├── Dockerfile              ← Production-ready Docker image
├── docker-compose.yml      ← Local dev with MongoDB
├── .env                    ← Your secrets (never commit!)
├── .env.example            ← Template to commit to GitHub
├── .gitignore
├── README.md
├── handlers/
│   ├── __init__.py
│   ├── start.py            ← /start, /help, /about + force-sub
│   ├── video.py            ← Video receiver + main action keyboard
│   ├── screenshots.py      ← Auto (2–10) + manual screenshots
│   ├── trim.py             ← Two-step trim flow
│   ├── sample.py           ← Sample video from middle
│   ├── media_info.py       ← FFprobe media details
│   ├── thumbnails.py       ← Thumbnail extraction
│   ├── settings.py         ← /settings inline panel
│   ├── admin.py            ← /stats, /users, /broadcast
│   └── cancel.py           ← /cancel command
└── utils/
    ├── __init__.py
    ├── ffmpeg_utils.py     ← All FFmpeg operations
    └── helpers.py          ← Progress bar, force-sub, time parser
```

---

## 🌐 Web Endpoints

| Route | Description |
|---|---|
| `GET /` | Plain text status page |
| `GET /health` | JSON health check (used by Koyeb) |
| `GET /stats` | JSON bot stats from MongoDB |

---

## 📦 Supported Video Formats

`MP4` · `MKV` · `AVI` · `MOV` · `WEBM` · `FLV` · `MPEG` · `MPG` · Telegram video files · Up to **4 GB**

---

## 📄 License

MIT — free to use and modify.
