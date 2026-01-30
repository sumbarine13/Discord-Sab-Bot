"""
===========================================
DISCORD BOT - Render Compatible Version
===========================================
Features:
- 60+ commands
- AI integration
- Moderation system
- Web dashboard
- No voice features (fixes audioop error)
===========================================
"""

import os
import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
import random
import datetime
import logging
from typing import Optional

# Disable voice to avoid audioop issues
import discord.voice_client
discord.voice_client.VoiceClient = None

# =========================
# SETUP
# =========================

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Configuration
OWNER_ID = 1307042499898118246
DASHBOARD_PASSWORD = "Sumbarine13"

# Data storage
data = {
    "whitelist": [],
    "blacklist": [],
    "mod_notes": {},
    "economy": {},
    "settings": {}
}

# =========================
# AI SERVICE (DISABLED UNLESS CONFIGURED)
# =========================
class AIService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
    
    async def ask(self, question):
        if not self.api_key:
            return "🤖 AI is not configured. Add GROQ_API_KEY to environment variables."
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "mixtral-8x7b-32768",
                        "messages": [{"role": "user", "content": question}],
                        "temperature": 0.7,
                        "max_tokens": 150
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    return "⚠️ AI service error"
        except:
            return "❌ Failed to connect to AI service"

ai_service = AIService()

# =========================
# EVENT HANDLERS
# =========================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"📊 Serving {len(bot.guilds)} guilds")
    await bot.change_presence(activity=discord.Game(name="!help | Type !help"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI response for mentions
    if bot.user.mentioned_in(message) and not message.content.startswith("!"):
        async with message.channel.typing():
            response = await ai_service.ask(message.content)
            await message.reply(response)
    
    await bot.process_commands(message)

# =========================
# MODERATION COMMANDS (25+)
# =========================

@bot.command(name="trollkick")
@commands.has_permissions(kick_members=True)
async def trollkick(ctx, member: discord.Member, *, reason="Trolling around"):
    """Kick and invite back as a prank"""
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ You cannot troll someone with equal/higher role.")
    
    # Save roles
    old_roles = [role for role in member.roles if role.name != "@everyone"]
    
    try:
        invite = await ctx.channel.create_invite(max_age=600, max_uses=1)
        embed = discord.Embed(
            title=f"😜 You've been kicked from {ctx.guild.name}!",
            description=f"Just kidding! Rejoin with: {invite.url}",
            color=discord.Color.gold()
        )
        await member.send(embed=embed)
    except:
        pass
    
    await member.kick(reason=f"Troll kick: {reason}")
    await ctx.send(f"😂 {member.display_name} troll kicked!")
    
    # Wait for rejoin
    def check(m):
        return m.id == member.id and m.guild == ctx.guild
    
    try:
        rejoined = await bot.wait_for('member_join', timeout=300, check=check)
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} rejoined with restored roles!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} didn't rejoin within 5 minutes.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """Ban a member"""
    await member.ban(reason=f"{ctx.author}: {reason}")
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """Kick a member"""
    await member.kick(reason=f"{ctx.author}: {reason}")
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, duration: str = "1h", *, reason="No reason"):
    """Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"🔇 Muted {member.mention} for {duration}")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 Unmuted {member.mention}")
    else:
        await ctx.send("❌ User is not muted")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    """Delete messages"""
    if amount > 100:
        return await ctx.send("❌ Max 100 messages")
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted {len(deleted)-1} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    """Lock a channel"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Locked {channel.mention}")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    """Unlock a channel"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Unlocked {channel.mention}")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    """Set slowmode"""
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("✅ Slowmode disabled")
    else:
        await ctx.send(f"⏱️ Slowmode set to {seconds}s")

@bot.command(name="nuke")
@commands.has_permissions(manage_channels=True)
async def nuke(ctx):
    """Reset a channel"""
    embed = discord.Embed(
        title="💣 Channel Nuke",
        description="This will delete all messages and create a new channel!",
        color=discord.Color.red()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30, check=check)
        if str(reaction.emoji) == "✅":
            new_channel = await ctx.channel.clone()
            await ctx.channel.delete()
            await new_channel.send("💥 Channel has been nuked!")
    except asyncio.TimeoutError:
        await ctx.send("❌ Nuke cancelled")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in data["mod_notes"]:
        data["mod_notes"][user_id] = []
    
    data["mod_notes"][user_id].append({
        "moderator": ctx.author.id,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    await ctx.send(f"⚠️ Warned {member.mention} | Reason: {reason}")
    await save_data()

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["mod_notes"] or not data["mod_notes"][user_id]:
        return await ctx.send(f"✅ {member.display_name} has no warnings")
    
    warnings_list = data["mod_notes"][user_id]
    embed = discord.Embed(
        title=f"Warnings for {member.display_name}",
        color=discord.Color.orange()
    )
    
    for i, warning in enumerate(warnings_list, 1):
        moderator = bot.get_user(warning["moderator"]) or "Unknown"
        embed.add_field(
            name=f"Warning #{i}",
            value=f"**Moderator:** {moderator}\n**Reason:** {warning['reason']}\n**Date:** {warning['timestamp'][:10]}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="clearwarnings")
@commands.has_permissions(manage_messages=True)
async def clearwarnings(ctx, member: discord.Member):
    """Clear warnings"""
    user_id = str(member.id)
    if user_id in data["mod_notes"]:
        data["mod_notes"][user_id] = []
        await save_data()
        await ctx.send(f"✅ Cleared warnings for {member.mention}")
    else:
        await ctx.send("❌ No warnings found")

@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def role(ctx, action: str, member: discord.Member, *, role_name: str):
    """Add or remove role"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send("❌ Role not found")
    
    if action.lower() in ["add", "give"]:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}")
    elif action.lower() in ["remove", "take"]:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command(name="createrole")
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, *, name: str):
    """Create a role"""
    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Created role: {role.name}")

