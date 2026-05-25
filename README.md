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

## System Requirements

- **Mac** (tested on MacBook M4, macOS Tahoe) — runs the Python bot and display server
- **Python 3.12 or newer**
- **iPad** (7th generation or newer recommended) — the always-on display
- **Home Wi-Fi** — Mac and iPad must be on the same network
- **Internet connection** — for Telegram, TTS audio, and family alerts
- **ffmpeg** — for audio format conversion (voice messages)

---

## Tech Stack

| Component         | Technology                                      |
|-------------------|-------------------------------------------------|
| Bot backend       | Python 3.12+                                    |
| Telegram          | python-telegram-bot                             |
| Bot↔iPad comms    | WebSocket (websockets library)                  |
| HTTP file server  | aiohttp + aiofiles                              |
| iPad display      | HTML + CSS + JS in Safari (fullscreen)          |
| TTS (Malayalam)   | gTTS (Google Text-to-Speech)                    |
| Audio conversion  | ffmpeg                                          |
| Config            | python-dotenv + config.py                       |
| Logging           | utils/logger.py                                 |

---

## Step-by-Step Setup

### Step 1 — Install system dependencies

```bash
# Install ffmpeg (needed for audio format conversion)
brew install ffmpeg
```

### Step 2 — Clone the project

```bash
git clone https://github.com/premkrishnan/AmmaHome.git
cd AmmaHome
```

### Step 3 — Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4 — Install Python dependencies

```bash
pip install python-telegram-bot websockets gTTS python-dotenv aiohttp aiofiles
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
   - Tap the group name → Edit → Administrators → Add Admin → select your bot
5. Find the group chat ID:
   - Add **@userinfobot** to the group temporarily
   - It will reply with the group ID (a negative number like `-1001234567890`)
   - Remove @userinfobot after you have the ID

### Step 7 — Find family member Telegram IDs

Each family member who should appear as a named sender:

1. They send any message to **@userinfobot** directly (private chat)
2. It replies with their numeric user ID (like `123456789`)
3. Collect all IDs — you will put them in `.env` in the next step

### Step 8 — Find your Mac's local IP address

Go to: **System Settings → Wi-Fi → Details → IP Address**

It will look like `192.168.1.10`. Write it down.

### Step 9 — Set up your .env file

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
FAMILY_GROUP_CHAT_ID=-1001234567890
DISPLAY_SERVER_HOST=192.168.1.10
DISPLAY_SERVER_PORT=8080
WS_PORT=8765
FAMILY_MEMBER_NAMES={"123456789": "Prem", "987654321": "Priya", "555000111": "Rajan"}
HEARTBEAT_TIMEOUT_MINUTES=15
MAX_MEDIA_QUEUE_SIZE=10
```

> **DISPLAY_SERVER_HOST** is your Mac's local IP from Step 8.
> **FAMILY_MEMBER_NAMES** maps Telegram user IDs to display names. Use real first names.

### Step 10 — Test the configuration

```bash
python main.py --test
```

This checks your `.env` without starting any services. If anything is wrong,
it tells you exactly which value is missing or incorrect. Fix all errors before continuing.

### Step 11 — Set up the iPad

