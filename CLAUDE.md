# CLAUDE.md — AmmaHome Project Context
# ============================================================
# This file gives Claude Code the context it needs to work
# on the AmmaHome project correctly every time.
#
# READ THIS BEFORE TOUCHING ANY CODE.
# ============================================================

## What is AmmaHome?

AmmaHome is a family presence display system built for an elderly,
non-tech-savvy mother (Amma) living alone. It makes her feel like
family is always nearby, even when they are far away.

A Telegram bot monitors the family group chat. When any family member
sends a photo, video, voice message, or text, it is automatically
displayed or played on an always-on iPad at Amma's home.

**Tagline:** "കുടുംബം എപ്പോഴും അടുത്ത്" (Family Always Nearby)

## The End User

Amma is elderly and NOT tech-savvy. She must never need to:
- Restart anything
- Troubleshoot a problem
- Navigate menus
- Type anything

The entire system must be self-healing and automatic.
She has exactly TWO interactions:
1. Tap anywhere → acknowledge she saw the message
2. Hold the mic button → send a voice note to the family

## Hardware

- **Mac (MacBook M4, macOS Tahoe):** runs the Python bot and servers
- **iPad:** displays content in Safari fullscreen, always plugged in
- **Same Wi-Fi network:** Mac and iPad must be on the same network

## Tech Stack

| Component         | Technology                    |
|-------------------|-------------------------------|
| Bot backend       | Python 3.12+                  |
| Telegram          | python-telegram-bot           |
| Bot↔iPad comms    | WebSocket (websockets library)|
| iPad display      | HTML + CSS + JS in Safari     |
| TTS (Malayalam)   | gTTS (google text-to-speech)  |
| Audio conversion  | ffmpeg                        |
| Config            | .env + config.py              |
| Logging           | utils/logger.py               |

## Coding Standards

**ALWAYS read SKILL.md before writing any code.**
The SKILL.md file is the law for this project. It covers:
- File structure rules
- File header format (mandatory on every .py and .js file)
- Function docstring format (mandatory on every function)
- Error handling patterns
- Logging conventions
- WebSocket protocol (JSON payload format)
- iPad display rules (font sizes, colours, two interactions only)
- Naming conventions

## Project Structure

```
ammahome/
├── SKILL.md              ← Coding law — read first
├── CLAUDE.md             ← This file
├── README.md             ← Human setup guide
├── .env                  ← Secrets (never commit)
├── .env.example          ← Template for .env
├── config.py             ← All settings
├── main.py               ← Entry point
├── services/
│   ├── bot.py            ← Telegram bot
│   ├── display_server.py ← WebSocket + HTTP server
│   ├── tts.py            ← Malayalam TTS
│   ├── heartbeat.py      ← iPad connection monitor
│   └── media_handler.py  ← Download/prepare media
├── display/
│   ├── index.html        ← iPad display page
│   ├── style.css         ← Large fonts, warm colours
│   └── app.js            ← WebSocket client + mic
├── utils/
│   ├── logger.py         ← Shared logging
│   └── file_utils.py     ← Temp file helpers
└── temp/                 ← Auto-cleared media files
```

## WebSocket Protocol

Server → iPad:
```json
{
  "type": "photo|video|voice|text|chime|clear",
  "sender": "Prem",
  "data": "<base64 media or plain text>",
  "mime_type": "image/jpeg|video/mp4|audio/ogg|null",
  "message_id": "123456789_42",
  "timestamp": "2026-05-24T14:32:01"
}
```

iPad → Server:
```json
{
  "type": "ack|heartbeat|voice_reply",
  "message_id": "123456789_42",
  "data": "<base64 audio for voice_reply>",
  "timestamp": "2026-05-24T14:32:05"
}
```

## Key Rules to Never Break

1. Amma never troubleshoots — the system self-heals
2. Every connection auto-reconnects on failure
3. Missed heartbeat → alert family, do NOT crash
4. All config values live in config.py, never hardcoded
5. temp/ files deleted after sending
6. .env is never committed to git
7. Every .py file has the standard header
8. Every function has a docstring with Steps/Args/Returns/Example

## Running the Project

```bash
# Test config without starting services
python main.py --test

# Start AmmaHome
python main.py
```

## Current Phase

**Phase 1 — Complete ✅**
Core pipeline: Telegram bot → display server → iPad display.
All message types working (photo, video, voice, text + TTS).
Gallery, mic recording, heartbeat monitoring all implemented.

**Phase 2 — In Progress**
Railway cloud deployment. Single combined HTTP + WebSocket server.

---

## Production Deployment

- Server: Brahma (AMD Ryzen 7700, Ubuntu, Singapore)
- URL: https://ammahome.brahmaserver.dev
- AmmaHome: systemd service `ammahome`
- Tunnel: Cloudflare named tunnel `ammahome` (7173370d-4e60-424f-b331-0861303f148f)
- Domain: brahmaserver.dev (Cloudflare Registrar)
- Future projects: *.brahmaserver.dev subdomains

---

## Known Fixes (Phase 1)

These bugs were hit and fixed during Phase 1. Do not reintroduce them.

### Fix 1 — python-telegram-bot `run_polling()` event loop conflict
**Symptom:** `RuntimeError: This event loop is already running` on macOS.
**Cause:** `run_polling()` tries to create its own event loop but one already exists.
**Fix:** Wrap the entire startup in `asyncio.run()` and use `application.run_polling()` inside an async context. See `main.py` for the correct pattern.

### Fix 2 — `Application __slots__` error
**Symptom:** `AttributeError: 'Application' object has no attribute 'X'` when trying to attach custom data to the bot application object.
**Cause:** `python-telegram-bot`'s `Application` class uses `__slots__`, so you cannot set arbitrary attributes on it.
**Fix:** Use `context.bot_data` (a plain dict available inside all handler callbacks) to store shared state like the WebSocket broadcast function.

### Fix 3 — Safari autoplay blocks TTS and voice audio
**Symptom:** Audio (TTS, voice messages) does not play on first message after page load. No error visible.
**Cause:** Safari on iOS refuses `audio.play()` until the user has physically tapped the page at least once.
**Fix:** On the first `touchstart` or `click` event on `document`, create and resume an `AudioContext`. This unlocks audio for all subsequent `play()` calls. See `display/app.js` — `unlockAudio()` function.