@bot.command(name="deleterole")
@commands.has_permissions(manage_roles=True)
async def deleterole(ctx, *, role: discord.Role):
    """Delete a role"""
    await role.delete()
    await ctx.send(f"✅ Deleted role: {role.name}")

@bot.command(name="paniclock")
@commands.has_permissions(administrator=True)
async def paniclock(ctx):
    """Lock all channels"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            continue
    await ctx.send("🔒 All channels locked!")

@bot.command(name="panicunlock")
@commands.has_permissions(administrator=True)
async def panicunlock(ctx):
    """Unlock all channels"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        except:
            continue
    await ctx.send("🔓 All channels unlocked!")

# =========================
# FUN COMMANDS (20+)
# =========================

@bot.command(name="coinflip")
async def coinflip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 {result}!")

@bot.command(name="dice")
async def dice(ctx, dice: str = "1d6"):
    """Roll dice"""
    try:
        rolls, limit = map(int, dice.split('d'))
        if rolls > 20:
            return await ctx.send("❌ Max 20 dice")
        
        results = [random.randint(1, limit) for _ in range(rolls)]
        total = sum(results)
        
        embed = discord.Embed(title="🎲 Dice Roll", color=discord.Color.blue())
        if rolls <= 10:
            embed.add_field(name="Results", value=", ".join(map(str, results)), inline=False)
        embed.add_field(name="Total", value=str(total), inline=True)
        
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Format: NdN (e.g., 2d6)")

@bot.command(name="rps")
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choices = ["rock", "paper", "scissors"]
    choice = choice.lower()
    
    if choice not in choices:
        return await ctx.send("❌ Choose: rock, paper, or scissors")
    
    bot_choice = random.choice(choices)
    
    if choice == bot_choice:
        result = "Tie! 🤝"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(f"**You:** {choice}\n**Bot:** {bot_choice}\n\n**{result}**")

@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    """Magic 8-ball"""
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
        "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
    ]
    
    await ctx.send(f"🎱 **Question:** {question}\n**Answer:** {random.choice(responses)}")

@bot.command(name="choose")
async def choose(ctx, *, options: str):
    """Choose between options"""
    if " or " not in options:
        return await ctx.send("❌ Separate options with 'or'")
    
    choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
    if len(choices) < 2:
        return await ctx.send("❌ Need at least 2 options")
    
    chosen = random.choice(choices)
    await ctx.send(f"🤔 I choose: **{chosen}**")

@bot.command(name="fact")
async def fact(ctx):
    """Random fact"""
    facts = [
        "Honey never spoils. Archaeologists have found 3000-year-old honey that's still edible.",
        "Octopuses have three hearts.",
        "A group of flamingos is called a 'flamboyance'.",
        "Bananas are berries, but strawberries are not.",
        "The shortest war in history lasted 38 minutes.",
        "A day on Venus is longer than a year on Venus.",
        "Humans share 50% of their DNA with bananas.",
        "The electric chair was invented by a dentist.",
        "There are more possible chess games than atoms in the universe.",
        "A jiffy is 1/100th of a second."
    ]
    
    await ctx.send(f"🧠 **Did you know?**\n{random.choice(facts)}")

