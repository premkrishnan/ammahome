# AmmaHome 🏠
### "കുടുംബം എപ്പോഴും അടുത്ത്" — Family Always Nearby

AmmaHome is a family presence display system. It connects your family's
Telegram group chat to an always-on iPad at your mother's home. She sees
your photos, hears your voice messages, and can send voice notes back —
all without needing to touch a phone or navigate any app.

When a family member sends anything to the Telegram group, it appears on
Amma's iPad within seconds. Text messages are also read aloud in Malayalam
by a text-to-speech voice. Amma can browse a gallery of all past photos
and videos, and hold a mic button to send a voice note back to everyone.

---

## How It Works

1. Any family member sends a photo, video, voice note, or text to the family Telegram group
2. AmmaHome picks it up automatically and displays it on Amma's iPad
3. Text messages are read aloud in Malayalam using Google Text-to-Speech
4. Amma taps the screen to acknowledge — the family receives an "Amma saw it ❤️" notification
5. She can browse all past photos (📷) and videos (🎥) using the gallery buttons
6. She can hold the blue 🎙️ mic button to send a voice note back to the family
7. If the iPad goes offline for too long, the family gets an automatic alert on Telegram

---

## Deployment Options

AmmaHome supports two deployment modes:

| Mode | Use case | iPad access |
|------|----------|-------------|
| **Local (Mac)** | Development and testing | Same Wi-Fi network only |
| **Production (Brahma + Cloudflare Tunnel)** | Always-on, accessible from anywhere | Public HTTPS URL |

---

## System Requirements

### Local (Mac) Mode
- **Mac** (tested on MacBook M4, macOS Tahoe)
- **Python 3.12 or newer**
- **iPad** on the same Wi-Fi network as your Mac
- **ffmpeg** — for audio format conversion
- **Internet connection** — for Telegram, TTS, and family alerts

### Production (Brahma) Mode
- **Linux server** (tested on Ubuntu, AMD Ryzen 7700) — runs 24/7
- **Python 3.12 or newer**
- **iPad** anywhere with internet access
- **ffmpeg** — for audio format conversion
- **Cloudflare account** — for the free tunnel (no credit card required)
- **Domain on Cloudflare** — for a permanent public URL

---

## Tech Stack

| Component         | Technology                                      |
|-------------------|-------------------------------------------------|
| Bot backend       | Python 3.12+                                    |
| Telegram          | python-telegram-bot                             |
| Bot↔iPad comms    | WebSocket on `/ws` path via aiohttp             |
| HTTP file server  | aiohttp + aiofiles (single port for HTTP + WS)  |
| iPad display      | HTML + CSS + JS in Safari (fullscreen)          |
| TTS (Malayalam)   | gTTS (Google Text-to-Speech)                    |
| Audio conversion  | ffmpeg                                          |
| Config            | python-dotenv + config.py                       |
| Logging           | utils/logger.py                                 |
| Tunnel (prod)     | Cloudflare Tunnel (cloudflared)                 |

---

## Local (Mac) Setup

### Step 1 — Install system dependencies

```bash
brew install ffmpeg
```

### Step 2 — Clone the project

```bash
git clone https://github.com/premkrishnan/AmmaHome.git
cd AmmaHome
```

### Step 3 — Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Create the Telegram bot

1. Open Telegram and search for **@BotFather**
2. Send: `/newbot`
3. Give it a name: `AmmaHome`
4. Give it a username: `ammahome_yourname_bot`
5. BotFather will give you a **token** — copy it (looks like `123456789:ABCdef...`)

### Step 6 — Create the family Telegram group

1. Create a new Telegram group called **"AmmaHome Family"**
2. Add all family members (including anyone overseas)
3. Add your AmmaHome bot to the group
4. **Make the bot an Admin** — without this, it cannot read messages
5. Find the group chat ID by adding **@userinfobot** to the group temporarily — it replies with the group ID (a negative number like `-1001234567890`). Remove it after.

