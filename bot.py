"""
===========================================
DISCORD BOT v2.0 - Complete Rewrite
===========================================
Features:
- Advanced moderation with whitelist system
- 30+ fun games & interactive commands
- Groq AI integration for smart responses
- Persistent storage with JSON backup
- Role-based permissions & logging
- Beautiful embeds & UI components
===========================================
"""

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import aiohttp
import json
import os
import random
import datetime
import logging
from typing import Optional, List, Dict, Union
from enum import Enum
import re
import math

# =========================
# CONFIGURATION
# =========================
class Config:
    PREFIX = "!"
    VERSION = "2.0.0"
    OWNER_IDS = [1307042499898118246]  # Add your ID(s)
    SUPPORT_SERVER = "https://discord.gg/example"
    GITHUB_REPO = "https://github.com/yourusername/yourbot"
    DEFAULT_COOLDOWN = 3  # seconds
    
    # Colors
    COLORS = {
        "success": 0x2ecc71,
        "error": 0xe74c3c,
        "warning": 0xf39c12,
        "info": 0x3498db,
        "moderation": 0xe67e22,
        "fun": 0x9b59b6
    }

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DiscordBot')

# =========================
# DATA MANAGER
# =========================
class DataManager:
    """Handles all data persistence with backup system"""
    
    def __init__(self):
        self.data_dir = "data/"
        self.backup_dir = "data/backups/"
        self.data_file = "data/bot_data.json"
        self.ensure_dirs()
        self.data = self.load_data()
        
    def ensure_dirs(self):
        """Create necessary directories"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs("logs/", exist_ok=True)
        
    def load_data(self) -> dict:
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info("Data loaded successfully")
                return data
        except Exception as e:
            logger.error(f"Error loading data: {e}")
        
        # Return default data structure
        return {
            "guilds": {},
            "users": {},
            "whitelist": [],
            "blacklist": [],
            "mod_notes": {},
            "temp_bans": {},
            "temp_mutes": {},
            "economy": {},
            "stats": {
                "commands_used": 0,
                "messages_processed": 0,
                "start_time": datetime.datetime.now().isoformat()
            }
        }
    
    def save_data(self):
        """Save data with backup"""
        try:
            # Create backup
            if os.path.exists(self.data_file):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{self.backup_dir}backup_{timestamp}.json"
                import shutil
                shutil.copy2(self.data_file, backup_file)
            
            # Save current data
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            
            # Keep only last 10 backups
            backups = sorted(os.listdir(self.backup_dir))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    os.remove(f"{self.backup_dir}{old_backup}")
                    
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def get_guild_settings(self, guild_id: int) -> dict:
        """Get or create guild settings"""
        guild_id = str(guild_id)
        if guild_id not in self.data["guilds"]:
            self.data["guilds"][guild_id] = {
                "prefix": Config.PREFIX,
                "mod_log_channel": None,
                "welcome_channel": None,
                "mute_role": None,
                "auto_mod": False,
                "welcome_message": "Welcome {user} to {server}!",
                "command_stats": {},
                "roles": {}
            }
        return self.data["guilds"][guild_id]
    
    def update_command_stats(self, guild_id: int, command_name: str):
        """Update command usage statistics"""
        guild_id = str(guild_id)
        guild_data = self.get_guild_settings(guild_id)
        
        if "command_stats" not in guild_data:
            guild_data["command_stats"] = {}
        
        if command_name not in guild_data["command_stats"]:
            guild_data["command_stats"][command_name] = 0
        
        guild_data["command_stats"][command_name] += 1
        self.data["stats"]["commands_used"] += 1

# =========================
# EMBED BUILDER
# =========================
class EmbedFactory:
    """Factory for creating beautiful embeds"""
    
    @staticmethod
    def create(
        title: str = "",
        description: str = "",
        color: discord.Color = None,
        **kwargs
    ) -> discord.Embed:
        """Create a standard embed"""
        if color is None:
            color = discord.Color(Config.COLORS["info"])
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now()
        )
        
        if "author" in kwargs:
            embed.set_author(**kwargs["author"])
        
        if "thumbnail" in kwargs:
            embed.set_thumbnail(url=kwargs["thumbnail"])
        
        if "image" in kwargs:
            embed.set_image(url=kwargs["image"])
        
        if "footer" in kwargs:
            embed.set_footer(text=kwargs["footer"])
        else:
            embed.set_footer(text=f"Bot v{Config.VERSION}")
        
        if "fields" in kwargs:
            for name, value, inline in kwargs["fields"]:
                embed.add_field(name=name, value=value, inline=inline)
        
        return embed
    
    @staticmethod
    def success(description: str, title: str = "✅ Success") -> discord.Embed:
        return EmbedFactory.create(
            title=title,
            description=description,
            color=discord.Color(Config.COLORS["success"])
        )
    
    @staticmethod
    def error(description: str, title: str = "❌ Error") -> discord.Embed:
        return EmbedFactory.create(
            title=title,
            description=description,
            color=discord.Color(Config.COLORS["error"])
        )
    
    @staticmethod
    def warning(description: str, title: str = "⚠️ Warning") -> discord.Embed:
        return EmbedFactory.create(
            title=title,
            description=description,
            color=discord.Color(Config.COLORS["warning"])
        )
    
    @staticmethod
    def moderation(description: str, title: str = "🔨 Moderation") -> discord.Embed:
        return EmbedFactory.create(
            title=title,
            description=description,
            color=discord.Color(Config.COLORS["moderation"])
        )
    
    @staticmethod
    def fun(description: str, title: str = "🎮 Fun") -> discord.Embed:
        return EmbedFactory.create(
            title=title,
            description=description,
            color=discord.Color(Config.COLORS["fun"])
        )

# =========================
# PERMISSION SYSTEM
# =========================
class PermissionLevel(Enum):
    EVERYONE = 0
    MEMBER = 1
    MODERATOR = 2
    ADMIN = 3
    OWNER = 4

class PermissionManager:
    """Advanced permission management system"""
    
    def __init__(self, data_manager: DataManager):
        self.data = data_manager
        
    def get_user_level(self, user: discord.Member, guild: discord.Guild) -> PermissionLevel:
        """Get user's permission level"""
        user_id = str(user.id)
        
        # Check if owner
        if user.id in Config.OWNER_IDS:
            return PermissionLevel.OWNER
        
        # Check if blacklisted
        if user_id in self.data.data["blacklist"]:
            return PermissionLevel.EVERYONE
        
        # Check if admin in guild
        if user.guild_permissions.administrator:
            return PermissionLevel.ADMIN
        
        # Check moderator permissions
        if any([
            user.guild_permissions.manage_messages,
            user.guild_permissions.kick_members,
            user.guild_permissions.ban_members,
            user.guild_permissions.manage_channels
        ]):
            return PermissionLevel.MODERATOR
        
        # Check whitelist
        if user_id in self.data.data["whitelist"]:
            return PermissionLevel.MODERATOR
        
        return PermissionLevel.MEMBER
    
    def has_permission(self, user: discord.Member, required_level: PermissionLevel, guild: discord.Guild) -> bool:
        """Check if user has required permission"""
        user_level = self.get_user_level(user, guild)
        return user_level.value >= required_level.value

