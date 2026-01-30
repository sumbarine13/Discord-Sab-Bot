"""
===========================================
DISCORD BOT v3.0 - Complete System
===========================================
Features:
- 60+ commands including troll kick system
- Groq AI integration with context memory
- Web dashboard for moderation
- Economy & leveling system
- Music player
- Advanced moderation tools
- Database with backup system
===========================================
"""

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal
import asyncio
import aiohttp
import json
import os
import random
import datetime
import logging
import sqlite3
from typing import Optional, List, Dict, Union
from enum import Enum
import re
import math
import time
import hashlib
import yaml

# =========================
# CONFIGURATION
# =========================
class Config:
    """Central configuration class"""
    PREFIX = "!"
    VERSION = "3.0.0"
    OWNER_IDS = [1307042499898118246]  # Your ID
    DASHBOARD_PASSWORD = "Sumbarine13"
    SUPPORT_SERVER = "https://discord.gg/example"
    GITHUB_REPO = "https://github.com/yourusername/discord-bot"
    
    # Colors
    COLORS = {
        "success": 0x2ecc71,
        "error": 0xe74c3c,
        "warning": 0xf39c12,
        "info": 0x3498db,
        "moderation": 0xe67e22,
        "fun": 0x9b59b6,
        "music": 0x1abc9c,
        "economy": 0xf1c40f
    }
    
    # API Keys (load from .env)
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    # Web Dashboard
    DASHBOARD_PORT = 8080
    DASHBOARD_HOST = "0.0.0.0"

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DiscordBot')

# =========================
# DATABASE MANAGER
# =========================
class Database:
    """SQLite database manager"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_db()
    
    def init_db(self):
        """Initialize database with tables"""
        self.conn = sqlite3.connect('data/bot.db')
        self.cursor = self.conn.cursor()
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                balance INTEGER DEFAULT 100,
                bank INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                reputation INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Guilds table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '!',
                mod_log_channel INTEGER,
                welcome_channel INTEGER,
                mute_role INTEGER,
                auto_mod INTEGER DEFAULT 0,
                welcome_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Economy transactions
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Moderation logs
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                duration TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Music playlists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                songs TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id: int):
        """Get user data"""
        self.cursor.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            # Create new user
            self.cursor.execute(
                'INSERT INTO users (user_id) VALUES (?)',
                (user_id,)
            )
            self.conn.commit()
            return self.get_user(user_id)
        
        return {
            'user_id': result[0],
            'xp': result[1],
            'level': result[2],
            'balance': result[3],
            'bank': result[4],
            'daily_streak': result[5],
            'last_daily': result[6],
            'reputation': result[7],
            'warnings': result[8],
            'created_at': result[9]
        }
    
    def update_user(self, user_id: int, **kwargs):
        """Update user data"""
        for key, value in kwargs.items():
            self.cursor.execute(
                f'UPDATE users SET {key} = ? WHERE user_id = ?',
                (value, user_id)
            )
        self.conn.commit()
    
    def add_transaction(self, user_id: int, amount: int, type: str, description: str):
        """Add transaction record"""
        self.cursor.execute(
            '''INSERT INTO transactions 
               (user_id, amount, type, description) 
               VALUES (?, ?, ?, ?)''',
            (user_id, amount, type, description)
        )
        self.conn.commit()
    
    def log_moderation(self, guild_id: int, user_id: int, moderator_id: int, 
                      action: str, reason: str, duration: str = None):
        """Log moderation action"""
        self.cursor.execute(
            '''INSERT INTO moderation_logs 
               (guild_id, user_id, moderator_id, action, reason, duration) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (guild_id, user_id, moderator_id, action, reason, duration)
        )
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# =========================
# AI SERVICE WITH MEMORY
# =========================
class AIService:
    """Groq AI with conversation memory"""
    
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = None
        self.conversations = {}  # Store conversation history
        
    async def initialize(self):
        """Initialize AI service"""
        self.session = aiohttp.ClientSession()
    
    async def ask(self, user_id: int, question: str, context: str = ""):
        """Ask AI with conversation memory"""
        if not self.api_key:
            return "🤖 AI service is currently unavailable."
        
        # Get or create conversation history
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        # Add system message
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful Discord bot assistant. 
                {context}
                Keep responses concise, friendly, and under 200 characters."""
            }
        ]
        
        # Add conversation history (last 5 messages)
        for msg in self.conversations[user_id][-5:]:
            messages.append(msg)
        
        # Add current question
        messages.append({
            "role": "user",
            "content": question
        })
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "mixtral-8x7b-32768",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            async with self.session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    answer = data["choices"][0]["message"]["content"]
                    
                    # Store in conversation history
                    self.conversations[user_id].extend([
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer}
                    ])
                    
                    # Limit history size
                    if len(self.conversations[user_id]) > 20:
                        self.conversations[user_id] = self.conversations[user_id][-20:]
                    
                    return answer
                else:
                    return f"❌ API Error: {response.status}"
                    
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "⚠️ I encountered an error. Please try again."
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.close()

# =========================
# MUSIC PLAYER
# =========================
class MusicPlayer:
    """Music player for voice channels"""
    
    def __init__(self):
        self.queues = {}
        self.now_playing = {}
        
    async def play_song(self, ctx, query: str):
        """Play a song from YouTube"""
        try:
            if not ctx.author.voice:
                return await ctx.send("❌ You need to be in a voice channel!")
            
            voice_channel = ctx.author.voice.channel
            
            # Join voice channel if not already connected
            if not ctx.voice_client:
                await voice_channel.connect()
            elif ctx.voice_client.channel != voice_channel:
                await ctx.voice_client.move_to(voice_channel)
            
            # Search for song
            # Note: You'll need yt-dlp or youtube-dl for this
            # This is a simplified version
            
            await ctx.send(f"🎵 Searching for: {query}")
            
            # Simulated response
            song_info = {
                "title": f"Example Song - {query}",
                "duration": "3:45",
                "url": "https://example.com"
            }
            
            # Add to queue
            if ctx.guild.id not in self.queues:
                self.queues[ctx.guild.id] = []
            
            self.queues[ctx.guild.id].append(song_info)
            
            if len(self.queues[ctx.guild.id]) == 1:
                await self._play_next(ctx)
            
            embed = discord.Embed(
                title="🎵 Added to Queue",
                description=f"**{song_info['title']}**\nDuration: {song_info['duration']}",
                color=discord.Color(Config.COLORS["music"])
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Music error: {e}")
            await ctx.send("❌ Could not play the song.")
    
    async def _play_next(self, ctx):
        """Play next song in queue"""
        if ctx.guild.id in self.queues and self.queues[ctx.guild.id]:
            song = self.queues[ctx.guild.id].pop(0)
            self.now_playing[ctx.guild.id] = song
            
            # Here you would actually play the audio
            # This is a placeholder
            
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"**{song['title']}**",
                color=discord.Color(Config.COLORS["music"])
            )
            embed.add_field(name="Duration", value=song["duration"])
            
            message = await ctx.send(embed=embed)
            
            # Add control reactions
            for emoji in ["⏯️", "⏭️", "⏹️", "🔉", "🔊"]:
                await message.add_reaction(emoji)
    
    async def stop(self, ctx):
        """Stop music"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            if ctx.guild.id in self.queues:
                self.queues[ctx.guild.id].clear()
            if ctx.guild.id in self.now_playing:
                del self.now_playing[ctx.guild.id]
            await ctx.send("⏹️ Stopped music and cleared queue.")

# =========================
# MAIN BOT CLASS
# =========================
class DiscordBot(commands.Bot):
    """Main bot class with all features"""
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # Initialize components
        self.db = Database()
        self.ai = AIService()
        self.music = MusicPlayer()
        self.start_time = datetime.datetime.now()
        
        # Statistics
        self.command_count = 0
        self.message_count = 0
        
        # Cooldown tracking
        self.cooldowns = {}
        
        # Web dashboard data
        self.dashboard_sessions = {}
        
        logger.info("Bot initialized")
    
    async def get_prefix(self, message):
        """Get dynamic prefix"""
        if not message.guild:
            return Config.PREFIX
        
        # Get from database
        self.db.cursor.execute(
            'SELECT prefix FROM guilds WHERE guild_id = ?',
            (message.guild.id,)
        )
        result = self.db.cursor.fetchone()
        
        return result[0] if result else Config.PREFIX
    
    async def setup_hook(self):
        """Setup on startup"""
        logger.info("Starting bot setup...")
        
        # Initialize AI
        await self.ai.initialize()
        
        # Load cogs
        await self.load_cogs()
        
        # Start background tasks
        self.status_task.start()
        self.stats_task.start()
        self.backup_task.start()
        
        logger.info("Bot setup complete!")
    
    async def load_cogs(self):
        """Load all cogs"""
        cogs = [
            Moderation(self),
            Fun(self),
            Utility(self),
            Economy(self),
            Music(self),
            Events(self)
        ]
        
        for cog in cogs:
            try:
                await self.add_cog(cog)
                logger.info(f"Loaded cog: {cog.qualified_name}")
            except Exception as e:
                logger.error(f"Failed to load cog: {e}")
    
    @tasks.loop(minutes=5)
    async def status_task(self):
        """Update bot status"""
        statuses = [
            discord.Activity(type=discord.ActivityType.playing, name=f"on {len(self.guilds)} servers"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{self.command_count} commands"),
            discord.Activity(type=discord.ActivityType.listening, name=f"{Config.PREFIX}help"),
            discord.Activity(type=discord.ActivityType.competing, name="Discord Bot Olympics")
        ]
        
        await self.change_presence(
            activity=random.choice(statuses),
            status=discord.Status.online
        )
    
    @tasks.loop(minutes=10)
    async def stats_task(self):
        """Update statistics"""
        self.db.cursor.execute('SELECT COUNT(*) FROM users')
        user_count = self.db.cursor.fetchone()[0]
        
        logger.info(f"Stats: {len(self.guilds)} servers, {user_count} users, {self.command_count} commands")
    
    @tasks.loop(hours=6)
    async def backup_task(self):
        """Create database backup"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/backups/backup_{timestamp}.db"
        
        # Create backup
        import shutil
        shutil.copy2('data/bot.db', backup_file)
        
        # Keep only last 7 backups
        backups = sorted([f for f in os.listdir('data/backups') if f.startswith('backup_')])
        if len(backups) > 7:
            for old_backup in backups[:-7]:
                os.remove(f"data/backups/{old_backup}")
        
        logger.info(f"Created backup: {backup_file}")
    
    async def close(self):
        """Cleanup on shutdown"""
        await self.ai.close()
        self.db.close()
        await super().close()
        logger.info("Bot shutdown complete")

