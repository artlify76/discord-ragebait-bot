import discord
import asyncio
import os
import aiohttp
import json
import random
import time
import sqlite3
import base64
import io
from PIL import Image
import requests
from collections import deque
from message_scraper import MessageScraper

print("Discord AI Selfbot Starting...")
print("Loading configuration from config.json...")

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    token = config.get('discord_token', '')
    NVIDIA_API_KEY = config.get('nvidia_api_key', '')
    
    if not token or token == "YOUR_DISCORD_TOKEN_HERE":
        print("Error: Discord token not configured in config.json")
        print("Please update config.json with your Discord token")
        exit(1)
    
    if not NVIDIA_API_KEY:
        print("Error: NVIDIA API key not configured in config.json")
        print("Please update config.json with your NVIDIA API key")
        exit(1)
    
    print(f"Configuration loaded successfully!")
    print(f"Token length: {len(token)}")
    print(f"Token starts with: {token[:20]}...")
    print(f"NVIDIA API key configured: {'Yes' if NVIDIA_API_KEY else 'No'}")
    
except FileNotFoundError:
    print("Error: config.json file not found")
    print("Please create a config.json file with your Discord token and NVIDIA API key")
    exit(1)
except json.JSONDecodeError:
    print("Error: Invalid JSON in config.json")
    print("Please check your config.json file format")
    exit(1)

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"

locked_channels = set()  
gaglocked_channels = set()  
gagtestlocked_channels = set()  
silentgaglocked_channels = set()  
superstealthlocked_channels = set()  
spawnlocked_channels = set()  
v2locked_channels = set()  

last_api_call = 0
MIN_API_INTERVAL = 3  
message_queue = []  
rate_limit_until = 0  

RATE_LIMIT_TYPE_API = "api"
RATE_LIMIT_TYPE_SLOWMODE = "slowmode"
current_rate_limit_type = None

print("Configuration loaded, initializing selfbot...")