# =========================
# AI SERVICE
# =========================
class AIService:
    """Groq AI Integration"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.session = None
        self.models = ["mixtral-8x7b-32768", "llama2-70b-4096"]
        
    async def initialize(self):
        """Initialize AI service"""
        self.session = aiohttp.ClientSession()
        
    async def ask(self, question: str, context: str = "", max_tokens: int = 200) -> str:
        """Ask Groq AI a question"""
        if not self.api_key:
            return "🤖 AI service is currently unavailable. Please configure GROQ_API_KEY."
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.models[0],
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful Discord bot assistant. {context}"
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "temperature": 0.7,
                "max_tokens": max_tokens,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            async with self.session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=15
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status == 401:
                    return "❌ Invalid API key. Please check your GROQ_API_KEY."
                elif response.status == 429:
                    return "⚠️ Rate limit exceeded. Please try again later."
                else:
                    return f"🔧 API Error: {response.status}"
                    
        except asyncio.TimeoutError:
            return "⏰ The AI service is taking too long to respond."
        except Exception as e:
            logger.error(f"AI Service Error: {e}")
            return "❌ An error occurred while processing your request."
    
    async def close(self):
        """Cleanup AI service"""
        if self.session:
            await self.session.close()

# =========================
# MODERATION SYSTEM
# =========================
class ModerationService:
    """Complete moderation system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mute_tasks = {}
        self.ban_tasks = {}
        
    async def log_action(
        self,
        guild: discord.Guild,
        action: str,
        moderator: discord.Member,
        target: Union[discord.Member, discord.User],
        reason: str = "No reason provided",
        duration: str = None
    ):
        """Log moderation action to designated channel"""
        guild_settings = self.bot.data.get_guild_settings(guild.id)
        log_channel_id = guild_settings.get("mod_log_channel")
        
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = EmbedFactory.moderation(
            f"**Action:** {action}\n"
            f"**Moderator:** {moderator.mention} (`{moderator.id}`)\n"
            f"**Target:** {target.mention if hasattr(target, 'mention') else target} (`{target.id}`)\n"
            f"**Reason:** {reason}\n"
            f"**Duration:** {duration or 'Permanent'}\n"
            f"**Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await log_channel.send(embed=embed)
    
    async def create_mute_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Create mute role if it doesn't exist"""
        mute_role = discord.utils.get(guild.roles, name="Muted")
        
        if not mute_role:
            try:
                # Create role
                mute_role = await guild.create_role(
                    name="Muted",
                    color=discord.Color.dark_gray(),
                    reason="Mute role for moderation",
                    permissions=discord.Permissions.none()
                )
                
                # Apply permissions to all channels
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            add_reactions=False,
                            connect=False,
                            speak=False
                        )
                    except:
                        continue
                
                logger.info(f"Created mute role in {guild.name}")
                return mute_role
                
            except discord.Forbidden:
                logger.error(f"No permission to create mute role in {guild.name}")
                return None
        
        return mute_role
    
    async def temp_mute(
        self,
        guild: discord.Guild,
        member: discord.Member,
        duration: int,  # in minutes
        moderator: discord.Member,
        reason: str = "No reason provided"
    ):
        """Temporarily mute a member"""
        mute_role = await self.create_mute_role(guild)
        if not mute_role:
            return False
        
        await member.add_roles(mute_role, reason=f"Muted by {moderator}: {reason}")
        
        # Schedule unmute
        task_id = f"{guild.id}_{member.id}"
        self.mute_tasks[task_id] = asyncio.create_task(
            self._schedule_unmute(guild.id, member.id, duration, mute_role.id)
        )
        
        # Store in data
        self.bot.data.data["temp_mutes"][task_id] = {
            "unmute_time": (datetime.datetime.now() + datetime.timedelta(minutes=duration)).isoformat(),
            "moderator": moderator.id,
            "reason": reason
        }
        self.bot.data.save_data()
        
        # Log action
        await self.log_action(
            guild, "Temp Mute", moderator, member, reason, f"{duration} minutes"
        )
        
        return True
    
    async def _schedule_unmute(self, guild_id: int, user_id: int, minutes: int, role_id: int):
        """Schedule automatic unmute"""
        await asyncio.sleep(minutes * 60)
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        mute_role = guild.get_role(role_id)
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role, reason="Temporary mute expired")
        
        # Cleanup
        task_id = f"{guild_id}_{user_id}"
        if task_id in self.mute_tasks:
            del self.mute_tasks[task_id]
        
        if task_id in self.bot.data.data["temp_mutes"]:
            del self.bot.data.data["temp_mutes"][task_id]
            self.bot.data.save_data()
    
    async def check_role_hierarchy(
        self,
        guild: discord.Guild,
        moderator: discord.Member,
        target: discord.Member
    ) -> bool:
        """Check if moderator can act on target based on role hierarchy"""
        if moderator == guild.owner:
            return True
        
        if target == guild.owner:
            return False
        
        return moderator.top_role > target.top_role