### Step 7 — Find family member Telegram IDs

Each family member sends any message to **@userinfobot** directly (private chat). It replies with their numeric user ID (like `123456789`). Collect all IDs.

### Step 8 — Find your Mac's local IP address

**System Settings → Wi-Fi → Details → IP Address** — looks like `192.168.1.10`.

### Step 9 — Set up your .env file

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
# ── Core ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
FAMILY_GROUP_CHAT_ID=-1001234567890
DISPLAY_SERVER_HOST=192.168.1.10
PORT=8080

# ── Reminder & Heartbeat ──────────────────────────────────────
REMINDER_INTERVAL_SECONDS=900
HEARTBEAT_INTERVAL_SECONDS=300
HEARTBEAT_TIMEOUT_MINUTES=15

# ── TTS (Text-to-Speech) ──────────────────────────────────────
TTS_LANGUAGE=ml
TTS_BACKEND=google

# ── Media Queue ───────────────────────────────────────────────
MAX_MEDIA_QUEUE_SIZE=10

# ── Family Members ────────────────────────────────────────────
FAMILY_MEMBER_NAMES={"123456789": "Prem", "987654321": "Priya"}
```

> **DISPLAY_SERVER_HOST** is your Mac's local IP from Step 8.
> HTTP and WebSocket share the same port — WebSocket connects on `/ws` path automatically.

### Step 10 — Set up the iPad

1. Make sure the iPad is on the **same Wi-Fi network** as your Mac
2. Plug the iPad into its charger (always-on)
3. Open **Safari** on the iPad and go to: `http://192.168.1.10:8080`
4. Tap **Share → Add to Home Screen** to bookmark it
5. **Settings → Display & Brightness → Auto-Lock → Never**
6. Tap the screen once on first load to unlock Safari's audio permissions

### Step 11 — Start AmmaHome

```bash
python main.py
```

Send a test message from Telegram — it should appear on the iPad within seconds.

---

## Production (Brahma + Cloudflare Tunnel) Setup

This runs AmmaHome 24/7 on a home server with a permanent public HTTPS URL so
Amma's iPad can connect from anywhere — no Mac needed, no same-network requirement.

### Step 1 — SSH into Brahma

```bash
ssh prem@brahma   # or use Tailscale IP: ssh prem@100.x.x.x
```

### Step 2 — Clone and set up

```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip ffmpeg

git clone https://github.com/premkrishnan/AmmaHome.git ~/Desktop/ai/non_agentic/ammahome
cd ~/Desktop/ai/non_agentic/ammahome

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3 — Create .env on Brahma

```bash
cat > .env << 'EOF'
# ── Core ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=your_bot_token_here
FAMILY_GROUP_CHAT_ID=your_group_chat_id_here
DISPLAY_SERVER_HOST=0.0.0.0
PORT=8080

# ── Reminder & Heartbeat ──────────────────────────────────────
REMINDER_INTERVAL_SECONDS=900
HEARTBEAT_INTERVAL_SECONDS=300
HEARTBEAT_TIMEOUT_MINUTES=15

# ── TTS (Text-to-Speech) ──────────────────────────────────────
TTS_LANGUAGE=ml
TTS_BACKEND=google

# ── Media Queue ───────────────────────────────────────────────
MAX_MEDIA_QUEUE_SIZE=10

# ── Family Members ────────────────────────────────────────────
FAMILY_MEMBER_NAMES={"000000000": "Prem"}
EOF
```

> **DISPLAY_SERVER_HOST** must be `0.0.0.0` on Brahma (listen on all interfaces).
> **PORT** must be set explicitly — unlike Railway, Brahma does not inject it automatically.

### Step 4 — Install Cloudflare Tunnel

```bash
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb && rm cloudflared.deb
cloudflared --version
```

### Step 5 — Create named tunnel

```bash
cloudflared tunnel login        # opens a browser URL — authorize brahmaserver.dev
cloudflared tunnel create ammahome
cloudflared tunnel list         # note the tunnel UUID
```

### Step 6 — Create tunnel config

```bash
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: YOUR-TUNNEL-UUID
credentials-file: /home/prem/.cloudflared/YOUR-TUNNEL-UUID.json

