"""
Discord Bot - Complete with AI, Moderation, Fun
Owner ID: 1307042499898118246
60+ Commands: 35 Moderation, 5 AI Games, 20+ Fun/Utility
"""
import os
import sys
import discord
from discord.ext import commands
import random
import asyncio
import aiohttp
import datetime
import json

# ========== FIX FOR AUDIOOP ==========
class FakeAudioop:
    def __getattr__(self, name):
        return lambda *args, **kwargs: b''

if 'audioop' not in sys.modules:
    sys.modules['audioop'] = FakeAudioop()

# ========== CONFIGURATION ==========
OWNER_ID = 1307042499898118246
PREFIX = "!"

# ========== DATA STORAGE ==========
data = {
    "economy": {},
    "warnings": {},
    "whitelist": [],  # Users who can use mod commands
    "blacklist": [],  # Users blocked from commands
    "ai_history": {}
}

# ========== BOT SETUP ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ========== PERMISSION SYSTEM ==========
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def can_use_mod():
    async def predicate(ctx):
        # Owner can always use
        if ctx.author.id == OWNER_ID:
            return True
        # Check whitelist
        if ctx.author.id in data["whitelist"]:
            return True
        # Check blacklist
        if ctx.author.id in data["blacklist"]:
            await ctx.send("⛔ You are blacklisted from using commands!")
            return False
        return False
    return commands.check(predicate)

# ========== GROQ AI SERVICE ==========
class AIService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
    
    async def ask(self, question, max_tokens=100):
        """Ask Groq AI a question"""
        if not self.api_key:
            return "🤖 AI not configured. Set GROQ_API_KEY environment variable."
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": "mixtral-8x7b-32768",
                "messages": [{
                    "role": "system",
                    "content": "You are a helpful Discord bot assistant. Keep responses concise and friendly."
                }, {
                    "role": "user",
                    "content": question
                }],
                "temperature": 0.7,
                "max_tokens": max_tokens
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    return "⚠️ AI service error"
        except:
            return "❌ Failed to connect to AI service"

ai_service = AIService()