# =========================
# MAIN BOT CLASS
# =========================
class DiscordBot(commands.Bot):
    """Main bot class"""
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions(
                roles=False,
                everyone=False,
                users=True
            )
        )
        
        # Initialize components
        self.data = DataManager()
        self.permissions = PermissionManager(self.data)
        self.moderation = ModerationService(self)
        self.ai = AIService()
        
        # Bot stats
        self.start_time = datetime.datetime.now()
        self.command_count = 0
        self.message_count = 0
        
        # Cooldowns
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 2.0, commands.BucketType.user)
        
    async def get_prefix(self, message: discord.Message) -> str:
        """Get prefix for guild"""
        if not message.guild:
            return Config.PREFIX
        
        guild_settings = self.data.get_guild_settings(message.guild.id)
        return guild_settings.get("prefix", Config.PREFIX)
    
    async def setup_hook(self):
        """Setup hook - runs on startup"""
        logger.info("Starting bot setup...")
        
        # Initialize AI service
        await self.ai.initialize()
        
        # Load cogs
        await self.load_cogs()
        
        # Start background tasks
        self.background_tasks.start()
        self.update_status.start()
        
        # Sync application commands
        await self.tree.sync()
        
        logger.info("Bot setup complete!")
    
    async def load_cogs(self):
        """Load all cogs"""
        # Create cog instances
        self.add_cog(ModerationCog(self))
        self.add_cog(FunCog(self))
        self.add_cog(InfoCog(self))
        self.add_cog(UtilityCog(self))
        self.add_cog(EconomyCog(self))
        self.add_cog(EventsCog(self))
        
        logger.info("All cogs loaded")
    
    @tasks.loop(minutes=5)
    async def background_tasks(self):
        """Background maintenance tasks"""
        await self.cleanup_temp_actions()
        await self.update_stats()
    
    @tasks.loop(minutes=2)
    async def update_status(self):
        """Update bot status"""
        statuses = [
            discord.Activity(type=discord.ActivityType.playing, name=f"on {len(self.guilds)} servers"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{self.command_count} commands"),
            discord.Activity(type=discord.ActivityType.listening, name="your commands"),
            discord.Activity(type=discord.ActivityType.competing, name="with other bots")
        ]
        
        await self.change_presence(
            activity=random.choice(statuses),
            status=discord.Status.online
        )
    
    async def cleanup_temp_actions(self):
        """Clean up expired temp actions"""
        current_time = datetime.datetime.now()
        
        # Check temp mutes
        for task_id, mute_data in list(self.data.data["temp_mutes"].items()):
            unmute_time = datetime.datetime.fromisoformat(mute_data["unmute_time"])
            if current_time >= unmute_time:
                guild_id, user_id = map(int, task_id.split("_"))
                await self.moderation._schedule_unmute(guild_id, user_id, 0, 0)
    
    async def update_stats(self):
        """Update bot statistics"""
        self.data.data["stats"]["uptime"] = str(datetime.datetime.now() - self.start_time)
        self.data.data["stats"]["guild_count"] = len(self.guilds)
        self.data.save_data()
    
    async def close(self):
        """Cleanup on shutdown"""
        await self.ai.close()
        self.data.save_data()
        await super().close()
        
        logger.info("Bot shutdown complete")

# =========================
# MODERATION COG
# =========================
class ModerationCog(commands.Cog, name="🔨 Moderation"):
    """Moderation commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.logger = logging.getLogger("ModerationCog")
    
    @commands.command(
        name="kick",
        description="Kick a member from the server",
        usage="<member> [reason]"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member"""
        if not await self.bot.moderation.check_role_hierarchy(ctx.guild, ctx.author, member):
            await ctx.send(embed=EmbedFactory.error("You cannot kick someone with equal or higher role."))
            return
        
        try:
            await member.send(f"You have been kicked from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
        
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=EmbedFactory.success(f"Kicked {member.mention}"))
        
        await self.bot.moderation.log_action(
            ctx.guild, "Kick", ctx.author, member, reason
        )
    
    @commands.command(
        name="ban",
        description="Ban a member from the server",
        usage="<member> [reason]"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member"""
        if not await self.bot.moderation.check_role_hierarchy(ctx.guild, ctx.author, member):
            await ctx.send(embed=EmbedFactory.error("You cannot ban someone with equal or higher role."))
            return
        
        try:
            await member.send(f"You have been banned from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
        
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
        await ctx.send(embed=EmbedFactory.success(f"Banned {member.mention}"))
        
        await self.bot.moderation.log_action(
            ctx.guild, "Ban", ctx.author, member, reason
        )
    
    @commands.command(
        name="mute",
        description="Mute a member",
        usage="<member> [duration in minutes] [reason]"
    )
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: int = 60, *, reason: str = "No reason provided"):
        """Mute a member"""
        if not await self.bot.moderation.check_role_hierarchy(ctx.guild, ctx.author, member):
            await ctx.send(embed=EmbedFactory.error("You cannot mute someone with equal or higher role."))
            return
        
        success = await self.bot.moderation.temp_mute(
            ctx.guild, member, duration, ctx.author, reason
        )
        
        if success:
            await ctx.send(embed=EmbedFactory.success(
                f"Muted {member.mention} for {duration} minutes"
            ))
        else:
            await ctx.send(embed=EmbedFactory.error(
                "Failed to mute member. Check bot permissions."
            ))
    
    @commands.command(
        name="unmute",
        description="Unmute a member",
        usage="<member>"
    )
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send(embed=EmbedFactory.error("No mute role found"))
            return
        
        if mute_role not in member.roles:
            await ctx.send(embed=EmbedFactory.error(f"{member.mention} is not muted"))
            return
        
        await member.remove_roles(mute_role, reason=f"Unmuted by {ctx.author}")
        await ctx.send(embed=EmbedFactory.success(f"Unmuted {member.mention}"))
    
    @commands.command(
        name="clear",
        aliases=["purge"],
        description="Clear messages",
        usage="[amount=10]"
    )
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        """Clear messages"""
        if amount > 100:
            await ctx.send(embed=EmbedFactory.error("You can only delete up to 100 messages at once."))
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=EmbedFactory.success(f"Deleted {len(deleted) - 1} messages."))
        await asyncio.sleep(3)
        await msg.delete()
    
    @commands.command(
        name="lock",
        description="Lock the current channel"
    )
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Lock a channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=EmbedFactory.success(f"🔒 {ctx.channel.mention} has been locked."))
    
    @commands.command(
        name="unlock",
        description="Unlock the current channel"
    )
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlock a channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=EmbedFactory.success(f"🔓 {ctx.channel.mention} has been unlocked."))
    
    @commands.command(
        name="slowmode",
        description="Set slowmode for the channel",
        usage="[seconds]"
    )
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set slowmode"""
        if seconds < 0 or seconds > 21600:
            await ctx.send(embed=EmbedFactory.error("Slowmode must be between 0 and 21600 seconds (6 hours)"))
            return
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send(embed=EmbedFactory.success("Slowmode disabled"))
        else:
            await ctx.send(embed=EmbedFactory.success(f"Slowmode set to {seconds} seconds"))

# =========================
# FUN COG
# =========================
class FunCog(commands.Cog, name="🎮 Fun & Games"):
    """Fun and game commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.games = {}
    
    @commands.command(
        name="coinflip",
        aliases=["flip", "coin"],
        description="Flip a coin"
    )
    async def coinflip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        
        embed = EmbedFactory.fun(
            f"The coin spun in the air...",
            "🪙 Coin Flip"
        )
        embed.add_field(name="Result", value=f"**{result}**!", inline=False)
        
        message = await ctx.send(embed=embed)
        
        # Add reactions for fun
        await message.add_reaction("🪙")
        await message.add_reaction("👍")
    
    @commands.command(
        name="dice",
        aliases=["roll"],
        description="Roll dice",
        usage="[dice=1d6]"
    )
    async def dice(self, ctx, dice: str = "1d6"):
        """Roll dice in NdN format"""
        try:
            if "d" not in dice:
                raise ValueError
            
            rolls, limit = map(int, dice.split("d"))
            
            if rolls > 20 or limit > 100:
                await ctx.send(embed=EmbedFactory.error("Maximum: 20 dice with 100 sides each"))
                return
            
            results = [random.randint(1, limit) for _ in range(rolls)]
            total = sum(results)
            
            embed = EmbedFactory.fun(
                f"Rolling {dice}...",
                "🎲 Dice Roll"
            )
            
            if rolls <= 10:
                embed.add_field(name="Results", value=", ".join(map(str, results)), inline=False)
            
            embed.add_field(name="Total", value=str(total), inline=True)
            embed.add_field(name="Average", value=f"{total/rolls:.2f}", inline=True)
            
            if rolls == 1:
                embed.add_field(name="Max", value=str(limit), inline=True)
            
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send(embed=EmbedFactory.error("Format must be NdN (e.g., 2d6, 1d20)"))
    
    @commands.command(
        name="rps",
        description="Play Rock Paper Scissors",
        usage="<rock|paper|scissors>"
    )
    async def rps(self, ctx, choice: str):
        """Rock Paper Scissors"""
        choices = {
            "rock": "🪨",
            "paper": "📄",
            "scissors": "✂️"
        }
        
        choice = choice.lower()
        if choice not in choices:
            await ctx.send(embed=EmbedFactory.error("Please choose rock, paper, or scissors!"))
            return
        
        bot_choice = random.choice(list(choices.keys()))
        
        # Determine winner
        if choice == bot_choice:
            result = "It's a tie! 🤝"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "You win! 🎉"
        else:
            result = "I win! 😎"
        
        embed = EmbedFactory.fun(
            f"**You:** {choices[choice]} {choice.title()}\n"
            f"**Bot:** {choices[bot_choice]} {bot_choice.title()}\n\n"
            f"**{result}**",
            "✂️ Rock Paper Scissors"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="8ball",
        description="Ask the magic 8-ball",
        usage="<question>"
    )
    async def eightball(self, ctx, *, question: str):
        """Magic 8-ball"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        
        embed = EmbedFactory.fun(
            f"**Question:** {question}\n"
            f"**Answer:** {random.choice(responses)}",
            "🎱 Magic 8-Ball"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="choose",
        description="Choose between options",
        usage="<option1> or <option2> or ..."
    )
    async def choose(self, ctx, *, options: str):
        """Choose between options"""
        if " or " not in options:
            await ctx.send(embed=EmbedFactory.error("Please separate options with 'or'"))
            return
        
        choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
        
        if len(choices) < 2:
            await ctx.send(embed=EmbedFactory.error("Please provide at least 2 options"))
            return
        
        chosen = random.choice(choices)
        
        embed = EmbedFactory.fun(
            f"**Options:** {', '.join(choices)}\n\n"
            f"**I choose:** **{chosen}**",
            "🤔 Choose"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="meme",
        description="Get a random meme"
    )
    async def meme(self, ctx):
        """Get a random meme"""
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
        
        embed = EmbedFactory.fun(
            f"**{meme}**\n{description}",
            "😄 Random Meme"
        )
        embed.set_footer(text="Use an image editor to create this meme!")
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="fact",
        description="Random interesting fact"
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
        
        embed = EmbedFactory.fun(
            random.choice(facts),
            "🧠 Did You Know?"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="joke",
        description="Tell a joke"
    )
    async def joke(self, ctx):
        """Tell a joke"""
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
        
        embed = EmbedFactory.fun(
            f"**{setup}**\n\n||{punchline}||",
            "😂 Random Joke"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="quote",
        description="Random inspirational quote"
    )
    async def quote(self, ctx):
        """Random quote"""
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
        
        embed = EmbedFactory.fun(
            f"*{quote}*\n\n— **{author}**",
            "💭 Inspirational Quote"
        )
        
        await ctx.send(embed=embed)

# =========================
# INFO COG
# =========================
class InfoCog(commands.Cog, name="📊 Information"):
    """Information commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
    
    @commands.command(
        name="serverinfo",
        aliases=["server", "guildinfo"],
        description="Get server information"
    )
    async def serverinfo(self, ctx):
        """Display server information"""
        guild = ctx.guild
        
        # Create embed
        embed = EmbedFactory.create(
            title=f"{guild.name} Information",
            description=guild.description or "No description",
            color=guild.owner.color if guild.owner else discord.Color.blue()
        )
        
        # Set thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        
        # Member info
        online = len([m for m in guild.members if m.status != discord.Status.offline])
        embed.add_field(name="👥 Members", value=f"{guild.member_count} ({online} online)", inline=True)
        embed.add_field(name="🤖 Bots", value=str(len([m for m in guild.members if m.bot])), inline=True)
        
        # Boost info
        if guild.premium_tier > 0:
            embed.add_field(
                name="🚀 Boosts",
                value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)",
                inline=True
            )
        
        # Channel info
        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        categories = len(guild.categories)
        embed.add_field(name="📝 Channels", value=f"{text} Text, {voice} Voice", inline=True)
        embed.add_field(name="📁 Categories", value=str(categories), inline=True)
        embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
        
        # Emoji info
        if guild.emojis:
            embed.add_field(name="😄 Emojis", value=str(len(guild.emojis)), inline=True)
        
        # Verification level
        embed.add_field(name="🔐 Verification", value=str(guild.verification_level).title(), inline=True)
        
        # Features
        if guild.features:
            features = [f.replace("_", " ").title() for f in guild.features[:5]]
            embed.add_field(name="✨ Features", value=", ".join(features), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="userinfo",
        aliases=["user", "whois"],
        description="Get user information",
        usage="[member]"
    )
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display user information"""
        member = member or ctx.author
        
        # Create embed
        embed = EmbedFactory.create(
            title=f"{member.display_name}'s Information",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        
        # Set thumbnail
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Basic info
        embed.add_field(name="👤 Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
        embed.add_field(name="🤖 Bot", value="✅" if member.bot else "❌", inline=True)
        
        # Account info
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
            roles_text = " ".join(roles[:10])
            if len(roles) > 10:
                roles_text += f" (+{len(roles) - 10} more)"
            embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
        
        # Key permissions
        permissions = []
        if member.guild_permissions.administrator:
            permissions.append("Administrator")
        if member.guild_permissions.manage_messages:
            permissions.append("Manage Messages")
        if member.guild_permissions.manage_channels:
            permissions.append("Manage Channels")
        
        if permissions:
            embed.add_field(name="🔑 Key Permissions", value=", ".join(permissions), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="botinfo",
        aliases=["about", "stats"],
        description="Get bot information"
    )
    async def botinfo(self, ctx):
        """Display bot information"""
        # Calculate uptime
        uptime = datetime.datetime.now() - self.bot.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Create embed
        embed = EmbedFactory.create(
            title=f"{self.bot.user.name} Information",
            description="A feature-rich Discord bot with moderation, fun, and AI capabilities.",
            color=self.bot.user.color
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        # Bot stats
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed.add_field(name="🤖 Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name="🆔 Bot ID", value=str(self.bot.user.id), inline=True)
        embed.add_field(name="📚 Version", value=Config.VERSION, inline=True)
        
        # Server stats
        embed.add_field(name="🏰 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Total Users", value=str(total_members), inline=True)
        embed.add_field(name="📈 Commands Used", value=str(self.bot.command_count), inline=True)
        
        # Performance
        embed.add_field(name="⏰ Uptime", value=f"{days}d {hours}h {minutes}m", inline=True)
        embed.add_field(name="📊 Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Developer info
        owners = [f"<@{owner_id}>" for owner_id in Config.OWNER_IDS]
        embed.add_field(name="👨‍💻 Developers", value=", ".join(owners), inline=False)
        
        # Links
        embed.add_field(
            name="🔗 Links",
            value=f"[Support Server]({Config.SUPPORT_SERVER}) | [GitHub]({Config.GITHUB_REPO})",
            inline=False
        )
        
        embed.set_footer(text=f"Made with discord.py v{discord.__version__}")
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="avatar",
        aliases=["av", "pfp"],
        description="Get user's avatar",
        usage="[member]"
    )
    async def avatar(self, ctx, member: discord.Member = None):
        """Display user's avatar"""
        member = member or ctx.author
        
        embed = EmbedFactory.create(
            title=f"{member.display_name}'s Avatar",
            color=member.color
        )
        
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        embed.set_image(url=avatar_url)
        
        # Add download link
        embed.add_field(
            name="🔗 Links",
            value=f"[PNG]({avatar_url}) | [JPG]({avatar_url}) | [WEBP]({avatar_url})",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="roleinfo",
        description="Get role information",
        usage="<role>"
    )
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Display role information"""
        # Create embed
        embed = EmbedFactory.create(
            title=f"{role.name} Information",
            color=role.color
        )
        
        # Basic info
        embed.add_field(name="🆔 Role ID", value=str(role.id), inline=True)
        embed.add_field(name="🎨 Color", value=str(role.color), inline=True)
        embed.add_field(name="👥 Members", value=str(len(role.members)), inline=True)
        
        # Position and hoist
        embed.add_field(name="📊 Position", value=f"#{role.position}", inline=True)
        embed.add_field(name="🏷️ Hoisted", value="✅" if role.hoist else "❌", inline=True)
        embed.add_field(name="🔔 Mentionable", value="✅" if role.mentionable else "❌", inline=True)
        
        # Created at
        embed.add_field(name="📅 Created", value=role.created_at.strftime("%b %d, %Y"), inline=True)
        
        # Key permissions
        perms = []
        if role.permissions.administrator:
            perms.append("Administrator")
        if role.permissions.manage_messages:
            perms.append("Manage Messages")
        if role.permissions.kick_members:
            perms.append("Kick Members")
        if role.permissions.ban_members:
            perms.append("Ban Members")
        
        if perms:
            embed.add_field(name="🔑 Key Permissions", value=", ".join(perms), inline=False)
        
        await ctx.send(embed=embed)

# =========================
# UTILITY COG
# =========================
class UtilityCog(commands.Cog, name="⚙️ Utility"):
    """Utility commands"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
    
    @commands.command(
        name="ping",
        description="Check bot latency"
    )
    async def ping(self, ctx):
        """Check bot latency"""
        # Calculate different pings
        ws_latency = round(self.bot.latency * 1000)
        
        # Message latency
        start = datetime.datetime.now()
        msg = await ctx.send("🏓 Pinging...")
        end = datetime.datetime.now()
        msg_latency = round((end - start).total_seconds() * 1000)
        
        embed = EmbedFactory.create(
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
        """Get bot invite link"""
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
        
        embed = EmbedFactory.create(
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
        """Show help menu"""
        if command:
            # Show specific command help
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                await ctx.send(embed=EmbedFactory.error(f"Command '{command}' not found."))
                return
            
            embed = EmbedFactory.create(
                title=f"Help: {cmd.name}",
                description=cmd.description or "No description provided.",
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
            
            # Cooldown
            if hasattr(cmd, '_buckets') and cmd._buckets:
                rate, per, type = cmd._buckets._cooldown
                embed.add_field(name="Cooldown", value=f"{rate} per {per}s", inline=True)
            
            # Permissions
            if cmd.checks:
                for check in cmd.checks:
                    if hasattr(check, '__name__') and 'has_permissions' in check.__name__:
                        embed.add_field(name="Required Permissions", value="Special", inline=True)
            
            await ctx.send(embed=embed)
            
        else:
            # Show general help menu
            embed = EmbedFactory.create(
                title="📚 Help Menu",
                description=f"Use `{ctx.prefix}help <command>` for detailed help on a specific command.",
                color=discord.Color.blue()
            )
            
            # Group commands by cog
            cogs = {}
            for cmd in self.bot.commands:
                if not cmd.hidden:
                    cog_name = cmd.cog.qualified_name if cmd.cog else "No Category"
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
            
            embed.add_field(
                name="ℹ️ Information",
                value=f"**Prefix:** `{ctx.prefix}`\n**Total Commands:** {len(self.bot.commands)}",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @commands.command(
        name="poll",
        description="Create a poll",
        usage="<question>"
    )
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, question: str):
        """Create a poll"""
        embed = EmbedFactory.create(
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
        """Set a timer"""
        if seconds > 3600:  # 1 hour max
            await ctx.send(embed=EmbedFactory.error("Maximum timer duration is 1 hour (3600 seconds)"))
            return
        
        if seconds < 5:
            await ctx.send(embed=EmbedFactory.error("Minimum timer duration is 5 seconds"))
            return
        
        msg = await ctx.send(embed=EmbedFactory.success(f"⏰ Timer set for {seconds} seconds..."))
        
        await asyncio.sleep(seconds)
        
        embed = EmbedFactory.create(
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
        """Set a reminder"""
        # Parse time (e.g., 1h, 30m, 2d)
        time_pattern = re.compile(r'^(\d+)([smhd])$')
        match = time_pattern.match(time.lower())
        
        if not match:
            await ctx.send(embed=EmbedFactory.error(
                "Invalid time format. Use: 30s, 5m, 1h, 2d"
            ))
            return
        
        amount, unit = match.groups()
        amount = int(amount)
        
        # Convert to seconds
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        seconds = amount * multipliers[unit]
        
        if seconds > 604800:  # 7 days max
            await ctx.send(embed=EmbedFactory.error("Maximum reminder time is 7 days"))
            return
        
        # Store reminder
        reminder_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        # Send confirmation
        time_text = f"{amount}{unit}"
        embed = EmbedFactory.success(
            f"⏰ I'll remind you in {time_text} about:\n\n{message}"
        )
        await ctx.send(embed=embed)
        
        # Wait and send reminder
        await asyncio.sleep(seconds)
        
        reminder_embed = EmbedFactory.create(
            title="⏰ Reminder!",
            description=f"You asked me to remind you:\n\n{message}",
            color=discord.Color.gold()
        )
        
        try:
            await ctx.author.send(embed=reminder_embed)
        except:
            await ctx.send(f"{ctx.author.mention}", embed=reminder_embed)

# =========================
# ECONOMY COG
# =========================
class EconomyCog(commands.Cog, name="💰 Economy"):
    """Simple economy system"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.cooldowns = {}
        
    def get_user_balance(self, user_id: int) -> dict:
        """Get user's balance"""
        user_id = str(user_id)
        if user_id not in self.bot.data.data["economy"]:
            self.bot.data.data["economy"][user_id] = {
                "balance": 100,
                "bank": 0,
                "last_daily": None,
                "inventory": []
            }
        return self.bot.data.data["economy"][user_id]
    
    @commands.command(
        name="balance",
        aliases=["bal", "money"],
        description="Check your balance"
    )
    async def balance(self, ctx, member: discord.Member = None):
        """Check balance"""
        member = member or ctx.author
        user_data = self.get_user_balance(member.id)
        
        embed = EmbedFactory.create(
            title=f"{member.display_name}'s Balance",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="💵 Wallet", value=f"${user_data['balance']}", inline=True)
        embed.add_field(name="🏦 Bank", value=f"${user_data['bank']}", inline=True)
        embed.add_field(name="💰 Total", value=f"${user_data['balance'] + user_data['bank']}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="daily",
        description="Claim your daily reward"
    )
    @commands.cooldown(1, 86400, commands.BucketType.user)  # 24 hours
    async def daily(self, ctx):
        """Claim daily reward"""
        reward = random.randint(50, 200)
        user_data = self.get_user_balance(ctx.author.id)
        user_data["balance"] += reward
        
        self.bot.data.save_data()
        
        embed = EmbedFactory.success(
            f"🎁 You claimed your daily reward of **${reward}**!\n"
            f"New balance: **${user_data['balance']}**"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="work",
        description="Work to earn money"
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour
    async def work(self, ctx):
        """Work for money"""
        jobs = [
            ("Developer", 100, 200),
            ("Designer", 80, 150),
            ("Writer", 50, 100),
            ("Streamer", 150, 300),
            ("Chef", 60, 120),
            ("Artist", 70, 140)
        ]
        
        job, min_pay, max_pay = random.choice(jobs)
        earned = random.randint(min_pay, max_pay)
        
        user_data = self.get_user_balance(ctx.author.id)
        user_data["balance"] += earned
        
        self.bot.data.save_data()
        
        embed = EmbedFactory.success(
            f"💼 You worked as a **{job}** and earned **${earned}**!\n"
            f"New balance: **${user_data['balance']}**"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="gamble",
        description="Gamble your money",
        usage="<amount>"
    )
    async def gamble(self, ctx, amount: str):
        """Gamble money"""
        user_data = self.get_user_balance(ctx.author.id)
        
        # Parse amount
        if amount.lower() == "all":
            bet = user_data["balance"]
        elif amount.lower() == "half":
            bet = user_data["balance"] // 2
        else:
            try:
                bet = int(amount)
                if bet < 1:
                    raise ValueError
            except ValueError:
                await ctx.send(embed=EmbedFactory.error("Please enter a valid amount (number, 'all', or 'half')"))
                return
        
        # Check if user has enough money
        if bet > user_data["balance"]:
            await ctx.send(embed=EmbedFactory.error("You don't have enough money!"))
            return
        
        # Gamble logic
        win_chance = 0.45  # 45% chance to win
        multiplier = 2.0   # Double your money if you win
        
        if random.random() < win_chance:
            # Win
            winnings = int(bet * multiplier)
            user_data["balance"] += winnings
            result = f"🎉 You won **${winnings}**!"
            color = discord.Color.green()
        else:
            # Lose
            user_data["balance"] -= bet
            result = f"😢 You lost **${bet}**."
            color = discord.Color.red()
        
        self.bot.data.save_data()
        
        embed = EmbedFactory.create(
            title="🎰 Gambling Results",
            description=f"{result}\nNew balance: **${user_data['balance']}**",
            color=color
        )
        
        await ctx.send(embed=embed)

# =========================
# EVENTS COG
# =========================
class EventsCog(commands.Cog, name="📡 Events"):
    """Event handlers"""
    
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        logger.info(f"Connected to {len(self.bot.guilds)} guilds")
        logger.info("=" * 50)
        
        # Set initial status
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{Config.PREFIX}help"
            )
        )
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Send welcome message to first available channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = EmbedFactory.create(
                    title="👋 Thanks for inviting me!",
                    description=(
                        f"Hello {guild.name}! I'm **{self.bot.user.name}**, "
                        "a feature-rich Discord bot with moderation, fun, and AI capabilities.\n\n"
                        f"**Quick Start:**\n"
                        f"• Use `{Config.PREFIX}help` to see all commands\n"
                        f"• Use `{Config.PREFIX}serverinfo` to see server stats\n"
                        f"• Configure settings with `{Config.PREFIX}settings`\n\n"
                        f"**Need Help?**\n"
                        f"Join our support server: {Config.SUPPORT_SERVER}"
                    ),
                    color=discord.Color.green()
                )
                
                try:
                    await channel.send(embed=embed)
                except:
                    continue
                break
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Update stats
        self.bot.message_count += 1
        self.bot.data.data["stats"]["messages_processed"] += 1
        
        # AI response for questions
        if isinstance(message.channel, discord.TextChannel):
            # Check if message is a question directed at the bot
            if self.bot.user.mentioned_in(message) or message.content.lower().startswith((
                "hey bot", "hello bot", "hi bot", "bot, "
            )):
                # Remove mentions and bot reference
                content = message.content.lower()
                content = content.replace(f"<@{self.bot.user.id}>", "").strip()
                content = content.replace("bot", "").strip()
                
                if content and len(content) > 3:
                    async with message.channel.typing():
                        response = await self.bot.ai.ask(
                            content,
                            f"You are a helpful Discord bot in a server called {message.guild.name}. "
                            "Keep responses friendly and concise."
                        )
                        
                        if response and not response.startswith("❌"):
                            await message.reply(response)
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Called when a command is invoked"""
        self.bot.command_count += 1
        
        # Update command stats
        self.bot.data.update_command_stats(ctx.guild.id, ctx.command.name)
        
        # Log command usage
        logger.info(f"Command: {ctx.command.name} by {ctx.author} in {ctx.guild}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            # Suggest similar commands
            available = [cmd.name for cmd in self.bot.commands]
            user_input = ctx.invoked_with
            
            # Find similar commands
            similar = []
            for cmd in available:
                if user_input in cmd or cmd.startswith(user_input[:3]):
                    similar.append(cmd)
            
            if similar:
                await ctx.send(embed=EmbedFactory.error(
                    f"Command not found. Did you mean: `{', '.join(similar[:3])}`?"
                ))
            return
        
        elif isinstance(error, commands.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(embed=EmbedFactory.error(
                f"You're missing required permissions: {missing}"
            ))
        
        elif isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(embed=EmbedFactory.error(
                f"I'm missing required permissions: {missing}"
            ))
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=EmbedFactory.error(
                f"Missing required argument: `{error.param.name}`\n"
                f"Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
            ))
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=EmbedFactory.error(
                f"Invalid argument provided.\n"
                f"Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
            ))
        
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=EmbedFactory.error(
                f"Command on cooldown. Try again in {error.retry_after:.1f} seconds."
            ))
        
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(embed=EmbedFactory.error(
                "You don't have permission to use this command."
            ))
        
        else:
            # Log unexpected errors
            logger.error(f"Command error: {error}", exc_info=True)
            
            # Send generic error message
            await ctx.send(embed=EmbedFactory.error(
                "An unexpected error occurred. The developers have been notified."
            ))
            
            # Send error to bot owner
            owner = self.bot.get_user(Config.OWNER_IDS[0])
            if owner:
                error_embed = EmbedFactory.error(
                    f"**Command:** {ctx.command}\n"
                    f"**User:** {ctx.author} ({ctx.author.id})\n"
                    f"**Guild:** {ctx.guild.name} ({ctx.guild.id})\n"
                    f"**Error:** ```{str(error)[:1000]}```"
                )
                
                try:
                    await owner.send(embed=error_embed)
                except:
                    pass

# =========================
# MAIN ENTRY POINT
# =========================
def main():
    """Main entry point"""
    print("=" * 50)
    print("Discord Bot v2.0 - Starting...")
    print("=" * 50)
    
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ Loaded environment variables")
    except ImportError:
        print("⚠ dotenv not installed, using system environment variables")
    
    # Check for required tokens
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable is required!")
        print("Create a .env file with: DISCORD_BOT_TOKEN=your_token_here")
        exit(1)
    
    # Check for AI token (optional)
    if not os.getenv("GROQ_API_KEY"):
        print("⚠ WARNING: GROQ_API_KEY not found. AI features will be disabled.")
    
    # Create and run bot
    bot = DiscordBot()
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid bot token. Please check your DISCORD_BOT_TOKEN.")
    except KeyboardInterrupt:
        print("\n⚠ Bot shutting down...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.critical(f"Bot crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