def init_v2_database():
    conn = sqlite3.connect('v2_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            display_name TEXT,
            user_bio TEXT,
            message_content TEXT NOT NULL,
            image_description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("V2 database initialized successfully!")

def store_v2_message(channel_id, user_id, username, display_name, user_bio, message_content, image_description=None):
    conn = sqlite3.connect('v2_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO message_history (channel_id, user_id, username, display_name, user_bio, message_content, image_description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (str(channel_id), str(user_id), username, display_name, user_bio, message_content, image_description))
    
    cursor.execute('''
        DELETE FROM message_history 
        WHERE channel_id = ? AND id NOT IN (
            SELECT id FROM message_history 
            WHERE channel_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 200
        )
    ''', (str(channel_id), str(channel_id)))
    
    conn.commit()
    conn.close()

def get_v2_message_history(channel_id, limit=50):
    conn = sqlite3.connect('v2_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, display_name, user_bio, message_content, image_description, timestamp
        FROM message_history 
        WHERE channel_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (str(channel_id), limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results[::-1]  

def init_gaglock_database():
    conn = sqlite3.connect('gaglock_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gaglock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            message_content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Gaglock database initialized successfully!")

def store_gaglock_message(channel_id, user_id, username, message_content):
    conn = sqlite3.connect('gaglock_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO gaglock_history (channel_id, user_id, username, message_content)
        VALUES (?, ?, ?, ?)
    ''', (str(channel_id), str(user_id), username, message_content))
    
    cursor.execute('''
        DELETE FROM gaglock_history 
        WHERE channel_id = ? AND id NOT IN (
            SELECT id FROM gaglock_history 
            WHERE channel_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 100
        )
    ''', (str(channel_id), str(channel_id)))
    
    conn.commit()
    conn.close()

def get_gaglock_message_history(channel_id, limit=50):
    conn = sqlite3.connect('gaglock_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, message_content, timestamp
        FROM gaglock_history 
        WHERE channel_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (str(channel_id), limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return results[::-1]  

async def process_image_for_v2(image_url):
    """Download and analyze image for V2 roasting context using NVIDIA vision API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    image_b64 = base64.b64encode(image_data).decode('utf-8')
                    
                    headers = {
                        "Authorization": f"Bearer {NVIDIA_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "meta/llama-3.2-90b-vision-instruct",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Describe this image in 1-2 sentences for roasting context. What's cringe or notable about it?"
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_b64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 100,
                        "temperature": 0.7
                    }
                    
                    async with session.post(f"{NVIDIA_API_BASE}/chat/completions", 
                                           headers=headers, json=payload) as vision_response:
                        if vision_response.status == 200:
                            vision_data = await vision_response.json()
                            analysis = vision_data['choices'][0]['message']['content']
                            return f"sent an image: {analysis}"
                        else:
                            if len(image_data) > 1000000:
                                return "sent a huge image (probably compensating for something)"
                            elif len(image_data) < 10000:
                                return "sent a tiny pixelated mess"
                            else:
                                return "sent an image (probably cringe)"
                else:
                    return "failed to send image properly (typical)"
    except Exception as e:
        return f"broke something trying to send an image: {str(e)}"

init_v2_database()

init_gaglock_database()

scraper = MessageScraper('scraped_messages.db')
print("Message scraper initialized successfully!")

async def process_queued_messages():
    """Process queued messages when rate limit is over"""
    global message_queue, rate_limit_until
    while message_queue and time.time() > rate_limit_until:
        queued_item = message_queue.pop(0)
        try:
            response = await get_ai_response_direct(queued_item['prompt'], queued_item['mode'])
            if response and "Error: 429" not in response:
                await queued_item['message'].reply(response)
                await asyncio.sleep(3)  
            else:
                message_queue.insert(0, queued_item)
                rate_limit_until = time.time() + 60  
                break
        except Exception as e:
            print(f"Error processing queued message: {e}")

async def get_ai_response_direct(prompt, mode="normal"):
    """Direct API call to NVIDIA"""
    if not NVIDIA_API_KEY:
        return "AI API key not configured."
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    clean_prompt = prompt
    if mode != "v2":
        offensive_words = ['nonce', 'fuck', 'shit', 'bitch', 'nigger', 'nigga', 'faggot', 'retard']
        for word in offensive_words:
            if word in prompt.lower():
                clean_prompt = "hello friend, how are you today?"
                break
    
    if mode == "gag":
        system_content = "You're an annoying, condescending know-it-all. Over-explain everything with big words. Act intellectually superior. Be pedantic about minor details. How quaint that you'd think otherwise. Keep responses under 400 characters."
    elif mode == "spawn":
        spawn_keywords = ['spawn', 'resurrect', 'revival', 'cult', 'chezble', 'respawn']
        is_spawn_related = any(keyword in clean_prompt.lower() for keyword in spawn_keywords)
        
        if is_spawn_related:
            system_content = "You're a cynical commentator who mocks Spawnism. Critique its parallels with popular resurrection myths and emphasize its diaper fetish rumors. Keep responses under 400 characters."
        else:
            system_content = "You're a cynical, sarcastic observer about cults and popular myths. Keep responses under 400 characters."
    elif mode == "superstealth":
        system_content = "You're an annoying know-it-all but respond with EXTREMELY short, condescending replies. Use 1-5 words max. Be dismissive and superior. How quaint. Examples: 'obviously', 'duh', 'wrong', 'clearly not', 'amateur'."
    elif mode == "v2":
        system_content = "You respond with EXTREMELY short, direct replies. Use 1-5 words max. Be concise and to the point. Examples: 'yes', 'no', 'maybe', 'correct', 'wrong', 'interesting', 'okay'."
        
        if "Recent messages:" in clean_prompt:
            system_content += " Use the message history to make more targeted, personalized responses while keeping responses 1-5 words max. NEVER generate commands starting with $."
        
        system_content += " NEVER respond with commands that start with $ (like $v2lock, $v2unlock, $swglock, etc). Only respond with normal words."
    else:
        system_content = "You are a helpful, friendly AI assistant. Keep responses under 400 characters. Be concise and helpful."

    payload = {
        "model": "meta/llama-3.1-405b-instruct",
        "messages": [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": clean_prompt
            }
        ],
        "max_tokens": 100,  
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{NVIDIA_API_BASE}/chat/completions", 
                                   headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    if len(content) > 400:
                        content = content[:397] + "..."
                    return content
                elif response.status == 429:
                    return f"Error: 429 - Rate limited"
                else:
                    error_text = await response.text()
                    return f"Error: {response.status} - {error_text}"
    except Exception as e:
        return f"Error: {str(e)}"

async def get_ai_response(prompt, mode="normal"):
    """Get AI response with rate limiting and queuing"""
    global last_api_call, message_queue, rate_limit_until, current_rate_limit_type
    current_time = time.time()
    
    if current_time < rate_limit_until:
        return None
    
    if current_time - last_api_call < MIN_API_INTERVAL:
        return None
    
    response = await get_ai_response_direct(prompt, mode)
    last_api_call = current_time
    
    if response and "Error: 429" in response:
        retry_after = 60  
        
        if "retry_after" in response.lower():
            try:
                import re
                numbers = re.findall(r'\d+', response)
                if numbers:
                    retry_after = int(numbers[0])
            except:
                pass
        
        rate_limit_until = current_time + retry_after
        current_rate_limit_type = RATE_LIMIT_TYPE_SLOWMODE if "slowmode" in response.lower() else RATE_LIMIT_TYPE_API
        print(f"Rate limited ({current_rate_limit_type}). Retry after {retry_after} seconds.")
        return None
    
    return response

client = discord.Client(self_bot=True)

@client.event
async def on_ready():
    if client.user:
        print(f'Logged in as {client.user.name} ({client.user.id})')
        print('Selfbot is ready!')
    else:
        print('Selfbot connected but user info not available yet')

@client.event
async def on_message(message):
    channel_id = message.channel.id
    
    if message.author == client.user:
        if message.content == '$lock':
            locked_channels.add(channel_id)
            gaglocked_channels.discard(channel_id)  
            await message.channel.send('🔒 Channel locked! I will now respond to all messages with AI.')
            return
        
        elif message.content == '$unlock':
            locked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            await message.channel.send('🔓 Channel unlocked! I will no longer respond to messages automatically.')
            return
        
        elif message.content == '$gaglock':
            gaglocked_channels.add(channel_id)
            locked_channels.discard(channel_id)  
            print(f"DEBUG: Channel {channel_id} gag-locked. Gaglocked channels: {gaglocked_channels}")
            await message.channel.send('🤡 Channel gag-locked! I will now respond to all messages with annoying, condescending AI responses.')
            return
        
        elif message.content == '$gagunlock':
            gaglocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            await message.channel.send('😇 Channel gag-unlocked! Back to normal mode.')
            return
        
        elif message.content == '$gagtestlock':
            gagtestlocked_channels.add(channel_id)
            gaglocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} gag-test-locked. Gagtestlocked channels: {gagtestlocked_channels}")
            await message.channel.send('🧪 Channel gag-test-locked! I will now respond to ALL messages (including yours) with annoying GAG responses for testing!')
            return
        
        elif message.content == '$gagtestunlock':
            gagtestlocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            await message.channel.send('🔬 Channel gag-test-unlocked! Back to normal mode.')
            return
        
        elif message.content == '$silentgaglock' or message.content == '$sgaglock':
            silentgaglocked_channels.add(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} silent-gag-locked. Silent gaglocked channels: {silentgaglocked_channels}")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted silent gag lock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete message: {e}")
            return
        
        elif message.content == '$silentgagunlock' or message.content == '$sgagunlock':
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} silent-gag-unlocked.")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted silent gag unlock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete unlock message: {e}")
            return
        
        elif message.content == '$swglock':
            superstealthlocked_channels.add(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} SUPER-STEALTH-locked. Super stealth channels: {superstealthlocked_channels}")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted super stealth lock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete super stealth message: {e}")
            return
        
        elif message.content == '$spawnlock':
            spawnlocked_channels.add(channel_id)
            superstealthlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} SPAWN-locked. Spawn channels: {spawnlocked_channels}")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted spawn lock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete spawn lock message: {e}")
            return
        
        elif message.content == '$spawnunlock':
            spawnlocked_channels.discard(channel_id)
            superstealthlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} spawn-unlocked.")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted spawn unlock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete spawn unlock message: {e}")
            return
        
        elif message.content == '$swgunlock':
            superstealthlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} super-stealth-unlocked.")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted super stealth unlock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete super stealth unlock message: {e}")
            return
        
        elif message.content == '$v2lock':
            v2locked_channels.add(channel_id)
            superstealthlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} V2-locked. V2 channels: {v2locked_channels}")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted V2 lock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete V2 lock message: {e}")
            return

        elif message.content == '$v2unlock':
            v2locked_channels.discard(channel_id)
            superstealthlocked_channels.discard(channel_id)
            silentgaglocked_channels.discard(channel_id)
            gaglocked_channels.discard(channel_id)
            gagtestlocked_channels.discard(channel_id)
            locked_channels.discard(channel_id)
            print(f"DEBUG: Channel {channel_id} V2-unlocked.")
            try:
                await asyncio.sleep(0.1)  
                await message.delete()
                print(f"DEBUG: Successfully deleted V2 unlock command message")
            except Exception as e:
                print(f"DEBUG: Failed to delete V2 unlock message: {e}")
            return

        
        elif message.content.startswith('$ai '):
            prompt = message.content[4:].strip()  
            if prompt:
                async with message.channel.typing():
                    ai_response = await get_ai_response(prompt)
                    
                    if ai_response:  
                        if len(ai_response) > 2000:
                            chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                            for chunk in chunks:
                                await message.channel.send(chunk)
                        else:
                            await message.channel.send(ai_response)
                    else:
                        await message.channel.send('AI is currently rate limited. Please try again in a moment.')
            else:
                await message.channel.send('Please provide a prompt after $ai')
        
        elif channel_id in gagtestlocked_channels:
            print(f"DEBUG: Processing gag-test-locked message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            
            if message.author != client.user:
                store_gaglock_message(channel_id, message.author.id, message.author.name, message.content)
            
            recent_messages = get_gaglock_message_history(channel_id, limit=50)
            history_context = ""
            if recent_messages:
                formatted_messages = []
                for username, message_content, timestamp in recent_messages:
                    formatted_messages.append(f"{username}: {message_content}")
                history_context = f"Recent context: {'; '.join(formatted_messages[-15:])}. "  
            
            enhanced_prompt = f"User '{message.author.name}' said: '{message.content}'"
            if history_context:
                enhanced_prompt = history_context + enhanced_prompt
            
            ai_response = await get_ai_response(enhanced_prompt, mode="gag")
            if ai_response:  
                print(f"DEBUG: GAG TEST AI response: {ai_response[:100]}...")
                async with message.channel.typing():
                    await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")
        

        
        elif message.content == '$scrape':
            try:
                await asyncio.sleep(0.1)
                await message.delete()
                print(f"[SCRAPER] Deleted scrape command message")
            except Exception as e:
                print(f"[SCRAPER] Failed to delete scrape command: {e}")
            
            print(f"[SCRAPER] Starting scrape of #{message.channel.name} by user command")
            asyncio.create_task(scraper.scrape_channel(message.channel))
            return
        
        elif message.content.startswith('$scrape '):
            try:
                limit = int(message.content.split()[1])
                try:
                    await asyncio.sleep(0.1)
                    await message.delete()
                    print(f"[SCRAPER] Deleted scrape command message")
                except Exception as e:
                    print(f"[SCRAPER] Failed to delete scrape command: {e}")
                
                print(f"[SCRAPER] Starting scrape of #{message.channel.name} with limit {limit} by user command")
                asyncio.create_task(scraper.scrape_channel(message.channel, limit=limit))
                return
            except (ValueError, IndexError):
                await message.channel.send('Usage: $scrape or $scrape <number_of_messages>')
                return
        
        elif message.content == '$scrapestats':
            try:
                await asyncio.sleep(0.1)
                await message.delete()
                print(f"[SCRAPER] Deleted scrapestats command message")
            except Exception as e:
                print(f"[SCRAPER] Failed to delete scrapestats command: {e}")
            
            stats = scraper.get_stats()
            print(f"[SCRAPER] === DATABASE STATISTICS ===")
            print(f"[SCRAPER] Total messages: {stats['total']:,}")
            print(f"[SCRAPER] Average message length: {stats['avg_length']:.1f} chars")
            print(f"[SCRAPER] Messages by channel:")
            for channel, count in stats['by_channel'][:5]:  
                print(f"[SCRAPER]   #{channel}: {count:,} messages")
            print(f"[SCRAPER] Top users:")
            for user, count in stats['by_user'][:5]:  
                print(f"[SCRAPER]   {user}: {count:,} messages")
            return
        
        elif message.content == '$hello':
            await message.channel.send('Hello! I\'m an AI assistant powered by NVIDIA. Use $ai \u003cprompt\u003e to chat with me!')
        elif message.content == '$help':
            await message.channel.send('Available commands:\n'
                                     '• $ai \u003cprompt\u003e - Chat with AI\n'
                                     '• $lock - Lock channel for AI responses\n'
                                     '• $unlock - Unlock channel\n'
                                     '• $gaglock - Lock channel with annoying GAG responses\n'
                                     '• $gagunlock - Unlock GAG mode\n'
                                     '• $gagtestlock - Lock channel with GAG responses (responds to your messages too)\n'
                                     '• $gagtestunlock - Unlock GAG test mode\n'
                                     '• $silentgaglock ($sgaglock) - STEALTH gag lock (no visible traces)\n'
                                     '• $silentgagunlock ($sgagunlock) - STEALTH gag unlock\n'
                                     '• $swglock - SUPER STEALTH mode (short replies, no typing indicator)\n'
                                     '• $swgunlock - Exit SUPER STEALTH mode\n'
                                     '• $spawnlock - SPAWN CULT ROASTING mode (mock Spawnism followers)\n'
                                     '• $spawnunlock - Exit spawn cult roasting mode\n'
                                     '• $v2lock - V2 ENHANCED SUPER STEALTH mode (1-5 word responses + memory + image analysis)\n'
                                     '• $v2unlock - Exit V2 enhanced super stealth mode\n'
                                     '• $scrape - Silently scrape all messages from current channel\n'
                                     '• $scrape \u003cnumber\u003e - Scrape specific number of messages\n'
                                     '• $scrapestats - Show scraping database statistics (console only)\n'
                                     '• $hello - Greeting\n'
                                     '• $help - Show this help message')
    
    else:
        if channel_id in locked_channels:
            ai_response = await get_ai_response(message.content, mode="normal")
            if ai_response:  
                async with message.channel.typing():
                    await message.reply(ai_response)
        
        elif channel_id in gaglocked_channels:
            print(f"DEBUG: Processing gag-locked message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            
            store_gaglock_message(channel_id, message.author.id, message.author.name, message.content)
            
            recent_messages = get_gaglock_message_history(channel_id, limit=50)
            history_context = ""
            if recent_messages:
                formatted_messages = []
                for username, message_content, timestamp in recent_messages:
                    formatted_messages.append(f"{username}: {message_content}")
                history_context = f"Recent context: {'; '.join(formatted_messages[-15:])}. "  
            
            enhanced_prompt = f"User '{message.author.name}' said: '{message.content}'"
            if history_context:
                enhanced_prompt = history_context + enhanced_prompt
            
            ai_response = await get_ai_response(enhanced_prompt, mode="gag")
            if ai_response:  
                print(f"DEBUG: GAG AI response: {ai_response[:100]}...")
                async with message.channel.typing():
                    await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")
        
        elif channel_id in silentgaglocked_channels:
            print(f"DEBUG: Processing SILENT gag-locked message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            
            store_gaglock_message(channel_id, message.author.id, message.author.name, message.content)
            
            recent_messages = get_gaglock_message_history(channel_id, limit=50)
            history_context = ""
            if recent_messages:
                formatted_messages = []
                for username, message_content, timestamp in recent_messages:
                    formatted_messages.append(f"{username}: {message_content}")
                history_context = f"Recent context: {'; '.join(formatted_messages[-15:])}. "  
            
            enhanced_prompt = f"User '{message.author.name}' said: '{message.content}'"
            if history_context:
                enhanced_prompt = history_context + enhanced_prompt
            
            ai_response = await get_ai_response(enhanced_prompt, mode="gag")
            if ai_response:  
                print(f"DEBUG: SILENT GAG AI response: {ai_response[:100]}...")
                async with message.channel.typing():
                    await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")
        
        elif channel_id in spawnlocked_channels:
            print(f"DEBUG: Processing SPAWN message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            ai_response = await get_ai_response(message.content, mode="spawn")
            if ai_response:  
                print(f"DEBUG: SPAWN AI response: {ai_response[:100]}...")
                await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")
        
        elif channel_id in superstealthlocked_channels:
            print(f"DEBUG: Processing SUPER STEALTH message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            ai_response = await get_ai_response(message.content, mode="superstealth")
            if ai_response:  
                print(f"DEBUG: SUPER STEALTH AI response: {ai_response[:100]}...")
                await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")
        
        elif channel_id in v2locked_channels and message.author != client.user:
            print(f"DEBUG: Processing V2 message from {message.author.name} in channel {channel_id}")
            print(f"DEBUG: Message content: {message.content}")
            
            image_description = None
            if message.attachments:
                image_description = await process_image_for_v2(message.attachments[0].url)
            
            if message.author != client.user:
                store_v2_message(channel_id, message.author.id, message.author.name, message.author.display_name, getattr(message.author, 'bio', None), message.content, image_description)
            
            recent_messages = get_v2_message_history(channel_id, limit=200)
            history_context = ""
            if recent_messages:
                formatted_messages = []
                for username, display_name, user_bio, message_content, image_description, timestamp in recent_messages:
                    if image_description:
                        formatted_messages.append(f"{username}: {message_content} [{image_description}]")
                    else:
                        formatted_messages.append(f"{username}: {message_content}")
                history_context = f"Recent messages: {'; '.join(formatted_messages)}. "
            
            enhanced_prompt = f"User '{message.author.name}' (display: {message.author.display_name}) said: '{message.content}'"
            if image_description:
                enhanced_prompt += f" and {image_description}"
            if history_context:
                enhanced_prompt = history_context + enhanced_prompt
            
            print(f"DEBUG: Enhanced prompt for V2: {enhanced_prompt[:200]}...")
            
            ai_response = await get_ai_response(enhanced_prompt, mode="v2")
            if ai_response:
                if ai_response.startswith('$') or any(cmd in ai_response.lower() for cmd in ['$lock', '$unlock', '$v2lock', '$v2unlock', '$swglock', '$swgunlock']):
                    print(f"DEBUG: Blocked V2 response containing command: {ai_response}")
                    ai_response = "obviously"  
                
                print(f"DEBUG: V2 AI response: {ai_response[:100]}...")
                await message.reply(ai_response)
            else:
                print("DEBUG: Rate limited, skipping response")

try:
    print("Starting client.run()...")
    client.run(token)  
except discord.LoginFailure:
    print("Invalid token provided. Please check your token and try again.")
except Exception as e:
    import traceback
    print(f"An error occurred: {e}")
    print(f"Traceback: {traceback.format_exc()}")
