# Discord AI Selfbot

A Discord selfbot powered by NVIDIA's AI API that can respond to messages and have conversations.

## Features

- 🤖 AI-powered responses using NVIDIA's API
- 💬 Responds to mentions and direct messages
- ⚡ Real-time AI conversations
- 🔧 Easy setup and configuration

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your Discord user token:**
   - Open Discord in your browser
   - Press F12 to open Developer Tools
   - Go to Network tab
   - Send a message in any channel
   - Look for a request to `https://discord.com/api/v*/messages`
   - In the request headers, find `Authorization` and copy the token

3. **Get your NVIDIA API key:**
   - Go to [NVIDIA AI Foundation](https://build.nvidia.com/)
   - Create an account and get your API key
   - Set it as an environment variable:
     ```bash
     export NVIDIA_API_KEY='your_api_key_here'
     ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Usage

- **Mention the bot** in any channel: `@YourUsername hello`
- **Send a DM** to your account
- **Commands:**
  - `hello/hi/hey` - Greeting
  - `help/commands` - Show available commands
  - Any other message - AI-powered response

## Available Models

You can change the AI model in `main.py` by modifying the `model` field:
- `meta/llama-3.1-405b-instruct` (default)
- `meta/llama-3.1-70b-instruct`
- `meta/llama-3.1-8b-instruct`
- `microsoft/phi-3-medium-128k-instruct`
- And many more available on NVIDIA's platform

## ⚠️ Important Notes

- This is a **selfbot** - it runs on your personal Discord account
- Selfbots are against Discord's Terms of Service
- Use at your own risk and for educational purposes only
- Don't use this on servers where it might cause issues

## Configuration

You can customize the AI behavior by modifying the system prompt in the `get_ai_response` function.