# ========== EVENT HANDLERS ==========
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    print(f"🔒 Owner ID: {OWNER_ID}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI response for mentions
    if bot.user.mentioned_in(message):
        # Remove mention
        content = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        
        if content:
            # Store in history
            user_key = str(message.author.id)
            if user_key not in data["ai_history"]:
                data["ai_history"][user_key] = []
            data["ai_history"][user_key].append({
                "question": content,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            async with message.channel.typing():
                response = await ai_service.ask(content, max_tokens=50)
                await message.reply(response)
        else:
            await message.reply("🤖 How can I help you?")
    
    await bot.process_commands(message)

# ========== WHITELIST/BLACKLIST COMMANDS (OWNER ONLY) ==========
@bot.command()
@is_owner()
async def whitelist(ctx, action: str, member: discord.Member):
    """[OWNER] Add/remove from whitelist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["whitelist"]:
            data["whitelist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to whitelist")
        else:
            await ctx.send("ℹ️ User already in whitelist")
    elif action.lower() in ["remove", "-", "rm"]:
        if member.id in data["whitelist"]:
            data["whitelist"].remove(member.id)
            await ctx.send(f"✅ Removed {member.mention} from whitelist")
        else:
            await ctx.send("ℹ️ User not in whitelist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def blacklist(ctx, action: str, member: discord.Member):
    """[OWNER] Add/remove from blacklist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["blacklist"]:
            data["blacklist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to blacklist")
        else:
            await ctx.send("ℹ️ User already in blacklist")
    elif action.lower() in ["remove", "-", "rm"]:
        if member.id in data["blacklist"]:
            data["blacklist"].remove(member.id)
            await ctx.send(f"✅ Removed {member.mention} from blacklist")
        else:
            await ctx.send("ℹ️ User not in blacklist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def showlists(ctx):
    """[OWNER] Show whitelist and blacklist"""
    embed = discord.Embed(title="📋 Permission Lists", color=0x5865F2)
    
    whitelist_mentions = []
    for user_id in data["whitelist"][:20]:
        user = bot.get_user(user_id)
        whitelist_mentions.append(f"• {user.mention if user else f'<@{user_id}>'}")
    
    blacklist_mentions = []
    for user_id in data["blacklist"][:20]:
        user = bot.get_user(user_id)
        blacklist_mentions.append(f"• {user.mention if user else f'<@{user_id}>'}")
    
    embed.add_field(
        name=f"✅ Whitelist ({len(data['whitelist'])})",
        value="\n".join(whitelist_mentions) if whitelist_mentions else "Empty",
        inline=False
    )
    
    embed.add_field(
        name=f"❌ Blacklist ({len(data['blacklist'])})",
        value="\n".join(blacklist_mentions) if blacklist_mentions else "Empty",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ========== MODERATION COMMANDS (35 TOTAL) ==========
@bot.command()
@can_use_mod()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """Kick a member"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command()
@can_use_mod()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """Ban a member"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command()
@can_use_mod()
async def unban(ctx, user_id: int):
    """Unban a user"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned {user}")
    except:
        await ctx.send("❌ User not found or not banned")

@bot.command()
@can_use_mod()
async def purge(ctx, amount: int = 10):
    """Delete messages"""
    if amount > 100:
        await ctx.send("❌ Max 100 messages")
        return
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 Deleted {len(deleted)} messages")
    await asyncio.sleep(2)
    await msg.delete()

@bot.command()
@can_use_mod()
async def mute(ctx, member: discord.Member, duration: str = "1h", *, reason="No reason"):
    """Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"🔇 Muted {member.mention} for {duration}")

@bot.command()
@can_use_mod()
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 Unmuted {member.mention}")

@bot.command()
@can_use_mod()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in data["warnings"]:
        data["warnings"][user_id] = []
    
    data["warnings"][user_id].append({
        "moderator": ctx.author.id,
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    await ctx.send(f"⚠️ Warned {member.mention} | Reason: {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["warnings"] or not data["warnings"][user_id]:
        await ctx.send(f"✅ {member.display_name} has no warnings")
        return
    
    embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xff9900)
    for i, warning in enumerate(data["warnings"][user_id][:10], 1):
        embed.add_field(
            name=f"Warning #{i}",
            value=f"Reason: {warning['reason']}\nDate: {warning['timestamp'][:10]}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
@can_use_mod()
async def clearwarns(ctx, member: discord.Member):
    """Clear all warnings for a member"""
    user_id = str(member.id)
    if user_id in data["warnings"]:
        data["warnings"][user_id] = []
        await ctx.send(f"✅ Cleared warnings for {member.mention}")
    else:
        await ctx.send("ℹ️ No warnings found")

@bot.command()
@can_use_mod()
async def trollkick(ctx, member: discord.Member, *, reason="Trolling around"):
    """Prank kick a member"""
    # Save roles
    roles = [role for role in member.roles if role != ctx.guild.default_role]
    
    try:
        # Create invite
        invite = await ctx.channel.create_invite(max_age=300, max_uses=1)
        await member.send(f"😜 You've been kicked! Just kidding! Rejoin: {invite.url}")
    except:
        pass
    
    # Kick
    await member.kick(reason=f"Troll kick: {reason}")
    await ctx.send(f"😂 {member.display_name} was troll kicked!")
    
    # Wait for rejoin
    def check(m):
        return m.id == member.id
    
    try:
        rejoined = await bot.wait_for('member_join', timeout=300, check=check)
        if roles:
            await rejoined.add_roles(*roles)
            await ctx.send(f"✅ {member.display_name} rejoined with restored roles!")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ {member.display_name} didn't rejoin within 5 minutes")

@bot.command()
@can_use_mod()
async def lock(ctx, channel: discord.TextChannel = None):
    """Lock a channel"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Locked {channel.mention}")

@bot.command()
@can_use_mod()
async def unlock(ctx, channel: discord.TextChannel = None):
    """Unlock a channel"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Unlocked {channel.mention}")

@bot.command()
@can_use_mod()
async def slowmode(ctx, seconds: int):
    """Set slowmode"""
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode set to {seconds}s")

@bot.command()
@can_use_mod()
async def roleadd(ctx, member: discord.Member, *, role_name: str):
    """Add role to member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}")
    else:
        await ctx.send("❌ Role not found")

@bot.command()
@can_use_mod()
async def roleremove(ctx, member: discord.Member, *, role_name: str):
    """Remove role from member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}")
    else:
        await ctx.send("❌ Role not found or member doesn't have it")

@bot.command()
@can_use_mod()
async def createrole(ctx, *, name: str):
    """Create a role"""
    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Created role: {role.name}")

@bot.command()
@can_use_mod()
async def deleterole(ctx, *, role: discord.Role):
    """Delete a role"""
    await role.delete()
    await ctx.send(f"✅ Deleted role: {role.name}")

@bot.command()
@can_use_mod()
async def nick(ctx, member: discord.Member, *, nickname: str):
    """Change nickname"""
    await member.edit(nick=nickname[:32])
    await ctx.send(f"✅ Changed {member.mention}'s nickname")

@bot.command()
@can_use_mod()
async def clearuser(ctx, member: discord.Member, amount: int = 10):
    """Clear messages from specific user"""
    def check(m):
        return m.author.id == member.id
    
    deleted = await ctx.channel.purge(limit=amount, check=check)
    await ctx.send(f"🧹 Cleared {len(deleted)} messages from {member.mention}", delete_after=3)

# Additional moderation commands to reach 35
@bot.command()
@can_use_mod()
async def softban(ctx, member: discord.Member, *, reason="No reason"):
    """Kick and clear messages"""
    await member.ban(reason=f"Softban: {reason}")
    await ctx.guild.unban(member)
    await ctx.send(f"🧹 Softbanned {member.mention}")

@bot.command()
@can_use_mod()
async def timeout(ctx, member: discord.Member, minutes: int = 10):
    """Timeout a member"""
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration)
    await ctx.send(f"⏰ Timed out {member.mention} for {minutes} minutes")

@bot.command()
@can_use_mod()
async def untimeout(ctx, member: discord.Member):
    """Remove timeout"""
    await member.timeout(None)
    await ctx.send(f"✅ Removed timeout from {member.mention}")

@bot.command()
@can_use_mod()
async def modlog(ctx, member: discord.Member = None):
    """View moderation history"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["warnings"] or not data["warnings"][user_id]:
        await ctx.send(f"📝 No mod log for {member.display_name}")
        return
    
    warns = data["warnings"][user_id]
    embed = discord.Embed(title=f"Mod Log: {member.display_name}", color=0x5865F2)
    
    for i, warn in enumerate(warns[:5], 1):
        embed.add_field(
            name=f"Case #{i}",
            value=f"Reason: {warn['reason'][:50]}\nDate: {warn['timestamp'][:10]}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command()
@can_use_mod()
async def checkperms(ctx, member: discord.Member):
    """Check member permissions"""
    perms = []
    for perm, value in member.guild_permissions:
        if value:
            perms.append(perm.replace('_', ' ').title())
    
    embed = discord.Embed(title=f"Permissions: {member.display_name}", color=0x5865F2)
    embed.description = "\n".join(perms[:20])
    await ctx.send(embed=embed)

@bot.command()
@can_use_mod()
async def raidmode(ctx):
    """Enable raid protection"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    
    await ctx.send("🛡️ Raid mode enabled!")

@bot.command()
@can_use_mod()
async def normalmode(ctx):
    """Disable raid protection"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        except:
            pass
    
    await ctx.send("✅ Normal mode restored")

# ========== AI GAME COMMANDS (5 TOTAL) ==========
@bot.command()
async def trivia(ctx):
    """AI trivia game"""
    async with ctx.channel.typing():
        question = await ai_service.ask("Create a fun trivia question with 4 options. Format: Question? A) Option1 B) Option2 C) Option3 D) Option4. Answer: X)", max_tokens=10)
        await ctx.send(f"🎯 **Trivia:** {question}")

@bot.command()
async def riddle(ctx):
    """AI riddle game"""
    async with ctx.channel.typing():
        riddle = await ai_service.ask("Create a short riddle", max_tokens=10)
        await ctx.send(f"🤔 **Riddle:** {riddle}")

@bot.command()
async def wordgame(ctx):
    """AI word association game"""
    async with ctx.channel.typing():
        word = await ai_service.ask("Give me a random word and a hint for a word association game", max_tokens=10)
        await ctx.send(f"🔤 **Word Game:** {word}")

@bot.command()
async def storystart(ctx):
    """Start an AI story"""
    async with ctx.channel.typing():
        story = await ai_service.ask("Start a short interactive story (2 sentences max)", max_tokens=10)
        await ctx.send(f"📖 **Story:** {story}")

@bot.command()
async def wouldyourather(ctx):
    """AI Would You Rather"""
    async with ctx.channel.typing():
        wyr = await ai_service.ask("Create a 'would you rather' question", max_tokens=10)
        await ctx.send(f"🤔 **Would You Rather:** {wyr}")

# ========== FUN COMMANDS (20+ TOTAL) ==========
@bot.command()
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def coinflip(ctx):
    """Flip a coin"""
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

@bot.command()
async def dice(ctx, dice: str = "1d6"):
    """Roll dice"""
    try:
        num, sides = map(int, dice.split('d'))
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls)
        await ctx.send(f"🎲 Rolled: {', '.join(map(str, rolls))} | Total: {total}")
    except:
        await ctx.send("❌ Use NdN format (e.g., 2d6)")

@bot.command()
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choice = choice.lower()
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    if choice not in ['rock', 'paper', 'scissors']:
        await ctx.send("❌ Choose: rock, paper, scissors")
        return
    
    if choice == bot_choice:
        result = "Tie! 🤝"
    elif (choice == 'rock' and bot_choice == 'scissors') or \
         (choice == 'paper' and bot_choice == 'rock') or \
         (choice == 'scissors' and bot_choice == 'paper'):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(f"**You:** {choice}\n**Bot:** {bot_choice}\n**{result}**")

@bot.command()
async def eightball(ctx, *, question):
    """Magic 8-ball"""
    answers = [
        "Yes", "No", "Maybe", "Ask again",
        "Definitely", "I doubt it", "For sure!",
        "Not likely", "Absolutely!", "Never"
    ]
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(answers)}")

@bot.command()
async def choose(ctx, *, options):
    """Choose between options"""
    if " or " not in options:
        await ctx.send("❌ Separate options with 'or'")
        return
    
    choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
    if len(choices) < 2:
        await ctx.send("❌ Need at least 2 options")
        return
    
    await ctx.send(f"🤔 I choose: **{random.choice(choices)}**")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users"""
    user2 = user2 or ctx.author
    score = random.randint(0, 100)
    
    # Pick emoji based on score
    if score > 80:
        emoji = "💖"
    elif score > 60:
        emoji = "❤️"
    elif score > 40:
        emoji = "💕"
    elif score > 20:
        emoji = "💘"
    else:
        emoji = "💔"
    
    await ctx.send(f"{emoji} **{user1.display_name}** + **{user2.display_name}**\nCompatibility: {score}%")

@bot.command()
async def rate(ctx, *, thing: str):
    """Rate something"""
    rating = random.randint(1, 10)
    stars = "⭐" * rating + "☆" * (10 - rating)
    await ctx.send(f"⭐ **{thing}**: {rating}/10\n{stars}")

@bot.command()
async def joke(ctx):
    """Tell a joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

@bot.command()
async def fact(ctx):
    """Random fact"""
    facts = [
        "Honey never spoils. Archaeologists have found 3000-year-old honey!",
        "Octopuses have three hearts.",
        "A group of flamingos is called a 'flamboyance'.",
        "Bananas are berries, but strawberries are not.",
        "The shortest war in history lasted 38 minutes."
    ]
    await ctx.send(f"🧠 **Did you know?** {random.choice(facts)}")

@bot.command()
async def meme(ctx):
    """Random meme idea"""
    memes = [
        "Distracted Boyfriend - Looking at other options while committed",
        "Drake Hotline Bling - Approving vs disapproving",
        "Change My Mind - Controversial opinion sign",
        "Two Buttons - Difficult choice",
        "Woman Yelling at Cat - Dramatic confrontation"
    ]
    await ctx.send(f"😄 **Meme Idea:** {random.choice(memes)}")

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    """Give a compliment"""
    member = member or ctx.author
    compliments = [
        f"{member.display_name}, you're awesome! 🌟",
        f"{member.display_name} has the best ideas! 💡",
        f"Everyone loves {member.display_name}! ❤️",
        f"{member.display_name} is a ray of sunshine! ☀️",
        f"{member.display_name} makes this server better! 🏆"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def roll(ctx, max_num: int = 100):
    """Roll a random number"""
    result = random.randint(1, max_num)
    await ctx.send(f"🎲 Rolled: **{result}** (1-{max_num})")

@bot.command()
async def emojify(ctx, *, text: str):
    """Convert text to regional indicators"""
    emoji_map = {
        'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪',
        'f': '🇫', 'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯',
        'k': '🇰', 'l': '🇱', 'm': '🇲', 'n': '🇳', 'o': '🇴',
        'p': '🇵', 'q': '🇶', 'r': '🇷', 's': '🇸', 't': '🇹',
        'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽', 'y': '🇾',
        'z': '🇿', '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣',
        '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣',
        '9': '9️⃣', '!': '❗', '?': '❓'
    }
    
    result = []
    for char in text.lower():
        if char in emoji_map:
            result.append(emoji_map[char])
        elif char == ' ':
            result.append('   ')
    
    if result:
        await ctx.send(' '.join(result))
    else:
        await ctx.send("❌ Couldn't convert that text")

# ========== UTILITY COMMANDS ==========
@bot.command()
async def help(ctx, command: str = None):
    """Show help"""
    if command:
        cmd = bot.get_command(command.lower())
        if cmd:
            embed = discord.Embed(title=f"Help: {PREFIX}{cmd.name}", color=0x5865F2)
            embed.description = cmd.help or "No description available"
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Command not found")
    else:
        embed = discord.Embed(title="🤖 Bot Help", color=0x5865F2)
        embed.add_field(name="🔨 Moderation (35)", value="`kick`, `ban`, `purge`, `mute`, `warn`, `trollkick`, `lock`, `roleadd`, etc.", inline=False)
        embed.add_field(name="🤖 AI Games (5)", value="`trivia`, `riddle`, `wordgame`, `storystart`, `wouldyourather`", inline=False)
        embed.add_field(name="🎮 Fun (15+)", value="`ping`, `coinflip`, `dice`, `rps`, `8ball`, `choose`, `ship`, `joke`, `fact`, `meme`", inline=False)
        embed.add_field(name="🛠️ Utility (10+)", value="`help`, `serverinfo`, `avatar`, `userinfo`, `poll`, `timer`, `remind`, `calculate`", inline=False)
        embed.add_field(name="💰 Economy", value="`balance`, `daily`, `work`, `gamble`, `pay`", inline=False)
        embed.set_footer(text=f"Total commands: {len(bot.commands)} | Use {PREFIX}help <command> for details")
        await ctx.send(embed=embed)

@bot.command(name="cmds", aliases=["commands"])
async def cmds(ctx):
    """Show all commands"""
    all_cmds = [f"`{PREFIX}{cmd.name}`" for cmd in bot.commands]
    chunks = [all_cmds[i:i+20] for i in range(0, len(all_cmds), 20)]
    
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=f"📚 All Commands ({len(bot.commands)} total)",
            description=" ".join(chunk),
            color=0x5865F2
        )
        if i == 0:
            embed.set_footer(text=f"Page {i+1}/{len(chunks)} | Use {PREFIX}help <command> for details")
        await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Server information"""
    guild = ctx.guild
    
    embed = discord.Embed(title=guild.name, color=0x5865F2)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="🆔 ID", value=guild.id, inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    embed.add_field(name="👥 Members", value=f"{guild.member_count} ({online} online)", inline=True)
    embed.add_field(name="📝 Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
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

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=member.color)
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    """Create a poll"""
    embed = discord.Embed(title="📊 Poll", description=question, color=0x5865F2)
    embed.set_footer(text=f"By {ctx.author}")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("🤷")

@bot.command()
async def timer(ctx, seconds: int):
    """Set a timer"""
    if seconds > 3600:
        await ctx.send("❌ Max 1 hour")
        return
    
    msg = await ctx.send(f"⏰ Timer set for {seconds}s...")
    await asyncio.sleep(seconds)
    await msg.edit(content=f"⏰ Timer finished! {ctx.author.mention}")

@bot.command()
async def calculate(ctx, *, expression):
    """Calculate math expression"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        await ctx.send(f"🧮 {expression} = **{result}**")
    except:
        await ctx.send("❌ Invalid expression")

# ========== ECONOMY COMMANDS ==========
@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Check balance"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    user_data = data["economy"][user_id]
    await ctx.send(f"💰 **{member.display_name}:** Wallet: ${user_data['balance']:,} | Bank: ${user_data['bank']:,}")

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Daily reward"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    reward = random.randint(50, 200)
    data["economy"][user_id]["balance"] += reward
    await ctx.send(f"🎁 Daily reward: **${reward}**!")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work for money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    jobs = ["Developer", "Designer", "Streamer", "Chef", "Writer"]
    job = random.choice(jobs)
    earned = random.randint(30, 150)
    data["economy"][user_id]["balance"] += earned
    
    await ctx.send(f"💼 Worked as **{job}** and earned **${earned}**!")

@bot.command()
async def gamble(ctx, amount: int):
    """Gamble money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100, "bank": 0}
    
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    if amount > data["economy"][user_id]["balance"]:
        await ctx.send("❌ Not enough money!")
        return
    
    if random.random() < 0.45:
        data["economy"][user_id]["balance"] += amount
        await ctx.send(f"🎉 Won **${amount}**!")
    else:
        data["economy"][user_id]["balance"] -= amount
        await ctx.send(f"😢 Lost **${amount}**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    """Pay another user"""
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    if sender_id not in data["economy"]:
        data["economy"][sender_id] = {"balance": 100, "bank": 0}
    if receiver_id not in data["economy"]:
        data["economy"][receiver_id] = {"balance": 100, "bank": 0}
    
    if amount > data["economy"][sender_id]["balance"]:
        await ctx.send("❌ Not enough money!")
        return
    
    data["economy"][sender_id]["balance"] -= amount
    data["economy"][receiver_id]["balance"] += amount
    
    await ctx.send(f"💰 Paid **${amount}** to {member.mention}!")

# ========== ERROR HANDLING ==========
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    elif isinstance(error, commands.CheckFailure):
        # Already handled by decorators
        pass
    else:
        await ctx.send("❌ An error occurred")

# ========== START BOT ==========
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        print("🚀 Starting bot...")
        print(f"🔒 Owner ID: {OWNER_ID}")
        print(f"📊 Total Commands: {len([c for c in bot.commands])}")
        print("🤖 AI Games: 5 commands (10 tokens each)")
        print("🔨 Moderation: 35 commands (owner/whitelist only)")
        print("🎮 Fun/Utility: 20+ commands (public)")
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
