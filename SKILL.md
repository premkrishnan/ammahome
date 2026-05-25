# SKILL.md — AmmaHome Coding Law
# ============================================================
# This file defines the coding standards for AmmaHome.
# Every file, function, and pattern must follow these rules.
# READ THIS BEFORE WRITING ANY CODE.
# ============================================================

## File Header (mandatory on every .py and .js file)

Every Python and JavaScript file must begin with this header block:

```python
# ============================================================
# FILE: <relative path from project root>
#
# PURPOSE:
#   <One paragraph describing what this file does>
#
# INPUTS:
#   - <What this file receives / what triggers it>
#
# OUTPUTS:
#   - <What this file produces / sends>
#
# DEPENDENCIES:
#   - <External packages and internal modules this file imports>
#
# CALLED BY:
#   - <Which other files call into this one>
#
# AUTHOR: AmmaHome
# LAST UPDATED: YYYY-MM-DD
# ============================================================
```

---

## Function Docstring Format (mandatory on every function)

Every function and method must have a docstring in this exact format:

```python
def my_function(arg1: str, arg2: int) -> bool:
    """
    One-line summary of what this function does.

    Steps:
      1. First thing it does
      2. Second thing it does
      3. Return / side effect

    Args:
        arg1 (str): Description. Example: "hello"
        arg2 (int): Description. Example: 42

    Returns:
        bool: What True means. What False means.
        None: When it returns nothing, say so explicitly.

    Example:
        result = my_function("hello", 42)
        # Returns True if successful
    """
```

Rules:
- Include Steps only if the logic has more than one meaningful step
- Args must include the type and a concrete example
- Returns must describe every possible return value
- Example must show a real call (not pseudocode)

---

## Error Handling Patterns

### Pattern 1 — Log and return None (for helpers)
```python
try:
    result = do_something()
    return result
except SomeSpecificError as error:
    logger.error(f"Friendly message: {error}")
    logger.error("Fix: Tell the developer what to check")
    return None
```

### Pattern 2 — Log and continue (for background loops)
```python
try:
    await risky_operation()
except Exception as error:
    logger.error(f"Operation failed: {error}")
    # Do NOT re-raise — keep the loop alive
```

### Pattern 3 — Log and exit (for config errors only)
```python
if not required_value:
    print(f"❌  AmmaHome config error: missing {name}")
    sys.exit(1)
```

Rules:
- NEVER use bare `except:` — always catch a specific type or `Exception`
- ALWAYS log with `logger.error()` before returning or suppressing
- ALWAYS include a "Fix:" line telling the developer what to check
- NEVER let a background service crash without logging why
- NEVER crash from a heartbeat miss — alert instead

---

## Logging Conventions

```python
from utils.logger import get_logger
logger = get_logger(__name__)
```

| Level            | When to use                                      |
|------------------|--------------------------------------------------|
| `logger.debug`   | Internal state, file sizes, base64 lengths       |
| `logger.info`    | Normal operations: connected, received, sent     |
| `logger.warning` | Recoverable issues: fallback used, retry attempt |
| `logger.error`   | Failures: download failed, send failed           |

Rules:
- Include the specific value in the message, not just "error occurred"
- Errors must include a "Fix:" hint

```python
# Good
logger.error(f"Failed to download photo: {error}")
logger.error("Fix: Check internet connection and Telegram bot token")

# Bad
logger.error("Something went wrong")
```

---

## WebSocket Protocol

### Server → iPad payload
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

### iPad → Server payload
```json
{
  "type": "ack|heartbeat|voice_reply",
  "message_id": "123456789_42",
  "data": "<base64 audio for voice_reply, else omit>",
  "timestamp": "2026-05-24T14:32:05"
}
```

Rules:
- All payloads are JSON
- `message_id` format is always `{sender_id}_{telegram_message_id}`
- `data` is base64 for media, plain text for type=text
- `mime_type` is null (JSON null) for text messages

---

## iPad Display Rules

1. Font sizes: minimum 48px for all text Amma sees
2. Sender name: even larger — 64px or more
3. Background: warm, calm colour (#1a1a2e dark navy or similar)
4. Two interactions ONLY:
   - Tap anywhere → acknowledge (send ack back to server)
   - Hold mic button → record voice reply
5. Auto-play audio immediately on arrival — no tap required
6. Show content fullscreen — no menus, no navigation, no clutter
7. Auto-reconnect WebSocket if connection drops — no user action needed
8. Display must never show an error state to Amma — show a soft waiting screen instead

---

## Naming Conventions

| Thing              | Convention         | Example                        |
|--------------------|--------------------|--------------------------------|
| Python files       | snake_case.py      | `media_handler.py`             |
| Python functions   | snake_case         | `download_photo()`             |
| Python classes     | PascalCase         | `DisplayServer`                |
| Python constants   | UPPER_SNAKE_CASE   | `TELEGRAM_BOT_TOKEN`           |
| Private helpers    | _leading_underscore| `_is_from_family_group()`      |
| JS files           | snake_case.js      | `app.js`                       |
| CSS classes        | kebab-case         | `.sender-name`                 |
| WebSocket types    | snake_case strings | `"voice_reply"`, `"photo"`     |
| Temp file names    | `{type}_{uid}.ext` | `photo_a1b2c3.jpg`             |

---

## File Structure Rules

```
ammahome/
├── SKILL.md              ← This file — coding law
├── CLAUDE.md             ← Project context for Claude
├── README.md             ← Human setup guide
├── .env                  ← Secrets (never commit)
├── .env.example          ← Template (always up to date)
├── config.py             ← All settings — no hardcoded values elsewhere
├── main.py               ← Entry point only — no business logic
├── services/
│   ├── __init__.py
│   ├── bot.py            ← Telegram handlers
│   ├── display_server.py ← WebSocket + HTTP server
│   ├── tts.py            ← Malayalam TTS
│   ├── heartbeat.py      ← iPad connection monitor
│   └── media_handler.py  ← Download Telegram media
├── display/
│   ├── index.html        ← iPad display page
│   ├── style.css         ← Large fonts, warm colours
│   └── app.js            ← WebSocket client + mic
├── utils/
│   ├── __init__.py
│   ├── logger.py         ← Shared logging — imported by all
│   └── file_utils.py     ← Temp file helpers
└── temp/                 ← Auto-cleared media files
```

Rules:
- All configuration values live in `config.py` — never hardcode in service files
- All logging goes through `utils/logger.py`
- All temp file operations go through `utils/file_utils.py`
- `main.py` only wires services together — no business logic
- `services/` files never import from each other except via constructor injection

---

## Import Order (PEP 8 + project convention)

```python
# 1. Standard library
import asyncio
import json
from pathlib import Path

# 2. Third-party
from telegram import Update
from websockets.server import serve

# 3. Internal — config first, then utils, then services
import config
from utils.logger import get_logger
from utils.file_utils import make_temp_path
```

---

## Self-Healing Rules

These apply to every service without exception:

1. Every WebSocket connection must auto-reconnect with exponential backoff
2. Every background loop must catch exceptions and continue (not crash)
3. A missed heartbeat triggers a family alert — it does NOT crash the server
4. Message queue: if iPad is offline, hold up to `MAX_MEDIA_QUEUE_SIZE` messages
5. Flush the queue automatically when iPad reconnects
6. Temp files: always delete after use, even on error (use try/finally)