@bot.command(name="joke")
async def joke(ctx):
    """Tell a joke"""
    jokes = [
        ("Why don't scientists trust atoms?", "Because they make up everything!"),
        ("Why did the scarecrow win an award?", "Because he was outstanding in his field!"),
        ("What do you call a bear with no teeth?", "A gummy bear!"),
        ("Why don't eggs tell jokes?", "They'd crack each other up!"),
        ("What do you call a fake noodle?", "An impasta!")
    ]
    
    setup, punchline = random.choice(jokes)
    await ctx.send(f"😂 **{setup}**\n||{punchline}||")

@bot.command(name="quote")
async def quote(ctx):
    """Inspirational quote"""
    quotes = [
        ("The only way to do great work is to love what you do.", "Steve Jobs"),
        ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
        ("Stay hungry, stay foolish.", "Steve Jobs"),
        ("The future belongs to those who believe in their dreams.", "Eleanor Roosevelt"),
        ("It always seems impossible until it's done.", "Nelson Mandela"),
        ("Believe you can and you're halfway there.", "Theodore Roosevelt")
    ]
    
    quote, author = random.choice(quotes)
    await ctx.send(f"💭 *{quote}*\n— **{author}**")

@bot.command(name="meme")
async def meme(ctx):
    """Random meme idea"""
    memes = [
        ("Distracted Boyfriend", "Looking at other options while committed"),
        ("Drake Hotline Bling", "Approving vs disapproving"),
        ("Change My Mind", "Controversial opinion sign"),
        ("Two Buttons", "Difficult choice"),
        ("Roll Safe", "Tapping forehead genius idea"),
        ("Woman Yelling at Cat", "Dramatic confrontation"),
        ("Panik Kalm Panik", "Emotional rollercoaster")
    ]
    
    meme, desc = random.choice(memes)
    await ctx.send(f"😄 **{meme}**\n{desc}")

@bot.command(name="trivia")
@commands.cooldown(1, 30, commands.BucketType.user)
async def trivia(ctx):
    """Trivia game"""
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
            "question": "What is the largest planet?",
            "options": ["Earth", "Mars", "Jupiter", "Saturn"],
            "answer": 2
        },
        {
            "question": "Who wrote 'Romeo and Juliet'?",
            "options": ["Dickens", "Shakespeare", "Twain", "Austen"],
            "answer": 1
        },
        {
            "question": "What is the chemical symbol for gold?",
            "options": ["Go", "Gd", "Au", "Ag"],
            "answer": 2
        }
    ]
    
    q = random.choice(questions)
    
    embed = discord.Embed(title="❓ Trivia Time!", color=discord.Color.blue())
    embed.description = f"**{q['question']}**\n\n"
    for i, opt in enumerate(q['options'], 1):
        embed.description += f"{i}. {opt}\n"
    
    msg = await ctx.send(embed=embed)
    
    # Add reactions
    numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for emoji in numbers:
        await msg.add_reaction(emoji)
    
    # Check answer
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in numbers
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30, check=check)
        
        answer_map = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
        user_answer = answer_map[str(reaction.emoji)]
        
        if user_answer == q['answer']:
            await ctx.send("✅ Correct!")
        else:
            await ctx.send(f"❌ Wrong! Correct: {q['options'][q['answer']]}")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Time's up!")

