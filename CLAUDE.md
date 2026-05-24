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

Phase 1 — Core pipeline: Telegram bot → display server → iPad display
