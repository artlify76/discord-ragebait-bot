# Discord AI Selfbot - Usage Guide

A Discord selfbot powered by NVIDIA's AI API with multiple response modes and context-aware messaging.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Your NVIDIA NIM API Key


1. Visit [NVIDIA Build](https://build.nvidia.com/)
2. Sign up or log in to your account
3. Generate an API key from the dashboard
4. Copy your API key

### 3. Get Your Discord User Token
[![Discord User Token Tutorial](https://img.shields.io/badge/YouTube-Watch%20Tutorial-red?logo=youtube)]
https://www.youtube.com/watch?v=5SRwnLYdpJs

[Add your YouTube tutorial link here]

1. Open Discord in your browser
2. Press `F12` to open Developer Tools
3. Go to the **Network** tab
4. Send a message in any channel
5. Look for a request to `https://discord.com/api/v*/messages`
6. In request headers, find the `Authorization` header
7. Copy the token value (it starts with your user ID)

### 4. Configure the Bot
Create a `config.json` file in the root directory:

```json
{
  "discord_token": "YOUR_DISCORD_TOKEN_HERE",
  "nvidia_api_key": "YOUR_NVIDIA_API_KEY_HERE"
}
```

### 5. Start the Bot
```bash
cd /Users/damirshigayev/discord-ai-self
python3 main.py
```

## Commands

### Core Modes

| Command | Description |
|---------|-------------|
| `$lock` | Lock channel for normal AI responses |
| `$unlock` | Unlock channel |
| `$gaglock` | Enable annoying, condescending AI mode |
| `$gagunlock` | Disable gag mode |
| `$gagtestlock` | Gag mode + responds to your messages |
| `$gagtestunlock` | Disable gag test mode |
| `$silentgaglock` / `$sgaglock` | Stealth gag mode (no visible traces) |
| `$silentgagunlock` / `$sgagunlock` | Disable silent gag mode |
| `$swglock` | Super stealth mode (short replies, no typing indicator) |
| `$swgunlock` | Disable super stealth mode |
| `$v2lock` | V2 enhanced mode (1-5 word responses + memory + image analysis) |
| `$v2unlock` | Disable V2 mode |
| `$spawnlock` | Spawn cult roasting mode |
| `$spawnunlock` | Disable spawn mode |

### Chat & Utility

| Command | Description |
|---------|-------------|
| `$ai <prompt>` | Chat with AI directly |
| `$hello` | Greeting |
| `$help` | Show all commands |

### Message Scraping

| Command | Description |
|---------|-------------|
| `$scrape` | Silently scrape all messages from current channel |
| `$scrape <number>` | Scrape specific number of messages |
| `$scrapestats` | Show scraping database statistics (console only) |

## Features

### 🧠 Context-Aware Responses
- **Gaglock modes** store up to 100 messages of context per channel
- Bot remembers usernames and conversation history
- Responses are tailored to ongoing conversations

### 🎭 Multiple Response Personalities
- **Normal Mode**: Helpful AI assistant
- **Gag Mode**: Annoying, condescending know-it-all
- **Super Stealth**: Short, dismissive replies
- **V2 Mode**: Ultra-stealthy 1-5 word responses
- **Spawn Mode**: Cult mockery responses

### 🖼️ Image Processing
- V2 mode analyzes images using NVIDIA's vision API
- Contextualizes image content in responses

### 📊 Message Database
- Persistent SQLite databases for each mode
- Automatic message retention (100-200 messages per channel)
- User identification and history tracking

### 🔇 Stealth Modes
- Silent gag lock: Responds without visible traces
- Super stealth: No typing indicator, minimal responses
- V2 mode: Maximum stealth with context awareness

## Notes

⚠️ **Disclaimer**: Selfbots operate on user accounts and violate Discord's Terms of Service. Use at your own risk and for educational purposes only.

## Support

For issues or questions, check the console output for debug messages (prefixed with `DEBUG:` or `[SCRAPER]`).