# =========================
# MODERATION COG (20+ Commands)
# =========================
class Moderation(commands.Cog, name="🔨 Moderation"):
    """Advanced moderation commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.muted_users = {}
    
    @commands.command(
        name="trollkick",
        description="Kick and invite back as a prank",
        usage="<member> [reason]"
    )
    @commands.has_permissions(kick_members=True)
    async def trollkick(self, ctx, member: discord.Member, *, reason: str = "Trolling around"):
        """Troll kick - kick and invite back"""
        # Check hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot troll someone with equal or higher role.")
        
        # Save roles
        old_roles = [role for role in member.roles if role.name != "@everyone"]
        
        try:
            # Create invite
            invite = await ctx.channel.create_invite(
                max_age=600,  # 10 minutes
                max_uses=1,
                unique=True,
                reason=f"Troll kick by {ctx.author}"
            )
            
            # Send DM
            embed = discord.Embed(
                title=f"😜 You've been kicked from {ctx.guild.name}!",
                description=(
                    f"**Reason:** {reason}\n\n"
                    f"LOL JK! This is a prank! 😂\n\n"
                    f"Use this invite to rejoin: {invite.url}\n"
                    f"Your roles will be restored automatically."
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="Don't worry, it's just a joke!")
            
            await member.send(embed=embed)
            
        except discord.Forbidden:
            # Can't DM, send in channel instead
            await ctx.send(f"{member.mention} check your DMs for the re-invite!")
        
        # Actually kick
        await member.kick(reason=f"Troll kick by {ctx.author}: {reason}")
        
        await ctx.send(f"😂 {member.display_name} has been troll kicked! They'll be back soon...")
        
        # Wait for rejoin
        def check(m):
            return m.id == member.id and m.guild == ctx.guild
        
        try:
            rejoined = await self.bot.wait_for('member_join', timeout=300, check=check)
            
            # Restore roles
            if old_roles:
                await rejoined.add_roles(*old_roles)
                await ctx.send(f"✅ {member.display_name} rejoined and roles restored!")
            else:
                await ctx.send(f"✅ {member.display_name} rejoined!")
                
        except asyncio.TimeoutError:
            await ctx.send(f"⚠️ {member.display_name} didn't rejoin within 5 minutes.")
    
    @commands.command(
        name="ban",
        description="Ban a user",
        usage="<member> [reason]"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban command"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban someone with equal or higher role.")
        
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
        
        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**User:** {member.mention}\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        # Log to database
        self.bot.db.log_moderation(
            ctx.guild.id, member.id, ctx.author.id,
            "ban", reason, None
        )
    
    @commands.command(
        name="kick",
        description="Kick a user",
        usage="<member> [reason]"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick command"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot kick someone with equal or higher role.")
        
        await member.kick(reason=f"{ctx.author}: {reason}")
        
        embed = discord.Embed(
            title="👢 User Kicked",
            description=f"**User:** {member.mention}\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        self.bot.db.log_moderation(
            ctx.guild.id, member.id, ctx.author.id,
            "kick", reason, None
        )
    
    @commands.command(
        name="mute",
        description="Mute a user",
        usage="<member> [duration] [reason]"
    )
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason: str = "No reason provided"):
        """Mute command with duration"""
        # Parse duration
        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            return await ctx.send("❌ Invalid duration format. Use: 10m, 2h, 1d")
        
        # Create mute role if needed
        mute_role = await self.get_mute_role(ctx.guild)
        if not mute_role:
            return await ctx.send("❌ Could not create mute role. Check bot permissions.")
        
        await member.add_roles(mute_role, reason=f"{ctx.author}: {reason}")
        
        # Store mute info
        mute_id = f"{ctx.guild.id}_{member.id}"
        self.muted_users[mute_id] = {
            "unmute_time": time.time() + duration_seconds,
            "role_id": mute_role.id
        }
        
        embed = discord.Embed(
            title="🔇 User Muted",
            description=(
                f"**User:** {member.mention}\n"
                f"**Duration:** {self.format_duration(duration_seconds)}\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.dark_gray()
        )
        await ctx.send(embed=embed)
        
        self.bot.db.log_moderation(
            ctx.guild.id, member.id, ctx.author.id,
            "mute", reason, duration
        )
    
    @commands.command(
        name="unmute",
        description="Unmute a user",
        usage="<member>"
    )
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute command"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            return await ctx.send("❌ No mute role found.")
        
        if mute_role not in member.roles:
            return await ctx.send("❌ User is not muted.")
        
        await member.remove_roles(mute_role, reason=f"Unmuted by {ctx.author}")
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    
    @commands.command(
        name="warn",
        description="Warn a user",
        usage="<member> [reason]"
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn command"""
        user_data = self.bot.db.get_user(member.id)
        warnings = user_data.get('warnings', 0) + 1
        
        self.bot.db.update_user(member.id, warnings=warnings)
        
        embed = discord.Embed(
            title="⚠️ User Warned",
            description=(
                f"**User:** {member.mention}\n"
                f"**Warning:** #{warnings}\n"
                f"**Reason:** {reason}\n\n"
                f"Total warnings: {warnings}"
            ),
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        
        # Auto-mute after 3 warnings
        if warnings >= 3:
            mute_role = await self.get_mute_role(ctx.guild)
            if mute_role:
                await member.add_roles(mute_role, reason="Auto-mute: 3+ warnings")
                await ctx.send(f"🔇 {member.mention} auto-muted for reaching 3 warnings.")
    
    @commands.command(
        name="clearwarns",
        description="Clear warnings for a user",
        usage="<member>"
    )
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, member: discord.Member):
        """Clear warnings"""
        self.bot.db.update_user(member.id, warnings=0)
        await ctx.send(f"✅ Cleared all warnings for {member.mention}")
    
    @commands.command(
        name="purge",
        aliases=["clear"],
        description="Delete messages",
        usage="[amount=10]"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        """Purge messages"""
        if amount > 100:
            return await ctx.send("❌ Maximum 100 messages at once.")
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages.")
        await asyncio.sleep(3)
        await msg.delete()
    
    @commands.command(
        name="lock",
        description="Lock a channel",
        usage="[channel]"
    )
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 {channel.mention} has been locked.")
    
    @commands.command(
        name="unlock",
        description="Unlock a channel",
        usage="[channel]"
    )
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 {channel.mention} has been unlocked.")
    
    @commands.command(
        name="slowmode",
        description="Set slowmode",
        usage="[seconds]"
    )
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set slowmode"""
        if seconds < 0 or seconds > 21600:
            return await ctx.send("❌ Slowmode must be 0-21600 seconds.")
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled")
        else:
            await ctx.send(f"⏱️ Slowmode set to {seconds} seconds")
    
    @commands.command(
        name="nuke",
        description="Clone and delete channel (reset)",
        usage=""
    )
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Nuke channel"""
        # Confirmation
        embed = discord.Embed(
            title="💣 Channel Nuke",
            description="Are you sure you want to nuke this channel?",
            color=discord.Color.red()
        )
        embed.set_footer(text="This will delete all messages and create a new channel!")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Clone channel
                new_channel = await ctx.channel.clone()
                await ctx.channel.delete()
                
                # Send nuke message
                embed = discord.Embed(
                    title="💥 Channel Nuked!",
                    description="This channel has been reset.",
                    color=discord.Color.red()
                )
                await new_channel.send(embed=embed)
            else:
                await ctx.send("Nuke cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Nuke confirmation timed out.")
    
    async def get_mute_role(self, guild):
        """Get or create mute role"""
        mute_role = discord.utils.get(guild.roles, name="Muted")
        
        if not mute_role:
            try:
                mute_role = await guild.create_role(
                    name="Muted",
                    color=discord.Color.dark_gray(),
                    reason="Mute role for moderation"
                )
                
                # Set permissions for all channels
                for channel in guild.channels:
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        speak=False
                    )
                
                return mute_role
            except:
                return None
        
        return mute_role
    
    def parse_duration(self, duration_str):
        """Parse duration string to seconds"""
        try:
            if duration_str.isdigit():
                return int(duration_str) * 60  # Default to minutes
            
            match = re.match(r'^(\d+)([smhd])$', duration_str.lower())
            if not match:
                return None
            
            amount, unit = match.groups()
            amount = int(amount)
            
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            return amount * multipliers[unit]
        except:
            return None
    
    def format_duration(self, seconds):
        """Format seconds to human readable"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d"

# =========================
# FUN COG (20+ Commands)
# =========================
class Fun(commands.Cog, name="🎮 Fun & Games"):
    """Fun commands and games"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.games = {}
    
    @commands.command(
        name="coinflip",
        aliases=["flip", "coin"],
        description="Flip a coin"
    )
    async def coinflip(self, ctx):
        """Coin flip"""
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on **{result}**!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="dice",
        aliases=["roll"],
        description="Roll dice",
        usage="[dice=1d6]"
    )
    async def dice(self, ctx, dice: str = "1d6"):
        """Roll dice"""
        try:
            rolls, limit = map(int, dice.split('d'))
            if rolls > 20 or limit > 100:
                return await ctx.send("❌ Maximum: 20 dice with 100 sides")
            
            results = [random.randint(1, limit) for _ in range(rolls)]
            total = sum(results)
            
            embed = discord.Embed(
                title="🎲 Dice Roll",
                description=f"Rolling {dice}...",
                color=discord.Color.blue()
            )
            
            if rolls <= 10:
                embed.add_field(name="Results", value=", ".join(map(str, results)), inline=False)
            
            embed.add_field(name="Total", value=str(total), inline=True)
            
            if rolls == 1:
                embed.add_field(name="Max", value=str(limit), inline=True)
            
            await ctx.send(embed=embed)
            
        except:
            await ctx.send("❌ Format: NdN (e.g., 2d6, 1d20)")
    
    @commands.command(
        name="rps",
        description="Rock Paper Scissors",
        usage="<choice>"
    )
    async def rps(self, ctx, choice: str):
        """Rock Paper Scissors"""
        choices = ["rock", "paper", "scissors"]
        choice = choice.lower()
        
        if choice not in choices:
            return await ctx.send("❌ Choose: rock, paper, or scissors")
        
        bot_choice = random.choice(choices)
        
        # Determine winner
        if choice == bot_choice:
            result = "It's a tie! 🤝"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "You win! 🎉"
        else:
            result = "I win! 😎"
        
        embed = discord.Embed(
            title="✂️ Rock Paper Scissors",
            description=(
                f"**You:** {choice.title()}\n"
                f"**Bot:** {bot_choice.title()}\n\n"
                f"**{result}**"
            ),
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="8ball",
        description="Ask the magic 8-ball",
        usage="<question>"
    )
    async def eightball(self, ctx, *, question: str):
        """8-ball"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            description=(
                f"**Question:** {question}\n"
                f"**Answer:** {random.choice(responses)}"
            ),
            color=discord.Color.dark_blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="choose",
        description="Choose between options",
        usage="<option1> or <option2> or ..."
    )
    async def choose(self, ctx, *, options: str):
        """Choose command"""
        if " or " not in options:
            return await ctx.send("❌ Separate options with 'or'")
        
        choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
        
        if len(choices) < 2:
            return await ctx.send("❌ Need at least 2 options")
        
        chosen = random.choice(choices)
        
        embed = discord.Embed(
            title="🤔 Choose",
            description=(
                f"**Options:** {', '.join(choices)}\n\n"
                f"**I choose:** **{chosen}**"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="fact",
        description="Random fact"
    )
    async def fact(self, ctx):
        """Random fact"""
        facts = [
            "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat.",
            "Octopuses have three hearts. Two pump blood to the gills, while the third pumps it to the rest of the body.",
            "A group of flamingos is called a 'flamboyance'.",
            "Bananas are berries, but strawberries are not.",
            "The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.",
            "A day on Venus is longer than a year on Venus.",
            "Humans share 50% of their DNA with bananas.",
            "The electric chair was invented by a dentist.",
            "There are more possible iterations of a game of chess than there are atoms in the known universe.",
            "A jiffy is an actual unit of time: 1/100th of a second."
        ]
        
        embed = discord.Embed(
            title="🧠 Did You Know?",
            description=random.choice(facts),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="joke",
        description="Tell a joke"
    )
    async def joke(self, ctx):
        """Joke command"""
        jokes = [
            ("Why don't scientists trust atoms?", "Because they make up everything!"),
            ("Why did the scarecrow win an award?", "Because he was outstanding in his field!"),
            ("What do you call a bear with no teeth?", "A gummy bear!"),
            ("Why don't eggs tell jokes?", "They'd crack each other up!"),
            ("What do you call a fake noodle?", "An impasta!"),
            ("Why did the math book look so sad?", "Because it had too many problems."),
            ("What do you call a snowman with a six-pack?", "An abdominal snowman!"),
            ("Why did the coffee file a police report?", "It got mugged!"),
            ("What do you call a fish wearing a bowtie?", "Sofishticated!"),
            ("Why can't you trust stairs?", "They're always up to something!")
        ]
        
        setup, punchline = random.choice(jokes)
        
        embed = discord.Embed(
            title="😂 Random Joke",
            description=f"**{setup}**\n\n||{punchline}||",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="quote",
        description="Inspirational quote"
    )
    async def quote(self, ctx):
        """Quote command"""
        quotes = [
            ("The only way to do great work is to love what you do.", "Steve Jobs"),
            ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
            ("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs"),
            ("Stay hungry, stay foolish.", "Steve Jobs"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It always seems impossible until it's done.", "Nelson Mandela"),
            ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
            ("The only limit to our realization of tomorrow will be our doubts of today.", "Franklin D. Roosevelt"),
            ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
            ("Believe you can and you're halfway there.", "Theodore Roosevelt")
        ]
        
        quote, author = random.choice(quotes)
        
        embed = discord.Embed(
            title="💭 Inspirational Quote",
            description=f"*{quote}*\n\n— **{author}**",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="meme",
        description="Random meme idea"
    )
    async def meme(self, ctx):
        """Meme command"""
        memes = [
            ("Distracted Boyfriend", "Looking at other options while committed"),
            ("Drake Hotline Bling", "Approving vs disapproving"),
            ("Change My Mind", "Controversial opinion sign"),
            ("Two Buttons", "Difficult choice between two options"),
            ("Roll Safe", "Tapping forehead genius idea"),
            ("Woman Yelling at Cat", "Dramatic confrontation"),
            ("Panik Kalm Panik", "Emotional rollercoaster"),
            ("Is This A Pigeon", "Misidentifying something obvious"),
            ("American Chopper Argument", "Heated debate about trivial things"),
            ("Expanding Brain", "Evolution of ideas")
        ]
        
        meme, description = random.choice(memes)
        
        embed = discord.Embed(
            title="😄 Random Meme",
            description=f"**{meme}**\n{description}",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Use an image editor to create this meme!")
        await ctx.send(embed=embed)
    
    @commands.command(
        name="ascii",
        description="Convert text to ASCII art",
        usage="<text>"
    )
    async def ascii(self, ctx, *, text: str):
        """ASCII art"""
        # Simple ASCII conversion
        if len(text) > 20:
            return await ctx.send("❌ Text too long (max 20 characters)")
        
        ascii_map = {
            'a': '''
  ▄▄  
 █  █ 
 █▀▀█ 
 █  █ 
   █  
''',
            'b': '''
 █▄▄  
 █  █ 
 █▄▄█ 
 █  █ 
 █▄▄  
'''
        }
        
        # Create simple ASCII
        result = ""
        for char in text.lower():
            if char in ascii_map:
                result += ascii_map[char]
            else:
                result += f" {char} \n"
        
        embed = discord.Embed(
            title="🎨 ASCII Art",
            description=f"```{result}```",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="lottery",
        description="Buy a lottery ticket",
        usage=""
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def lottery(self, ctx):
        """Lottery command"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        # Check balance
        ticket_price = 50
        if user_data['balance'] < ticket_price:
            return await ctx.send(f"❌ You need ${ticket_price} for a lottery ticket!")
        
        # Deduct money
        self.bot.db.update_user(ctx.author.id, balance=user_data['balance'] - ticket_price)
        
        # Generate numbers
        numbers = sorted(random.sample(range(1, 51), 6))
        winning_numbers = sorted(random.sample(range(1, 51), 6))
        
        # Check matches
        matches = len(set(numbers) & set(winning_numbers))
        
        # Calculate prize
        prizes = {
            0: 0,
            1: 0,
            2: 10,
            3: 100,
            4: 1000,
            5: 10000,
            6: 1000000
        }
        
        prize = prizes[matches]
        
        if prize > 0:
            self.bot.db.update_user(ctx.author.id, balance=user_data['balance'] - ticket_price + prize)
            self.bot.db.add_transaction(ctx.author.id, prize, "lottery_win", f"Matched {matches} numbers")
        
        embed = discord.Embed(
            title="🎰 Lottery Results",
            color=discord.Color.gold() if prize > 0 else discord.Color.red()
        )
        embed.add_field(name="Your Numbers", value=", ".join(map(str, numbers)), inline=True)
        embed.add_field(name="Winning Numbers", value=", ".join(map(str, winning_numbers)), inline=True)
        embed.add_field(name="Matches", value=str(matches), inline=True)
        embed.add_field(name="Prize", value=f"${prize:,}", inline=True)
        
        if prize > 0:
            embed.description = f"🎉 You won **${prize:,}**!"
        else:
            embed.description = "Better luck next time!"
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="trivia",
        description="Trivia game",
        usage=""
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def trivia(self, ctx):
        """Trivia command"""
        questions = [
            {
                "question": "What is the capital of France?",
                "options": ["London", "Berlin", "Paris", "Madrid"],
                "answer": 2
            },
            {
                "question": "How many continents are there?",
                "options": ["5", "6", "7", "8"],
                "answer": 2
            },
            {
                "question": "What is the largest planet in our solar system?",
                "options": ["Earth", "Mars", "Jupiter", "Saturn"],
                "answer": 2
            },
            {
                "question": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Mark Twain", "Jane Austen"],
                "answer": 1
            },
            {
                "question": "What is the chemical symbol for gold?",
                "options": ["Go", "Gd", "Au", "Ag"],
                "answer": 2
            }
        ]
        
        q = random.choice(questions)
        
        embed = discord.Embed(
            title="❓ Trivia Time!",
            description=f"**{q['question']}**\n\n"
                       f"1️⃣ {q['options'][0]}\n"
                       f"2️⃣ {q['options'][1]}\n"
                       f"3️⃣ {q['options'][2]}\n"
                       f"4️⃣ {q['options'][3]}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="You have 30 seconds to answer!")
        
        message = await ctx.send(embed=embed)
        
        # Add reactions
        for emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]:
            await message.add_reaction(emoji)
        
        # Check answer
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            answer_map = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            user_answer = answer_map[str(reaction.emoji)]
            
            if user_answer == q['answer']:
                # Award points
                reward = random.randint(10, 50)
                user_data = self.bot.db.get_user(ctx.author.id)
                self.bot.db.update_user(ctx.author.id, balance=user_data['balance'] + reward)
                
                await ctx.send(f"✅ Correct! You won **${reward}**!")
            else:
                await ctx.send(f"❌ Wrong! The correct answer was: **{q['options'][q['answer']]}**")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up!")
    
    @commands.command(
        name="hangman",
        description="Play hangman",
        usage=""
    )
    async def hangman(self, ctx):
        """Hangman game"""
        words = ["python", "javascript", "discord", "bot", "programming", 
                "computer", "keyboard", "monitor", "internet", "website"]
        
        word = random.choice(words)
        guessed = ["_"] * len(word)
        attempts = 6
        guessed_letters = []
        
        embed = discord.Embed(
            title="🎮 Hangman",
            description=f"Word: {' '.join(guessed)}\n"
                       f"Attempts left: {attempts}\n"
                       f"Guessed letters: {', '.join(guessed_letters)}",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed)
        
        # Game loop (simplified)
        # In reality, you'd need to handle multiple games simultaneously
        
        await ctx.send("⚠️ Hangman game started! (This is a simplified version)")
    
    @commands.command(
        name="wouldyourather",
        aliases=["wyr"],
        description="Would you rather game",
        usage=""
    )
    async def wouldyourather(self, ctx):
        """WYR game"""
        questions = [
            ("Would you rather have the ability to fly or be invisible?", "Fly", "Invisible"),
            ("Would you rather live without internet or without AC/heating?", "No Internet", "No AC/Heating"),
            ("Would you rather be able to talk to animals or speak all human languages?", "Talk to Animals", "All Languages"),
            ("Would you rather have unlimited money or unlimited time?", "Unlimited Money", "Unlimited Time"),
            ("Would you rather be famous or be the best friend of someone famous?", "Be Famous", "Friend of Famous")
        ]
        
        question, option1, option2 = random.choice(questions)
        
        embed = discord.Embed(
            title="🤔 Would You Rather?",
            description=f"**{question}**\n\n"
                       f"🇦 {option1}\n"
                       f"🇧 {option2}",
            color=discord.Color.purple()
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("🇦")
        await message.add_reaction("🇧")
    
    @commands.command(
        name="truth",
        description="Random truth question",
        usage=""
    )
    async def truth(self, ctx):
        """Truth command"""
        truths = [
            "What's your biggest fear?",
            "Have you ever lied to your best friend?",
            "What's your most embarrassing moment?",
            "Do you have a secret hobby?",
            "What's the craziest thing you've ever done?",
            "Have you ever cheated on a test?",
            "What's your guilty pleasure?",
            "What's something you've never told anyone?",
            "What's your worst habit?",
            "What's the biggest mistake you've ever made?"
        ]
        
        embed = discord.Embed(
            title="🤔 Truth",
            description=random.choice(truths),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="dare",
        description="Random dare",
        usage=""
    )
    async def dare(self, ctx):
        """Dare command"""
        dares = [
            "Do 10 pushups right now!",
            "Send a funny selfie in this channel.",
            "Say something nice to the person above you.",
            "Imitate your favorite animal for 30 seconds.",
            "Sing a song in voice chat.",
            "Change your nickname to something silly for 1 hour.",
            "Tell a joke in the general channel.",
            "Post your favorite meme.",
            "Compliment 3 people in this server.",
            "Do your best impression of a celebrity."
        ]
        
        embed = discord.Embed(
            title="😎 Dare",
            description=random.choice(dares),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="rate",
        description="Rate something",
        usage="<thing>"
    )
    async def rate(self, ctx, *, thing: str):
        """Rate command"""
        rating = random.randint(1, 10)
        
        stars = "⭐" * rating
        if rating < 4:
            comment = "Not great..."
        elif rating < 7:
            comment = "Pretty good!"
        else:
            comment = "Amazing!"
        
        embed = discord.Embed(
            title="⭐ Rating",
            description=f"I give **{thing}** a **{rating}/10**\n{stars}\n\n{comment}",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="ship",
        description="Ship two users",
        usage="<user1> <user2>"
    )
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member):
        """Ship command"""
        percentage = random.randint(0, 100)
        
        # Create ship name
        name1 = user1.display_name[:len(user1.display_name)//2]
        name2 = user2.display_name[len(user2.display_name)//2:]
        ship_name = name1 + name2
        
        # Comments based on percentage
        if percentage < 20:
            comment = "Not a good match..."
        elif percentage < 50:
            comment = "Could work maybe?"
        elif percentage < 80:
            comment = "Good match!"
        else:
            comment = "Perfect match! ❤️"
        
        # Progress bar
        bars = 10
        filled = int(percentage / 100 * bars)
        progress_bar = "█" * filled + "░" * (bars - filled)
        
        embed = discord.Embed(
            title="💖 Ship Meter",
            description=(
                f"**{user1.display_name}** ❤️ **{user2.display_name}**\n\n"
                f"**Compatibility:** {percentage}%\n"
                f"{progress_bar}\n\n"
                f"**Ship Name:** {ship_name}\n"
                f"**Comment:** {comment}"
            ),
            color=discord.Color.pink()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="catfact",
        description="Random cat fact",
        usage=""
    )
    async def catfact(self, ctx):
        """Cat fact"""
        facts = [
            "Cats have 32 muscles in each ear.",
            "Cats can't taste sweetness.",
            "A cat's nose print is unique, much like a human's fingerprint.",
            "Cats sleep for 70% of their lives.",
            "Cats have a special reflective layer in their eyes called the tapetum lucidum.",
            "The world's oldest cat lived to be 38 years old.",
            "Cats can jump up to 6 times their length.",
            "A group of cats is called a clowder.",
            "Cats have 230 bones in their body (humans have 206).",
            "Cats walk with both left legs, then both right legs."
        ]
        
        embed = discord.Embed(
            title="🐱 Cat Fact",
            description=random.choice(facts),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    @commands.command(
        name="dogfact",
        description="Random dog fact",
        usage=""
    )
    async def dogfact(self, ctx):
        """Dog fact"""
        facts = [
            "Dogs' sense of smell is 40 times better than humans.",
            "Dogs can understand up to 250 words and gestures.",
            "The Basenji is the only barkless dog.",
            "Dogs have three eyelids.",
            "A dog's nose print is unique, like a human's fingerprint.",
            "Dogs dream just like humans.",
            "The Greyhound is the fastest dog breed.",
            "Dogs curl up to protect their organs while sleeping.",
            "Dogs have 18 muscles to move their ears.",
            "The average dog is as intelligent as a 2-year-old child."
        ]
        
        embed = discord.Embed(
            title="🐶 Dog Fact",
            description=random.choice(facts),
            color=discord.Color.brown()
        )
        await ctx.send(embed=embed)

# =========================
# UTILITY COG (15+ Commands)
# =========================
class Utility(commands.Cog, name="⚙️ Utility"):
    """Utility commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
    
    @commands.command(
        name="ping",
        description="Check bot latency"
    )
    async def ping(self, ctx):
        """Ping command"""
        # Calculate latencies
        ws_latency = round(self.bot.latency * 1000)
        
        start = datetime.datetime.now()
        msg = await ctx.send("🏓 Pinging...")
        end = datetime.datetime.now()
        msg_latency = round((end - start).total_seconds() * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(name="WebSocket", value=f"{ws_latency}ms", inline=True)
        embed.add_field(name="Message", value=f"{msg_latency}ms", inline=True)
        
        if ws_latency < 100:
            embed.add_field(name="Status", value="✅ Excellent", inline=True)
        elif ws_latency < 200:
            embed.add_field(name="Status", value="⚠️ Good", inline=True)
        else:
            embed.add_field(name="Status", value="❌ High", inline=True)
        
        await msg.edit(content=None, embed=embed)
    
    @commands.command(
        name="invite",
        description="Get bot invite link"
    )
    async def invite(self, ctx):
        """Invite command"""
        permissions = discord.Permissions(
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            use_external_emojis=True,
            add_reactions=True,
            connect=True,
            speak=True,
            mute_members=True,
            deafen_members=True,
            move_members=True,
            change_nickname=True,
            manage_nicknames=True
        )
        
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=["bot", "applications.commands"]
        )
        
        embed = discord.Embed(
            title="📨 Invite Me!",
            description=f"[Click here to add me to your server!]({invite_url})",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="Required Permissions",
            value="• Moderate Members\n• Manage Messages\n• Manage Roles\n• Manage Channels\n• View Channels\n• Send Messages",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="help",
        description="Show help menu",
        usage="[command]"
    )
    async def help_command(self, ctx, command: str = None):
        """Help command"""
        if command:
            # Specific command help
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                return await ctx.send(f"❌ Command `{command}` not found.")
            
            embed = discord.Embed(
                title=f"Help: {cmd.name}",
                description=cmd.description or "No description",
                color=discord.Color.blue()
            )
            
            # Usage
            usage = f"{ctx.prefix}{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            # Aliases
            if cmd.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join([f"`{alias}`" for alias in cmd.aliases]),
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        else:
            # General help
            embed = discord.Embed(
                title="📚 Help Menu",
                description=(
                    f"Use `{ctx.prefix}help <command>` for detailed help.\n"
                    f"**Prefix:** `{ctx.prefix}`\n"
                    f"**Total Commands:** {len(self.bot.commands)}"
                ),
                color=discord.Color.blue()
            )
            
            # Group by cog
            cogs = {}
            for cmd in self.bot.commands:
                if cmd.cog:
                    cog_name = cmd.cog.qualified_name
                    if cog_name not in cogs:
                        cogs[cog_name] = []
                    cogs[cog_name].append(cmd)
            
            for cog_name, commands_list in cogs.items():
                if commands_list:
                    cmd_names = [f"`{cmd.name}`" for cmd in commands_list]
                    embed.add_field(
                        name=cog_name,
                        value=" ".join(cmd_names),
                        inline=False
                    )
            
            embed.set_footer(text=f"Bot v{Config.VERSION} • {len(self.bot.commands)} commands")
            await ctx.send(embed=embed)
    
    @commands.command(
        name="poll",
        description="Create a poll",
        usage="<question>"
    )
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, question: str):
        """Poll command"""
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Poll by {ctx.author}")
        
        message = await ctx.send(embed=embed)
        
        # Add reactions
        reactions = ["✅", "❌", "🤷"]
        for reaction in reactions:
            await message.add_reaction(reaction)
    
    @commands.command(
        name="timer",
        description="Set a timer",
        usage="<seconds> [message]"
    )
    async def timer(self, ctx, seconds: int, *, message: str = "Time's up!"):
        """Timer command"""
        if seconds > 3600:
            return await ctx.send("❌ Maximum 1 hour (3600 seconds)")
        if seconds < 5:
            return await ctx.send("❌ Minimum 5 seconds")
        
        msg = await ctx.send(f"⏰ Timer set for {seconds} seconds...")
        
        await asyncio.sleep(seconds)
        
        embed = discord.Embed(
            title="⏰ Timer Finished!",
            description=f"{ctx.author.mention} {message}",
            color=discord.Color.gold()
        )
        
        await msg.edit(embed=embed)
        await ctx.send(content=ctx.author.mention, embed=embed)
    
    @commands.command(
        name="remind",
        description="Set a reminder",
        usage="<time> <message>"
    )
    async def remind(self, ctx, time: str, *, message: str):
        """Reminder command"""
        # Parse time
        time_pattern = re.compile(r'^(\d+)([smhd])$')
        match = time_pattern.match(time.lower())
        
        if not match:
            return await ctx.send("❌ Format: 30s, 5m, 1h, 2d")
        
        amount, unit = match.groups()
        amount = int(amount)
        
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        seconds = amount * multipliers[unit]
        
        if seconds > 604800:  # 7 days
            return await ctx.send("❌ Maximum 7 days")
        
        # Send confirmation
        time_text = f"{amount}{unit}"
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=(
                f"I'll remind you in **{time_text}** about:\n\n"
                f"{message}"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        # Wait and remind
        await asyncio.sleep(seconds)
        
        reminder_embed = discord.Embed(
            title="⏰ Reminder!",
            description=message,
            color=discord.Color.gold()
        )
        
        try:
            await ctx.author.send(embed=reminder_embed)
        except:
            await ctx.send(f"{ctx.author.mention}", embed=reminder_embed)
    
    @commands.command(
        name="weather",
        description="Get weather for a location",
        usage="<city>"
    )
    async def weather(self, ctx, *, city: str):
        """Weather command"""
        # This would use a weather API
        # For now, simulate response
        
        temperatures = {
            "new york": {"temp": "15°C", "condition": "Cloudy"},
            "london": {"temp": "10°C", "condition": "Rainy"},
            "tokyo": {"temp": "20°C", "condition": "Sunny"},
            "sydney": {"temp": "25°C", "condition": "Clear"},
            "paris": {"temp": "12°C", "condition": "Partly Cloudy"}
        }
        
        city_lower = city.lower()
        if city_lower in temperatures:
            data = temperatures[city_lower]
        else:
            # Random data for unknown cities
            temp = random.randint(-10, 35)
            conditions = ["Sunny", "Cloudy", "Rainy", "Snowy", "Stormy"]
            data = {
                "temp": f"{temp}°C",
                "condition": random.choice(conditions)
            }
        
        # Get emoji for condition
        emoji_map = {
            "Sunny": "☀️",
            "Cloudy": "☁️",
            "Rainy": "🌧️",
            "Snowy": "❄️",
            "Stormy": "⛈️",
            "Clear": "✨",
            "Partly Cloudy": "⛅"
        }
        
        emoji = emoji_map.get(data["condition"], "🌤️")
        
        embed = discord.Embed(
            title=f"{emoji} Weather in {city.title()}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Temperature", value=data["temp"], inline=True)
        embed.add_field(name="Condition", value=data["condition"], inline=True)
        embed.add_field(name="Feels Like", value=f"{int(data['temp'][:-2]) + random.randint(-2, 2)}°C", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="translate",
        description="Translate text",
        usage="<language> <text>"
    )
    async def translate(self, ctx, language: str, *, text: str):
        """Translate command"""
        languages = {
            "spanish": "Español",
            "french": "Français",
            "german": "Deutsch",
            "japanese": "日本語",
            "korean": "한국어",
            "chinese": "中文",
            "russian": "Русский",
            "arabic": "العربية"
        }
        
        if language.lower() not in languages:
            return await ctx.send(f"❌ Supported languages: {', '.join(languages.keys())}")
        
        # Simulated translation
        translations = {
            "hello": {
                "spanish": "Hola",
                "french": "Bonjour",
                "german": "Hallo",
                "japanese": "こんにちは",
                "korean": "안녕하세요",
                "chinese": "你好",
                "russian": "Привет",
                "arabic": "مرحبا"
            },
            "thank you": {
                "spanish": "Gracias",
                "french": "Merci",
                "german": "Danke",
                "japanese": "ありがとう",
                "korean": "감사합니다",
                "chinese": "谢谢",
                "russian": "Спасибо",
                "arabic": "شكرا"
            }
        }
        
        text_lower = text.lower()
        if text_lower in translations:
            translated = translations[text_lower][language.lower()]
        else:
            # Simulate translation by adding language code
            translated = f"[{language.upper()}] {text}"
        
        embed = discord.Embed(
            title="🌍 Translation",
            color=discord.Color.green()
        )
        embed.add_field(name="Original", value=text, inline=False)
        embed.add_field(name=f"To {languages[language.lower()]}", value=translated, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="calc",
        description="Calculate expression",
        usage="<expression>"
    )
    async def calc(self, ctx, *, expression: str):
        """Calculator command"""
        try:
            # Remove dangerous characters
            safe_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            
            # Evaluate safely
            result = eval(safe_expr, {"__builtins__": {}}, {})
            
            embed = discord.Embed(
                title="🧮 Calculator",
                color=discord.Color.blue()
            )
            embed.add_field(name="Expression", value=f"`{expression}`", inline=False)
            embed.add_field(name="Result", value=f"`{result}`", inline=False)
            
            await ctx.send(embed=embed)
            
        except:
            await ctx.send("❌ Invalid expression")
    
    @commands.command(
        name="qr",
        description="Generate QR code",
        usage="<text>"
    )
    async def qr(self, ctx, *, text: str):
        """QR code generator"""
        if len(text) > 100:
            return await ctx.send("❌ Text too long (max 100 characters)")
        
        # Generate QR code URL (using external service)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={text}"
        
        embed = discord.Embed(
            title="📱 QR Code",
            description=f"**Text:** {text}",
            color=discord.Color.blue()
        )
        embed.set_image(url=qr_url)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="avatar",
        aliases=["av", "pfp"],
        description="Get user avatar",
        usage="[user]"
    )
    async def avatar(self, ctx, member: discord.Member = None):
        """Avatar command"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=member.color
        )
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Add download links
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.add_field(
            name="🔗 Links",
            value=f"[PNG]({avatar_url}) | [JPG]({avatar_url}) | [WEBP]({avatar_url})",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="serverinfo",
        description="Get server information",
        usage=""
    )
    async def serverinfo(self, ctx):
        """Server info command"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"{guild.name} Information",
            color=discord.Color.blue()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        
        # Members
        online = len([m for m in guild.members if m.status != discord.Status.offline])
        embed.add_field(name="👥 Members", value=f"{guild.member_count} ({online} online)", inline=True)
        embed.add_field(name="🤖 Bots", value=str(len([m for m in guild.members if m.bot])), inline=True)
        
        # Channels
        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        embed.add_field(name="📝 Channels", value=f"{text} Text, {voice} Voice", inline=True)
        
        # Boost
        if guild.premium_tier > 0:
            embed.add_field(
                name="🚀 Boosts",
                value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)",
                inline=True
            )
        
        # Roles
        embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
        
        # Features
        if guild.features:
            features = [f.replace("_", " ").title() for f in guild.features[:3]]
            embed.add_field(name="✨ Features", value=", ".join(features), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="userinfo",
        aliases=["whois"],
        description="Get user information",
        usage="[user]"
    )
    async def userinfo(self, ctx, member: discord.Member = None):
        """User info command"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Information",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Basic info
        embed.add_field(name="👤 Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
        embed.add_field(name="🤖 Bot", value="✅" if member.bot else "❌", inline=True)
        
        # Dates
        embed.add_field(name="📅 Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="📥 Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
        
        # Status
        status_emojis = {
            "online": "🟢",
            "idle": "🟡",
            "dnd": "🔴",
            "offline": "⚫"
        }
        status = str(member.status)
        embed.add_field(name="📊 Status", value=f"{status_emojis.get(status, '⚫')} {status.title()}", inline=True)
        
        # Roles
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            roles_text = " ".join(roles[:5])
            if len(roles) > 5:
                roles_text += f" (+{len(roles) - 5} more)"
            embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="roleinfo",
        description="Get role information",
        usage="<role>"
    )
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Role info command"""
        embed = discord.Embed(
            title=f"{role.name} Information",
            color=role.color
        )
        
        embed.add_field(name="🆔 Role ID", value=str(role.id), inline=True)
        embed.add_field(name="🎨 Color", value=str(role.color), inline=True)
        embed.add_field(name="👥 Members", value=str(len(role.members)), inline=True)
        embed.add_field(name="📊 Position", value=f"#{role.position}", inline=True)
        embed.add_field(name="🏷️ Hoisted", value="✅" if role.hoist else "❌", inline=True)
        embed.add_field(name="🔔 Mentionable", value="✅" if role.mentionable else "❌", inline=True)
        embed.add_field(name="📅 Created", value=role.created_at.strftime("%b %d, %Y"), inline=True)
        
        await ctx.send(embed=embed)

# =========================
# ECONOMY COG (10+ Commands)
# =========================
class Economy(commands.Cog, name="💰 Economy"):
    """Economy system with leveling"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.work_cooldowns = {}
    
    @commands.command(
        name="balance",
        aliases=["bal", "money"],
        description="Check your balance"
    )
    async def balance(self, ctx, member: discord.Member = None):
        """Balance command"""
        member = member or ctx.author
        user_data = self.bot.db.get_user(member.id)
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Balance",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="💵 Wallet", value=f"${user_data['balance']:,}", inline=True)
        embed.add_field(name="🏦 Bank", value=f"${user_data['bank']:,}", inline=True)
        embed.add_field(name="💰 Total", value=f"${user_data['balance'] + user_data['bank']:,}", inline=True)
        embed.add_field(name="⭐ Level", value=str(user_data['level']), inline=True)
        embed.add_field(name="📊 XP", value=f"{user_data['xp']:,}", inline=True)
        embed.add_field(name="👍 Rep", value=str(user_data['reputation']), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="daily",
        description="Claim daily reward"
    )
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx):
        """Daily reward"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        # Calculate streak bonus
        streak = user_data['daily_streak']
        last_daily = user_data['last_daily']
        
        now = datetime.datetime.now()
        if last_daily:
            last_date = datetime.datetime.fromisoformat(last_daily)
            days_diff = (now - last_date).days
            
            if days_diff == 1:
                streak += 1
            elif days_diff > 1:
                streak = 1
        else:
            streak = 1
        
        # Calculate reward
        base_reward = 100
        streak_bonus = streak * 10
        total_reward = base_reward + streak_bonus
        
        # Update user
        new_balance = user_data['balance'] + total_reward
        self.bot.db.update_user(
            ctx.author.id,
            balance=new_balance,
            daily_streak=streak,
            last_daily=now.isoformat()
        )
        
        # Log transaction
        self.bot.db.add_transaction(
            ctx.author.id, total_reward, "daily",
            f"Daily reward (streak: {streak})"
        )
        
        embed = discord.Embed(
            title="🎁 Daily Reward",
            description=(
                f"You claimed **${total_reward:,}**!\n"
                f"• Base: ${base_reward:,}\n"
                f"• Streak bonus: ${streak_bonus:,}\n\n"
                f"**Current streak:** {streak} days\n"
                f"**New balance:** ${new_balance:,}"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="work",
        description="Work to earn money"
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx):
        """Work command"""
        jobs = [
            ("Developer", 100, 200),
            ("Designer", 80, 150),
            ("Writer", 50, 100),
            ("Streamer", 150, 300),
            ("Chef", 60, 120),
            ("Artist", 70, 140),
            ("Engineer", 120, 250),
            ("Doctor", 200, 400),
            ("Teacher", 40, 80),
            ("Driver", 30, 60)
        ]
        
        job, min_pay, max_pay = random.choice(jobs)
        earned = random.randint(min_pay, max_pay)
        
        user_data = self.bot.db.get_user(ctx.author.id)
        new_balance = user_data['balance'] + earned
        
        self.bot.db.update_user(ctx.author.id, balance=new_balance)
        self.bot.db.add_transaction(ctx.author.id, earned, "work", f"Worked as {job}")
        
        embed = discord.Embed(
            title="💼 Work Results",
            description=(
                f"You worked as a **{job}** and earned **${earned:,}**!\n\n"
                f"**New balance:** ${new_balance:,}"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="gamble",
        description="Gamble your money",
        usage="<amount|all|half>"
    )
    async def gamble(self, ctx, amount: str):
        """Gamble command"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        # Parse amount
        if amount.lower() == "all":
            bet = user_data['balance']
        elif amount.lower() == "half":
            bet = user_data['balance'] // 2
        else:
            try:
                bet = int(amount)
                if bet < 1:
                    raise ValueError
            except ValueError:
                return await ctx.send("❌ Amount must be a number, 'all', or 'half'")
        
        # Check balance
        if bet > user_data['balance']:
            return await ctx.send("❌ You don't have enough money!")
        
        # Gamble logic
        win_chance = 0.45  # 45% chance to win
        multiplier = 2.0   # Double your money
        
        if random.random() < win_chance:
            # Win
            winnings = int(bet * multiplier)
            new_balance = user_data['balance'] + winnings
            result = f"🎉 You won **${winnings:,}**!"
            color = discord.Color.green()
            
            self.bot.db.add_transaction(ctx.author.id, winnings, "gamble_win", f"Won gamble")
        else:
            # Lose
            new_balance = user_data['balance'] - bet
            result = f"😢 You lost **${bet:,}**."
            color = discord.Color.red()
            
            self.bot.db.add_transaction(ctx.author.id, -bet, "gamble_loss", f"Lost gamble")
        
        # Update balance
        self.bot.db.update_user(ctx.author.id, balance=new_balance)
        
        embed = discord.Embed(
            title="🎰 Gambling Results",
            description=f"{result}\n**New balance:** ${new_balance:,}",
            color=color
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="deposit",
        description="Deposit money to bank",
        usage="<amount|all>"
    )
    async def deposit(self, ctx, amount: str):
        """Deposit command"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        if amount.lower() == "all":
            amount_num = user_data['balance']
        else:
            try:
                amount_num = int(amount)
                if amount_num < 1:
                    raise ValueError
            except ValueError:
                return await ctx.send("❌ Invalid amount")
        
        if amount_num > user_data['balance']:
            return await ctx.send("❌ You don't have that much money!")
        
        # Update
        new_balance = user_data['balance'] - amount_num
        new_bank = user_data['bank'] + amount_num
        
        self.bot.db.update_user(
            ctx.author.id,
            balance=new_balance,
            bank=new_bank
        )
        
        self.bot.db.add_transaction(
            ctx.author.id, amount_num, "deposit",
            "Deposited to bank"
        )
        
        embed = discord.Embed(
            title="🏦 Deposit Successful",
            description=(
                f"Deposited **${amount_num:,}** to your bank.\n\n"
                f"**Wallet:** ${new_balance:,}\n"
                f"**Bank:** ${new_bank:,}"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="withdraw",
        description="Withdraw money from bank",
        usage="<amount|all>"
    )
    async def withdraw(self, ctx, amount: str):
        """Withdraw command"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        if amount.lower() == "all":
            amount_num = user_data['bank']
        else:
            try:
                amount_num = int(amount)
                if amount_num < 1:
                    raise ValueError
            except ValueError:
                return await ctx.send("❌ Invalid amount")
        
        if amount_num > user_data['bank']:
            return await ctx.send("❌ You don't have that much in your bank!")
        
        # Update
        new_balance = user_data['balance'] + amount_num
        new_bank = user_data['bank'] - amount_num
        
        self.bot.db.update_user(
            ctx.author.id,
            balance=new_balance,
            bank=new_bank
        )
        
        self.bot.db.add_transaction(
            ctx.author.id, amount_num, "withdraw",
            "Withdrew from bank"
        )
        
        embed = discord.Embed(
            title="🏦 Withdrawal Successful",
            description=(
                f"Withdrew **${amount_num:,}** from your bank.\n\n"
                f"**Wallet:** ${new_balance:,}\n"
                f"**Bank:** ${new_bank:,}"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="pay",
        description="Pay another user",
        usage="<user> <amount>"
    )
    async def pay(self, ctx, member: discord.Member, amount: int):
        """Pay command"""
        if amount < 1:
            return await ctx.send("❌ Amount must be positive")
        
        if member == ctx.author:
            return await ctx.send("❌ You can't pay yourself")
        
        if member.bot:
            return await ctx.send("❌ You can't pay bots")
        
        # Check sender's balance
        sender_data = self.bot.db.get_user(ctx.author.id)
        if amount > sender_data['balance']:
            return await ctx.send("❌ You don't have enough money!")
        
        # Get receiver data
        receiver_data = self.bot.db.get_user(member.id)
        
        # Update balances
        sender_new_balance = sender_data['balance'] - amount
        receiver_new_balance = receiver_data['balance'] + amount
        
        self.bot.db.update_user(ctx.author.id, balance=sender_new_balance)
        self.bot.db.update_user(member.id, balance=receiver_new_balance)
        
        # Log transactions
        self.bot.db.add_transaction(
            ctx.author.id, -amount, "payment_sent",
            f"Paid {member.name}"
        )
        
        self.bot.db.add_transaction(
            member.id, amount, "payment_received",
            f"Received from {ctx.author.name}"
        )
        
        embed = discord.Embed(
            title="💰 Payment Sent",
            description=(
                f"**From:** {ctx.author.mention}\n"
                f"**To:** {member.mention}\n"
                f"**Amount:** ${amount:,}\n\n"
                f"Your new balance: **${sender_new_balance:,}**"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="leaderboard",
        aliases=["lb", "top"],
        description="Show economy leaderboard",
        usage="[page=1]"
    )
    async def leaderboard(self, ctx, page: int = 1):
        """Leaderboard command"""
        # Get top users by total wealth
        self.bot.db.cursor.execute('''
            SELECT user_id, balance + bank as total_wealth 
            FROM users 
            ORDER BY total_wealth DESC 
            LIMIT 10 OFFSET ?
        ''', ((page - 1) * 10,))
        
        results = self.bot.db.cursor.fetchall()
        
        if not results:
            return await ctx.send("❌ No users found.")
        
        embed = discord.Embed(
            title="🏆 Economy Leaderboard",
            color=discord.Color.gold()
        )
        
        for i, (user_id, wealth) in enumerate(results, 1):
            try:
                user = await self.bot.fetch_user(user_id)
                username = user.name
            except:
                username = f"User {user_id}"
            
            embed.add_field(
                name=f"#{i + (page-1)*10}. {username}",
                value=f"${wealth:,}",
                inline=False
            )
        
        embed.set_footer(text=f"Page {page}")
        await ctx.send(embed=embed)
    
    @commands.command(
        name="shop",
        description="View shop items",
        usage=""
    )
    async def shop(self, ctx):
        """Shop command"""
        items = [
            {"name": "🎨 Custom Color", "price": 5000, "description": "Custom role color for 7 days"},
            {"name": "🌟 VIP Badge", "price": 10000, "description": "Special role with perks"},
            {"name": "💎 Diamond Package", "price": 25000, "description": "50,000 coins + VIP"},
            {"name": "🎁 Mystery Box", "price": 1000, "description": "Random reward (100-10,000 coins)"},
            {"name": "🔧 Profile Customization", "price": 3000, "description": "Custom profile background"},
            {"name": "🎵 Music Request", "price": 500, "description": "Priority music requests for 24h"},
            {"name": "🛡️ Insurance", "price": 2000, "description": "Protect your coins for 30 days"},
            {"name": "⚡ XP Boost", "price": 1500, "description": "2x XP for 24 hours"}
        ]
        
        embed = discord.Embed(
            title="🛒 Shop",
            color=discord.Color.gold()
        )
        
        for item in items:
            embed.add_field(
                name=f"{item['name']} - ${item['price']:,}",
                value=item['description'],
                inline=False
            )
        
        embed.set_footer(text=f"Use {ctx.prefix}buy <item> to purchase")
        await ctx.send(embed=embed)
    
    @commands.command(
        name="buy",
        description="Buy item from shop",
        usage="<item>"
    )
    async def buy(self, ctx, *, item_name: str):
        """Buy command"""
        user_data = self.bot.db.get_user(ctx.author.id)
        
        # Check item
        items = {
            "custom color": {"price": 5000, "type": "color"},
            "vip badge": {"price": 10000, "type": "role"},
            "diamond package": {"price": 25000, "type": "package"},
            "mystery box": {"price": 1000, "type": "box"},
            "profile customization": {"price": 3000, "type": "profile"},
            "music request": {"price": 500, "type": "music"},
            "insurance": {"price": 2000, "type": "insurance"},
            "xp boost": {"price": 1500, "type": "boost"}
        }
        
        if item_name.lower() not in items:
            return await ctx.send(f"❌ Item not found. Use `{ctx.prefix}shop` to see available items.")
        
        item = items[item_name.lower()]
        
        if user_data['balance'] < item['price']:
            return await ctx.send(f"❌ You need ${item['price']:,} to buy this!")
        
        # Process purchase
        new_balance = user_data['balance'] - item['price']
        self.bot.db.update_user(ctx.author.id, balance=new_balance)
        
        # Give item benefits
        if item['type'] == "box":
            reward = random.randint(100, 10000)
            new_balance += reward
            self.bot.db.update_user(ctx.author.id, balance=new_balance)
            
            embed = discord.Embed(
                title="🎁 Mystery Box Opened!",
                description=(
                    f"You found **${reward:,}** inside!\n\n"
                    f"**New balance:** ${new_balance:,}"
                ),
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🛒 Purchase Successful",
                description=(
                    f"Bought **{item_name.title()}** for ${item['price']:,}!\n\n"
                    f"**New balance:** ${new_balance:,}"
                ),
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)

# =========================
# MUSIC COG (5+ Commands)
# =========================
class Music(commands.Cog, name="🎵 Music"):
    """Music player commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
    
    @commands.command(
        name="play",
        description="Play music",
        usage="<song>"
    )
    async def play(self, ctx, *, query: str):
        """Play command"""
        if not ctx.author.voice:
            return await ctx.send("❌ You need to be in a voice channel!")
        
        await self.bot.music.play_song(ctx, query)
    
    @commands.command(
        name="stop",
        description="Stop music",
        usage=""
    )
    async def stop(self, ctx):
        """Stop command"""
        await self.bot.music.stop(ctx)
    
    @commands.command(
        name="skip",
        description="Skip current song",
        usage=""
    )
    async def skip(self, ctx):
        """Skip command"""
        if ctx.guild.id in self.bot.music.queues and self.bot.music.queues[ctx.guild.id]:
            self.bot.music.queues[ctx.guild.id].pop(0)
            await ctx.send("⏭️ Skipped current song.")
            
            if self.bot.music.queues[ctx.guild.id]:
                await self.bot.music._play_next(ctx)
        else:
            await ctx.send("❌ No songs in queue.")
    
    @commands.command(
        name="queue",
        description="Show music queue",
        usage=""
    )
    async def queue(self, ctx):
        """Queue command"""
        if ctx.guild.id not in self.bot.music.queues or not self.bot.music.queues[ctx.guild.id]:
            return await ctx.send("❌ Queue is empty.")
        
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color(Config.COLORS["music"])
        )
        
        for i, song in enumerate(self.bot.music.queues[ctx.guild.id][:10], 1):
            embed.add_field(
                name=f"{i}. {song['title']}",
                value=f"Duration: {song['duration']}",
                inline=False
            )
        
        total_songs = len(self.bot.music.queues[ctx.guild.id])
        if total_songs > 10:
            embed.set_footer(text=f"And {total_songs - 10} more songs...")
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="nowplaying",
        aliases=["np"],
        description="Show currently playing",
        usage=""
    )
    async def nowplaying(self, ctx):
        """Now playing command"""
        if ctx.guild.id not in self.bot.music.now_playing:
            return await ctx.send("❌ Nothing is playing.")
        
        song = self.bot.music.now_playing[ctx.guild.id]
        
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"**{song['title']}**",
            color=discord.Color(Config.COLORS["music"])
        )
        embed.add_field(name="Duration", value=song["duration"])
        
        await ctx.send(embed=embed)

# =========================
# EVENTS COG
# =========================
class Events(commands.Cog):
    """Event handlers"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """On ready event"""
        logger.info(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        logger.info(f"Connected to {len(self.bot.guilds)} guilds")
        logger.info("=" * 50)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """On message event"""
        if message.author.bot:
            return
        
        self.bot.message_count += 1
        
        # Give XP for messages
        if isinstance(message.channel, discord.TextChannel):
            user_data = self.bot.db.get_user(message.author.id)
            
            # Give random XP (1-5)
            xp_gain = random.randint(1, 5)
            new_xp = user_data['xp'] + xp_gain
            
            # Check level up
            current_level = user_data['level']
            xp_needed = current_level * 100
            
            if new_xp >= xp_needed:
                new_level = current_level + 1
                new_xp = new_xp - xp_needed
                
                # Give level up reward
                reward = new_level * 100
                new_balance = user_data['balance'] + reward
                
                self.bot.db.update_user(
                    message.author.id,
                    xp=new_xp,
                    level=new_level,
                    balance=new_balance
                )
                
                # Send level up message
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=(
                        f"**{message.author.mention} reached level {new_level}!**\n"
                        f"Reward: **${reward:,}**\n\n"
                        f"**New balance:** ${new_balance:,}"
                    ),
                    color=discord.Color.green()
                )
                await message.channel.send(embed=embed)
            else:
                self.bot.db.update_user(message.author.id, xp=new_xp)
        
        # AI response for questions
        if self.bot.user.mentioned_in(message) and not message.content.startswith(self.bot.command_prefix):
            async with message.channel.typing():
                response = await self.bot.ai.ask(
                    message.author.id,
                    message.content,
                    f"You are in a Discord server. The user {message.author.name} mentioned you."
                )
                
                if response:
                    await message.reply(response)
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """On command event"""
        self.bot.command_count += 1
        logger.info(f"Command: {ctx.command} by {ctx.author} in {ctx.guild}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Error handling"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        elif isinstance(error, commands.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(f"❌ Missing permissions: {missing}")
        
        elif isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(f"❌ I need permissions: {missing}")
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: {error.param.name}")
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument")
        
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
        
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You can't use this command")
        
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("❌ An error occurred")

# =========================
# WEB DASHBOARD
# =========================
import aiohttp.web
import json

class WebDashboard:
    """Web dashboard for moderation"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.app = aiohttp.web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/style.css', self.handle_css)
        self.app.router.add_get('/script.js', self.handle_js)
        self.app.router.add_post('/login', self.handle_login)
        self.app.router.add_post('/api/commands', self.handle_api_commands)
        self.app.router.add_post('/api/execute', self.handle_api_execute)
        self.app.router.add_get('/api/stats', self.handle_api_stats)
    
    async def handle_index(self, request):
        """Serve index.html"""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Discord Bot Dashboard</title>
            <link rel="stylesheet" href="/style.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <div id="app">
                <!-- Content loaded by JavaScript -->
            </div>
            <script src="/script.js"></script>
        </body>
        </html>
        """
        return aiohttp.web.Response(text=html, content_type='text/html')
    
    async def handle_css(self, request):
        """Serve CSS"""
        css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        /* Add your CSS here */
        """
        return aiohttp.web.Response(text=css, content_type='text/css')
    
    async def handle_js(self, request):
        """Serve JavaScript"""
        js = """
        // Dashboard JavaScript
        console.log('Dashboard loaded');
        """
        return aiohttp.web.Response(text=js, content_type='application/javascript')
    
    async def handle_login(self, request):
        """Handle login"""
        data = await request.json()
        password = data.get('password', '')
        
        if password == Config.DASHBOARD_PASSWORD:
            return aiohttp.web.json_response({'success': True})
        else:
            return aiohttp.web.json_response({'success': False}, status=401)
    
    async def handle_api_commands(self, request):
        """Get commands list"""
        commands_list = []
        for cmd in self.bot.commands:
            if cmd.cog and cmd.cog.qualified_name == "🔨 Moderation":
                commands_list.append({
                    'name': cmd.name,
                    'description': cmd.description or 'No description',
                    'usage': cmd.signature or ''
                })
        
        return aiohttp.web.json_response(commands_list)
    
    async def handle_api_execute(self, request):
        """Execute command"""
        data = await request.json()
        # This would execute commands via the bot
        return aiohttp.web.json_response({'success': True})
    
    async def handle_api_stats(self, request):
        """Get bot stats"""
        stats = {
            'guilds': len(self.bot.guilds),
            'users': self.bot.db.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'commands': self.bot.command_count,
            'uptime': str(datetime.datetime.now() - self.bot.start_time)
        }
        return aiohttp.web.json_response(stats)
    
    async def start(self):
        """Start web server"""
        runner = aiohttp.web.AppRunner(self.app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, Config.DASHBOARD_HOST, Config.DASHBOARD_PORT)
        await site.start()
        logger.info(f"Dashboard running on http://{Config.DASHBOARD_HOST}:{Config.DASHBOARD_PORT}")

# =========================
# MAIN FUNCTION
# =========================
async def main():
    """Main function"""
    # Check for token
    if not Config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment!")
        return
    
    # Create bot
    bot = DiscordBot()
    
    # Create web dashboard
    dashboard = WebDashboard(bot)
    
    # Start bot and dashboard
    try:
        # Start dashboard in background
        asyncio.create_task(dashboard.start())
        
        # Start bot
        await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"Error: {e}")
        await bot.close()

if __name__ == "__main__":
    # Create directories
    os.makedirs("data/backups", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Run bot
    asyncio.run(main())
