import discord
import sqlite3
import asyncio
import json
from datetime import datetime
import re

class MessageScraper:
    def __init__(self, db_path='scraped_messages.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database for storing scraped messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                channel_id TEXT NOT NULL,
                channel_name TEXT,
                guild_id TEXT,
                guild_name TEXT,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT,
                message_content TEXT NOT NULL,
                has_attachments BOOLEAN DEFAULT FALSE,
                attachment_urls TEXT,
                reaction_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                message_length INTEGER,
                timestamp DATETIME,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel_id ON scraped_messages(channel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON scraped_messages(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON scraped_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_length ON scraped_messages(message_length)')
        
        conn.commit()
        conn.close()
        print(f"[SCRAPER] Database initialized at {self.db_path}")
    
    def is_quality_message(self, message):
        """Filter for quality messages worth training on"""
        content = message.content.strip()
        
        # Skip empty messages
        if not content:
            return False
        
        # Skip very short messages (less than 10 characters)
        if len(content) < 10:
            return False
        
        # Skip messages that are mostly special characters or numbers
        if len(re.sub(r'[^a-zA-Z\s]', '', content)) < 5:
            return False
        
        # Skip common spam patterns
        spam_patterns = [
            r'^\.+$',  # Just dots
            r'^lol+$',  # Just lol
            r'^ok+$',   # Just ok
            r'^yes+$',  # Just yes
            r'^no+$',   # Just no
            r'^[xd]+$', # Just xd
            r'^[haha]+$', # Just haha
            r'^[0-9]+$', # Just numbers
        ]
        
        for pattern in spam_patterns:
            if re.match(pattern, content.lower()):
                return False
        
        # Prefer messages with engagement (reactions or replies)
        has_engagement = len(message.reactions) > 0 or message.reference is not None
        
        # Prefer longer, more conversational messages
        is_conversational = len(content) > 20
        
        return True  # Basic filtering, we'll prioritize quality ones later
    
    def store_message(self, message, channel_name, guild_name):
        """Store a single message in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get attachment URLs if any
        attachment_urls = []
        if message.attachments:
            attachment_urls = [att.url for att in message.attachments]
        
        # Count reactions
        reaction_count = sum(reaction.count for reaction in message.reactions)
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO scraped_messages (
                    message_id, channel_id, channel_name, guild_id, guild_name,
                    user_id, username, display_name, message_content,
                    has_attachments, attachment_urls, reaction_count,
                    reply_count, message_length, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(message.id),
                str(message.channel.id),
                channel_name,
                str(message.guild.id) if message.guild else None,
                guild_name,
                str(message.author.id),
                message.author.name,
                message.author.display_name,
                message.content,
                len(message.attachments) > 0,
                json.dumps(attachment_urls) if attachment_urls else None,
                reaction_count,
                1 if message.reference else 0,
                len(message.content),
                message.created_at
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[SCRAPER] Error storing message {message.id}: {e}")
            return False
        finally:
            conn.close()
    
    async def scrape_channel(self, channel, limit=None):
        """Scrape all messages from a channel"""
        print(f"[SCRAPER] Starting scrape of #{channel.name}")
        print(f"[SCRAPER] Channel ID: {channel.id}")
        print(f"[SCRAPER] Guild: {channel.guild.name if channel.guild else 'DM'}")
        
        channel_name = channel.name
        guild_name = channel.guild.name if channel.guild else "DM"
        
        total_messages = 0
        quality_messages = 0
        stored_messages = 0
        skipped_messages = 0
        
        try:
            print(f"[SCRAPER] Fetching messages... (this may take a while)")
            
            async for message in channel.history(limit=limit):
                total_messages += 1
                
                # Progress update every 1000 messages
                if total_messages % 1000 == 0:
                    print(f"[SCRAPER] Progress: {total_messages} messages processed, {quality_messages} quality, {stored_messages} stored")
                
                # Skip bot messages (but not your selfbot)
                if message.author.bot:
                    skipped_messages += 1
                    continue
                
                # Check if it's a quality message
                if self.is_quality_message(message):
                    quality_messages += 1
                    
                    # Store the message
                    if self.store_message(message, channel_name, guild_name):
                        stored_messages += 1
                    
                    # Brief pause to avoid overwhelming the system
                    if stored_messages % 100 == 0:
                        await asyncio.sleep(0.1)
                else:
                    skipped_messages += 1
            
            print(f"[SCRAPER] ✅ Scraping complete!")
            print(f"[SCRAPER] Total messages processed: {total_messages}")
            print(f"[SCRAPER] Quality messages found: {quality_messages}")
            print(f"[SCRAPER] Messages stored: {stored_messages}")
            print(f"[SCRAPER] Messages skipped: {skipped_messages}")
            print(f"[SCRAPER] Quality rate: {(quality_messages/total_messages)*100:.1f}%")
            
            return {
                'total': total_messages,
                'quality': quality_messages,
                'stored': stored_messages,
                'skipped': skipped_messages
            }
            
        except Exception as e:
            print(f"[SCRAPER] ❌ Error during scraping: {e}")
            return None
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM scraped_messages')
        total = cursor.fetchone()[0]
        
        # Messages by channel
        cursor.execute('''
            SELECT channel_name, COUNT(*) as count 
            FROM scraped_messages 
            GROUP BY channel_id, channel_name 
            ORDER BY count DESC
        ''')
        by_channel = cursor.fetchall()
        
        # Messages by user (top 10)
        cursor.execute('''
            SELECT username, COUNT(*) as count 
            FROM scraped_messages 
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        by_user = cursor.fetchall()
        
        # Average message length
        cursor.execute('SELECT AVG(message_length) FROM scraped_messages')
        avg_length = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'by_channel': by_channel,
            'by_user': by_user,
            'avg_length': avg_length
        }
    
    def get_training_data(self, channel_id=None, min_length=20, limit=10000):
        """Get quality messages for training"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT username, message_content, reaction_count, message_length
            FROM scraped_messages 
            WHERE message_length >= ? 
        '''
        params = [min_length]
        
        if channel_id:
            query += ' AND channel_id = ?'
            params.append(str(channel_id))
        
        query += '''
            ORDER BY (reaction_count * 2 + message_length) DESC
            LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