ingress:
  - hostname: ammahome.brahmaserver.dev
    service: http://localhost:8080
  - service: http_status:404
EOF

cloudflared tunnel route dns ammahome ammahome.brahmaserver.dev
```

### Step 7 — Create systemd services

**AmmaHome service:**

```bash
sudo tee /etc/systemd/system/ammahome.service << 'EOF'
[Unit]
Description=AmmaHome Display Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=prem
WorkingDirectory=/home/prem/Desktop/ai/non_agentic/ammahome
EnvironmentFile=/home/prem/Desktop/ai/non_agentic/ammahome/.env
ExecStart=/home/prem/Desktop/ai/non_agentic/ammahome/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Cloudflare Tunnel service:**

```bash
sudo tee /etc/systemd/system/cloudflared.service << 'EOF'
[Unit]
Description=Cloudflare Tunnel - brahmaserver.dev
After=network.target

[Service]
Type=simple
User=prem
ExecStart=/usr/bin/cloudflared tunnel --config /home/prem/.cloudflared/config.yml run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

> Check `which cloudflared` — update `ExecStart` if it returns `/usr/local/bin/cloudflared`.

### Step 8 — Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable ammahome cloudflared
sudo systemctl start ammahome cloudflared
sudo systemctl status ammahome cloudflared --no-pager
```

### Step 9 — Set up the iPad

Open `https://ammahome.brahmaserver.dev` in Safari on the iPad.
Tap **Share → Add to Home Screen**. Set Auto-Lock to Never. Tap once to unlock audio.

---

## Production URL

```
https://ammahome.brahmaserver.dev
```

This URL is permanent. Brahma reboots, cloudflared restarts — the URL never changes.

---

## Adding Future Projects to brahmaserver.dev

To expose a new project (e.g. LingoBridge on port 8081), add a new ingress rule
to `~/.cloudflared/config.yml` and create a DNS record:

```yaml
ingress:
  - hostname: ammahome.brahmaserver.dev
    service: http://localhost:8080
  - hostname: lingobridge.brahmaserver.dev
    service: http://localhost:8081
  - service: http_status:404
```

```bash
cloudflared tunnel route dns ammahome lingobridge.brahmaserver.dev
sudo systemctl restart cloudflared
```

---

## Ongoing Maintenance

### Deploy code updates

```bash
cd ~/Desktop/ai/non_agentic/ammahome
git pull
source venv/bin/activate
pip install -r requirements.txt   # only if dependencies changed
sudo systemctl restart ammahome
journalctl -u ammahome -f         # watch startup logs
```

### Useful commands

```bash
# View live logs
journalctl -u ammahome -f
journalctl -u cloudflared -f

# Check status of both services
sudo systemctl status ammahome cloudflared --no-pager

# Check what's listening on port 8080
ss -tlnp | grep 8080

# Restart both after any config change
sudo systemctl restart ammahome cloudflared
```

---

## How to Use

### For family members

- **Just use the family Telegram group as normal**
- Send photos, videos, voice notes, or text messages to the group
- AmmaHome handles everything automatically — no special commands needed
- When Amma taps to acknowledge, the group will receive: **"Amma saw it ❤️"**
- Text messages are read aloud to Amma in Malayalam automatically

### For Amma

