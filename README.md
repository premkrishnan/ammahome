# AmmaHome 🏠
### "കുടുംബം എപ്പോഴും അടുത്ത്" — Family Always Nearby

AmmaHome is a family presence display system. It connects your family's
Telegram group chat to an always-on iPad at your mother's home. She sees
your photos, hears your voice messages, and can send voice notes back —
all without needing to touch a phone or navigate any app.

---

## How It Works

1. Any family member sends a photo, video, voice note, or message to the family Telegram group
2. AmmaHome picks it up automatically and shows it on the iPad
3. The iPad chimes every 15 minutes until she taps to acknowledge
4. She can hold the microphone button to send a voice note back to the family
5. If the iPad goes offline, the family gets an alert on Telegram

---

## System Requirements

- **Mac** (tested on MacBook M4, macOS Tahoe) — runs the Python bot
- **Python 3.12 or newer**
- **iPad** (7th generation or newer) — the display device
- **Home Wi-Fi** — Mac and iPad must be on the same network
- **Internet connection** — for Telegram and Malayalam TTS
- **ffmpeg** — for audio format conversion

---

## Step-by-Step Setup

### Step 1 — Install system dependencies

```bash
# Install ffmpeg (needed for audio conversion)
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
5. BotFather will give you a **token** — copy it

### Step 6 — Create the family Telegram group

1. Create a new Telegram group called **"AmmaHome Family"**
2. Add all family members (including Dubai siblings)
3. Add your AmmaHome bot to the group
4. Make the bot an **Admin** (so it can read all messages)
5. Find the group chat ID:
   - Add @userinfobot to the group
   - It will reply with the group ID (a negative number like -1001234567890)
   - Remove @userinfobot after getting the ID

### Step 7 — Find your family member Telegram IDs

1. Each family member messages @userinfobot directly
2. It replies with their Telegram user ID (a number like 123456789)
3. Collect all the IDs — you will need them for .env

### Step 8 — Set up your .env file

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
FAMILY_GROUP_CHAT_ID=-1001234567890
DISPLAY_SERVER_HOST=192.168.1.10     ← your Mac's local IP
FAMILY_MEMBER_NAMES={"123456789": "Prem", "987654321": "Priya"}
```

**How to find your Mac's local IP:**
System Settings → Wi-Fi → Details → IP Address

### Step 9 — Test the configuration

```bash
python main.py --test
```

You should see a summary with all your settings. If anything is wrong,
it will tell you exactly what to fix.

### Step 10 — Set up the iPad

1. Connect the iPad to the same Wi-Fi as your Mac
2. Plug it into power (it will be always-on)
3. Open **Safari** on the iPad
4. Go to: `http://192.168.1.10:8080` (use your Mac's IP from Step 8)
5. Tap the **Share** button → **Add to Home Screen**
6. Disable auto-lock: **Settings → Display & Brightness → Auto-Lock → Never**
7. Open the saved shortcut — it will run fullscreen

### Step 11 — Start AmmaHome

```bash
python main.py
```

You will see a startup summary. The display URL will be printed — confirm
the iPad is showing the AmmaHome screen.

---

## How to Use

**Family members:**
- Just use the family Telegram group normally
- Send photos, videos, voice notes, or text messages
- AmmaHome handles everything automatically

**Amma:**
- Watch the screen — new messages appear automatically
- Tap anywhere on the screen to say "I saw it" (sends ❤️ to family)
- Hold the 🎙️ button at the bottom to send a voice note

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Display not loading on iPad | Check Mac's IP in .env matches. Are both on same Wi-Fi? |
| "Config error: TELEGRAM_BOT_TOKEN is missing" | Open .env and add your bot token |
| Family offline alert not sending | Check TELEGRAM_BOT_TOKEN and FAMILY_GROUP_CHAT_ID in .env |
| Bot not receiving messages | Make sure the bot is Admin in the family group |
| Voice note not recording on iPad | Safari → Settings → allow microphone for this site |
| TTS not speaking Malayalam | Check internet connection (gTTS needs internet) |
| Screen going dark on iPad | Settings → Display & Brightness → Auto-Lock → Never |
| "Bot was blocked by the user" | Re-add the bot to the group as Admin |
| Audio not playing on iPad | Tap the screen once — Safari requires a user gesture first |

---

## Git Commit Format

```
[service] short description of what changed

Examples:
[bot] add photo handler and push to display
[heartbeat] alert family when iPad offline for 15 mins
[display] auto-play voice messages without tap
```

---

## Project Structure

```
ammahome/
├── config.py          ← All settings (edit .env, not this)
├── main.py            ← Start here: python main.py
├── services/          ← One file per feature
├── display/           ← iPad web app (HTML/CSS/JS)
├── utils/             ← Shared helpers
└── temp/              ← Auto-cleared media files
```

---

Built with ❤️ for Amma.