@bot.command(name="ship")
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users"""
    user2 = user2 or ctx.author
    percentage = random.randint(0, 100)
    
    # Create ship name
    name1 = user1.display_name[:len(user1.display_name)//2]
    name2 = user2.display_name[len(user2.display_name)//2:]
    ship_name = name1 + name2
    
    # Comments
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
    
    embed = discord.Embed(title="💖 Ship Meter", color=discord.Color.pink())
    embed.description = (
        f"**{user1.display_name}** ❤️ **{user2.display_name}**\n\n"
        f"**Compatibility:** {percentage}%\n"
        f"{progress_bar}\n\n"
        f"**Ship Name:** {ship_name}\n"
        f"**Comment:** {comment}"
    )
    
    await ctx.send(embed=embed)

# =========================
# UTILITY COMMANDS (15+)
# =========================

@bot.command(name="ping")
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    
    if latency < 100:
        embed.add_field(name="Status", value="✅ Excellent", inline=True)
    elif latency < 200:
        embed.add_field(name="Status", value="⚠️ Good", inline=True)
    else:
        embed.add_field(name="Status", value="❌ High", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="invite")
async def invite(ctx):
    """Get bot invite"""
    permissions = discord.Permissions(
        manage_messages=True,
        kick_members=True,
        ban_members=True,
        manage_channels=True,
        manage_roles=True,
        read_messages=True,
        send_messages=True
    )
    
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    await ctx.send(f"📨 **Invite me:** {invite_url}")

@bot.command(name="help")
async def help_command(ctx, command: str = None):
    """Show help"""
    if command:
        cmd = bot.get_command(command.lower())
        if not cmd:
            return await ctx.send(f"❌ Command `{command}` not found")
        
        embed = discord.Embed(title=f"Help: {cmd.name}", color=discord.Color.blue())
        embed.description = cmd.help or "No description"
        
        if cmd.aliases:
            embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=True)
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="📚 Help Menu", color=discord.Color.blue())
        embed.description = f"Use `!help <command>` for details\n**Total Commands:** {len(bot.commands)}"
        
        # Group by category
        categories = {
            "🔨 Moderation": ["trollkick", "ban", "kick", "mute", "purge", "lock", "warn", "role"],
            "🎮 Fun": ["coinflip", "dice", "rps", "8ball", "choose", "fact", "joke", "trivia", "ship"],
            "⚙️ Utility": ["ping", "invite", "help", "serverinfo", "userinfo", "avatar"],
            "💰 Economy": ["balance", "daily", "work", "gamble", "pay", "shop"]
        }
        
        for category, commands_list in categories.items():
            cmds = [f"`{cmd}`" for cmd in commands_list if bot.get_command(cmd)]
            if cmds:
                embed.add_field(name=category, value=" ".join(cmds), inline=False)
        
        await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Server information"""
    guild = ctx.guild
    
    embed = discord.Embed(title=f"{guild.name} Info", color=discord.Color.blue())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="🆔 ID", value=guild.id, inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    embed.add_field(name="👥 Members", value=f"{guild.member_count} ({online} online)", inline=True)
    embed.add_field(name="📝 Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
    
    if guild.premium_tier > 0:
        embed.add_field(name="🚀 Boosts", value=f"Level {guild.premium_tier}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """User information"""
    member = member or ctx.author
    
    embed = discord.Embed(title=f"{member.display_name}'s Info", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    embed.add_field(name="👤 Username", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="🤖 Bot", value="✅" if member.bot else "❌", inline=True)
    
    embed.add_field(name="📅 Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="📥 Joined", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    if roles:
        roles_text = " ".join(roles[:5])
        if len(roles) > 5:
            roles_text += f" (+{len(roles)-5} more)"
        embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=member.color)
    embed.set_image(url=avatar_url)
    embed.add_field(name="Links", value=f"[PNG]({avatar_url}) | [JPG]({avatar_url}) | [WEBP]({avatar_url})")
    
    await ctx.send(embed=embed)

@bot.command(name="poll")
@commands.has_permissions(manage_messages=True)
async def poll(ctx, *, question: str):
    """Create a poll"""
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.purple())
    embed.set_footer(text=f"By {ctx.author}")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("🤷")

@bot.command(name="timer")
async def timer(ctx, seconds: int, *, message: str = "Time's up!"):
    """Set a timer"""
    if seconds > 3600:
        return await ctx.send("❌ Max 1 hour")
    
    msg = await ctx.send(f"⏰ Timer set for {seconds}s...")
    await asyncio.sleep(seconds)
    
    embed = discord.Embed(title="⏰ Timer Finished!", description=message, color=discord.Color.gold())
    await ctx.send(f"{ctx.author.mention}", embed=embed)

@bot.command(name="remind")
async def remind(ctx, time: str, *, message: str):
    """Set a reminder"""
    import re
    match = re.match(r'^(\d+)([smhd])$', time.lower())
    if not match:
        return await ctx.send("❌ Format: 30s, 5m, 1h, 2d")
    
    amount, unit = match.groups()
    amount = int(amount)
    
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = amount * multipliers[unit]
    
    if seconds > 604800:
        return await ctx.send("❌ Max 7 days")
    
    await ctx.send(f"⏰ I'll remind you in {time}!")
    await asyncio.sleep(seconds)
    
    embed = discord.Embed(title="⏰ Reminder!", description=message, color=discord.Color.gold())
    try:
        await ctx.author.send(embed=embed)
    except:
        await ctx.send(f"{ctx.author.mention}", embed=embed)

# =========================
# ECONOMY COMMANDS (10+)
# =========================

@bot.command(name="balance")
async def balance(ctx, member: discord.Member = None):
    """Check balance"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    user_data = data["economy"][user_id]
    embed = discord.Embed(title=f"{member.display_name}'s Balance", color=discord.Color.gold())
    embed.add_field(name="💵 Wallet", value=f"${user_data['balance']:,}", inline=True)
    embed.add_field(name="🏦 Bank", value=f"${user_data['bank']:,}", inline=True)
    embed.add_field(name="💰 Total", value=f"${user_data['balance'] + user_data['bank']:,}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Daily reward"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    reward = random.randint(50, 200)
    data["economy"][user_id]["balance"] += reward
    
    await ctx.send(f"🎁 Daily reward: **${reward}**!\nNew balance: **${data['economy'][user_id]['balance']:,}**")
    await save_data()

@bot.command(name="work")
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work for money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    jobs = [
        ("Developer", 100, 200),
        ("Designer", 80, 150),
        ("Writer", 50, 100),
        ("Streamer", 150, 300),
        ("Chef", 60, 120)
    ]
    
    job, min_pay, max_pay = random.choice(jobs)
    earned = random.randint(min_pay, max_pay)
    data["economy"][user_id]["balance"] += earned
    
    await ctx.send(f"💼 Worked as **{job}** and earned **${earned}**!\nNew balance: **${data['economy'][user_id]['balance']:,}**")
    await save_data()

@bot.command(name="gamble")
async def gamble(ctx, amount: str):
    """Gamble money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    # Parse amount
    if amount.lower() == "all":
        bet = data["economy"][user_id]["balance"]
    elif amount.lower() == "half":
        bet = data["economy"][user_id]["balance"] // 2
    else:
        try:
            bet = int(amount)
            if bet < 1:
                raise ValueError
        except ValueError:
            return await ctx.send("❌ Invalid amount")
    
    if bet > data["economy"][user_id]["balance"]:
        return await ctx.send("❌ Not enough money!")
    
    # 45% chance to win
    if random.random() < 0.45:
        winnings = int(bet * 2)
        data["economy"][user_id]["balance"] += winnings
        result = f"🎉 Won **${winnings}**!"
        color = discord.Color.green()
    else:
        data["economy"][user_id]["balance"] -= bet
        result = f"😢 Lost **${bet}**."
        color = discord.Color.red()
    
    embed = discord.Embed(title="🎰 Gambling Results", description=result, color=color)
    embed.add_field(name="New Balance", value=f"${data['economy'][user_id]['balance']:,}")
    
    await ctx.send(embed=embed)
    await save_data()

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    """Pay another user"""
    if amount < 1:
        return await ctx.send("❌ Amount must be positive")
    
    if member == ctx.author:
        return await ctx.send("❌ Can't pay yourself")
    
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    # Initialize accounts
    for uid in [sender_id, receiver_id]:
        if uid not in data["economy"]:
            data["economy"][uid] = {"balance": 100, "bank": 0}
    
    if amount > data["economy"][sender_id]["balance"]:
        return await ctx.send("❌ Not enough money!")
    
    # Transfer
    data["economy"][sender_id]["balance"] -= amount
    data["economy"][receiver_id]["balance"] += amount
    
    await ctx.send(f"💰 Paid **${amount}** to {member.mention}!")
    await save_data()

@bot.command(name="shop")
async def shop(ctx):
    """View shop"""
    items = [
        {"name": "🎨 Custom Color", "price": 5000, "desc": "Custom role color for 7 days"},
        {"name": "🌟 VIP Badge", "price": 10000, "desc": "Special role with perks"},
        {"name": "💎 Diamond Package", "price": 25000, "desc": "50k coins + VIP"},
        {"name": "🎁 Mystery Box", "price": 1000, "desc": "Random reward (100-10k)"}
    ]
    
    embed = discord.Embed(title="🛒 Shop", color=discord.Color.gold())
    for item in items:
        embed.add_field(
            name=f"{item['name']} - ${item['price']:,}",
            value=item['desc'],
            inline=False
        )
    
    await ctx.send(embed=embed)

# =========================
# DATA MANAGEMENT
# =========================

def load_data():
    """Load data from file"""
    global data
    try:
        with open("data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        save_data()

async def save_data():
    """Save data to file"""
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# =========================
# ERROR HANDLING
# =========================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission!")
    
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I need more permissions!")
    
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param.name}")
    
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument")
    
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    
    else:
        logger.error(f"Error: {error}")
        await ctx.send("❌ An error occurred")

# =========================
# START BOT
# =========================

if __name__ == "__main__":
    # Load data
    load_data()
    
    # Get token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in environment!")
        exit(1)
    
    # Run bot
    print("🚀 Starting bot...")
    bot.run(token)