| What Amma sees / does | What it does |
|---|---|
| New message appears on screen | Sent automatically — nothing to do |
| **Tap anywhere** on the screen | Says "I saw it" — notifies the family |
| **📷 Photos** button | Browse all photos the family has sent |
| **🎥 Videos** button | Browse all videos the family has sent |
| **Hold the blue 🎙️ button** | Records a voice note — release to send to family |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Display not loading on iPad (local) | Wrong IP or different Wi-Fi | Check Mac IP in `.env`. Both must be on same Wi-Fi. |
| Display not loading on iPad (prod) | Service not running | `sudo systemctl status ammahome` on Brahma |
| "Config error: TELEGRAM_BOT_TOKEN is missing" | `.env` not set up | Open `.env` and add the token from BotFather |
| Bot not receiving messages | Bot is not Admin in group | Group → Edit → Administrators → make bot Admin |
| TTS not speaking | Safari autoplay not unlocked | Tap the iPad screen once on first load |
| Voice note not recording | Microphone not allowed | Safari → Settings → allow microphone for this site |
| Screen going dark | Auto-Lock is on | Settings → Display & Brightness → Auto-Lock → Never |
| `run_polling()` event loop error | asyncio conflict | Use `run_polling()` inside `asyncio.run()` — see `main.py` |
| `Application __slots__` error | Wrong bot data storage | Use `context.bot_data` instead of attributes on `Application` |
| Cloudflared URL changed | Quick tunnel restarted | Named tunnel on brahmaserver.dev has a permanent URL — use that |

---

## Project Structure

```
ammahome/
├── CLAUDE.md              ← Project context for Claude Code — read first
├── SKILL.md               ← Coding standards — read before writing any code
├── README.md              ← This file
├── .env                   ← Your secrets (never commit this)
├── .env.example           ← Template — copy to .env and fill in
├── .gitignore
├── config.py              ← All settings — values come from .env
├── main.py                ← Entry point: python main.py
├── services/
│   ├── bot.py             ← Telegram bot — handles all incoming messages
│   ├── display_server.py  ← aiohttp server — HTTP + WebSocket on single port
│   ├── heartbeat.py       ← Monitors iPad connection, alerts family if offline
│   ├── media_handler.py   ← Downloads and prepares Telegram media files
│   └── tts.py             ← Converts text messages to Malayalam speech (gTTS)
├── display/
│   ├── index.html         ← iPad display page
│   ├── style.css          ← Large fonts, animated gradient, warm colours
│   ├── app.js             ← WebSocket client on /ws, gallery, mic recording
│   └── family-icon.png    ← Family illustration shown on home screen
├── utils/
│   ├── logger.py          ← Shared logging
│   └── file_utils.py      ← Temp file creation and cleanup helpers
└── temp/                  ← Auto-cleared media files (photos, audio, video)
```

---

## Git Commit Format

```
[service] short description of what changed

Examples:
[bot] add photo handler and push to display
[heartbeat] alert family when iPad offline for 15 mins
[display] auto-play voice messages without tap
[tts] fall back to English if Malayalam TTS fails
```

---

## Roadmap

### Phase 1 — Complete ✅
Core pipeline: Telegram → bot → WebSocket → iPad display

- Telegram bot receives photos, videos, voice notes, and text messages
- Content pushed to iPad over WebSocket and displayed fullscreen
- Malayalam TTS reads text messages aloud
- Photo and video gallery with unread badges
- Amma sends voice replies back to family
- Heartbeat monitoring — family alerted if iPad goes offline
- Safari autoplay unlock, self-healing WebSocket reconnect
- WebSocket merged into aiohttp — single port for HTTP and WS

### Phase 2 — Complete ✅
Production deployment: always-on, accessible from anywhere

- Deployed to Brahma (AMD Ryzen 7700, Ubuntu, Singapore)
- Cloudflare Tunnel with permanent URL: `ammahome.brahmaserver.dev`
- systemd services — auto-start on boot, auto-restart on crash
- `brahmaserver.dev` domain ready for future projects as subdomains

### Future Ideas
- Birthday and special occasion automatic alerts
- Daily good morning message automation
- Weather display for Amma's city
- Photo slideshow during idle time
- LingoBridge at `lingobridge.brahmaserver.dev`

---

Built with ❤️ for Amma.