1. Make sure the iPad is on the **same Wi-Fi network** as your Mac
2. Plug the iPad into its charger (it will be always-on)
3. Open **Safari** on the iPad
4. Go to: `http://192.168.1.10:8080`
   (replace `192.168.1.10` with your Mac's IP from Step 8)
5. The AmmaHome screen should appear with the family icon and Malayalam text
6. To add it to the home screen: tap the **Share** button (box with arrow) → **Add to Home Screen**
7. Disable auto-lock so the screen never goes dark:
   **Settings → Display & Brightness → Auto-Lock → Never**
8. Open the saved shortcut from the home screen — it runs fullscreen with no browser UI

> **First tap:** When the iPad loads for the first time, tap the screen once anywhere.
> This unlocks Safari's audio permissions so voice messages and TTS play automatically.

### Step 12 — Start AmmaHome

```bash
python main.py
```

You will see a startup summary with all settings confirmed. The Mac terminal must stay
open while AmmaHome is running. Send a test message from Telegram — it should appear
on the iPad within a few seconds.

---

## How to Use

### For family members

- **Just use the family Telegram group as normal**
- Send photos, videos, voice notes, or text messages to the group
- AmmaHome handles everything automatically — no special commands needed
- When Amma taps to acknowledge, the group will receive: **"Amma saw it ❤️"**
- Text messages are read aloud to Amma in Malayalam automatically

### For Amma

The screen shows new messages automatically. She has four interactions:

| What Amma sees / does | What it does |
|---|---|
| New message appears on screen | It was sent automatically — nothing to do |
| **Tap anywhere** on the screen | Says "I saw it" — notifies the family |
| **📷 Photos** button | Browse all photos the family has sent |
| **🎥 Videos** button | Browse all videos the family has sent |
| **Hold the blue 🎙️ button** | Records a voice note — release to send it to family |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Display not loading on iPad | Wrong IP or not on same Wi-Fi | Check Mac IP in `.env`. Are both on same Wi-Fi network? |
| "Config error: TELEGRAM_BOT_TOKEN is missing" | `.env` not set up | Open `.env` and add the token from BotFather |
| Bot not receiving any messages | Bot is not Admin in the group | Open the group → Edit → Administrators → make the bot an Admin |
| "Bot was blocked by the user" error | Bot was removed from group | Re-add the bot to the group and make it Admin |
| Family offline alert not sending | Wrong group chat ID | Get the correct ID using @userinfobot in the group |
| TTS not speaking / audio silent | Safari autoplay not yet unlocked | Tap the iPad screen once — Safari needs one tap before audio works |
| Voice note not recording | Microphone not allowed in Safari | Safari → Settings → allow microphone for this site |
| TTS not working at all | No internet on Mac | gTTS needs internet — check Mac's internet connection |
| Screen going dark on iPad | Auto-Lock is on | Settings → Display & Brightness → Auto-Lock → **Never** |
| `run_polling()` event loop error on Mac | asyncio conflict with python-telegram-bot | Use `run_polling()` inside `asyncio.run()` — see `main.py` for the correct pattern |
| `Application __slots__` error | Wrong way to store custom data on the bot | Use `context.bot_data` instead of setting attributes directly on `Application` |
| Audio plays on first message but not later | Blob URL revoked too early | The blob URL must stay alive until audio finishes playing |

---

## Project Structure

```
ammahome/
├── CLAUDE.md              ← Project context for Claude Code — read first
├── SKILL.md               ← Coding law — read before writing any code
├── README.md              ← This file
├── .env                   ← Your secrets (never commit this)
├── .env.example           ← Template — copy to .env and fill in
├── .gitignore
├── config.py              ← All settings — values come from .env
├── main.py                ← Entry point: python main.py [--test]
├── services/
│   ├── bot.py             ← Telegram bot — handles all incoming messages
│   ├── display_server.py  ← WebSocket + HTTP server — talks to iPad
│   ├── heartbeat.py       ← Monitors iPad connection, alerts family if offline
│   ├── media_handler.py   ← Downloads and prepares Telegram media files
│   └── tts.py             ← Converts text messages to Malayalam speech (gTTS)
├── display/
│   ├── index.html         ← iPad display page (four screens)
│   ├── style.css          ← Large fonts, animated gradient, warm colours
│   ├── app.js             ← WebSocket client, gallery, mic recording
│   └── family-icon.png    ← Family illustration shown on home screen
├── utils/
│   ├── logger.py          ← Shared logging — imported by all services
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

### Phase 2 — Planned
- Deploy to cloud server for 24/7 running (no Mac needed)
- Auto-start on system boot
- Physical setup on Amma's iPad (iPad A16 11")
- Add all remaining family members including Dubai

### Future Ideas
- Birthday and special occasion automatic alerts
- Daily good morning message automation
- Weather display for Amma's city
- Photo slideshow during idle time

---

Built with ❤️ for Amma.
