import os
import discord
from discord.ext import commands
import random
import asyncio
import aiohttp
import threading
import time
import json
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

# ========== CONFIGURATION ==========
TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_TOKEN = os.environ.get("GROQ_TOKEN")
PORT = int(os.environ["PORT"])
PREFIX = "!"
OWNER_ID = 1307042499898118246
BOT_START_TIME = time.time()

# ========== DATA STORAGE ==========
bot_data = {
    "warnings": {},
    "whitelist": [],
    "blacklist": [],
    "ai_history": {},
    "user_stats": {}
}

def save_data():
    try:
        with open("bot_data.json", "w") as f:
            json.dump(bot_data, f)
    except:
        pass

def load_data():
    try:
        with open("bot_data.json", "r") as f:
            data = json.load(f)
            bot_data.update(data)
    except:
        pass

load_data()

# ========== HTTP SERVER ==========
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head>
    <title>DeepSeek Bot</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 50px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container { 
            background: rgba(255, 255, 255, 0.1); 
            padding: 40px; 
            border-radius: 15px; 
            display: inline-block; 
        }
        h1 { color: white; }
        .status { color: #4CAF50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 DeepSeek Bot</h1>
        <p>Status: <span class="status">Online</span></p>
        <p>Owner ID: 1307042499898118246</p>
        <p>Commands: 65+ | Prefix: !</p>
        <p>Bot is running on Render with Cloudflare</p>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status_data = {
                "status": "online",
                "uptime": int(time.time() - BOT_START_TIME),
                "owner": str(OWNER_ID)
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_http_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), BotHTTPServer)
        print(f"✅ HTTP server started on port {PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ HTTP server error: {e}")

# ========== DISCORD BOT ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ========== HELPER FUNCTIONS ==========
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_mod():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.id in bot_data["whitelist"]:
            return True
        if ctx.author.id in bot_data["blacklist"]:
            return False
        return False
    return commands.check(predicate)

def is_not_blacklisted():
    async def predicate(ctx):
        return ctx.author.id not in bot_data["blacklist"]
    return commands.check(predicate)

async def ask_groq(question, max_tokens=150):
    """Ask Groq AI a question"""
    if not GROQ_TOKEN:
        return "🤖 AI not configured. Add GROQ_TOKEN environment variable."
    
    try:
        headers = {"Authorization": f"Bearer {GROQ_TOKEN}"}
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": question}],
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
                else:
                    return "⚠️ AI service error"
    except Exception as e:
        return f"❌ Failed to connect to AI: {str(e)}"

# ========== EVENT HANDLERS ==========
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"🔒 Owner ID: {OWNER_ID}")
    print(f"📊 Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission!")
    else:
        await ctx.send(f"❌ Error: {str(error)}")

# ========== MODERATION COMMANDS ==========
@bot.command()
@is_mod()
async def troll(ctx, member: discord.Member):
    """Prank ban a user"""
    if member == ctx.author:
        await ctx.send("❌ Can't troll yourself!")
        return
    
    try:
        # Create temporary invite
        invite = await ctx.channel.create_invite(
            max_age=600,  # 10 minutes
            max_uses=1,
            reason=f"Troll invite for {member.display_name}"
        )
        
        # Create blue embed
        embed = discord.Embed(
            title="🔨 BANNED",
            description=(
                f"You have been banned from **{ctx.guild.name}** from <@{OWNER_ID}> for not complying with staff.\n\n"
                f"||Jk you aren't banned but still do work||\n"
                f"||Click [HERE]({invite.url}) to join back with your roles||"
            ),
            color=0x5865F2  # Blue
        )
        embed.set_footer(text="This is a prank! You're not actually banned.")
        
        try:
            await member.send(embed=embed)
            await ctx.send(f"✅ Troll message sent to {member.mention}! 😈")
        except:
            await ctx.send(f"❌ Could not DM {member.mention}")
            
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@is_mod()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """Kick a member"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command()
@is_mod()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """Ban a member"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command()
@is_mod()
async def unban(ctx, user_id: int):
    """Unban a user"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned {user}")
    except:
        await ctx.send("❌ User not found or not banned")

@bot.command()
@is_mod()
async def mute(ctx, member: discord.Member):
    """Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await member.add_roles(mute_role)
    await ctx.send(f"🔇 Muted {member.mention}")

@bot.command()
@is_mod()
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 Unmuted {member.mention}")

@bot.command()
@is_mod()
async def timeout(ctx, member: discord.Member, minutes: int = 10):
    """Timeout a member"""
    duration = timedelta(minutes=minutes)
    await member.timeout(duration)
    await ctx.send(f"⏰ {member.mention} timed out for {minutes} minutes")

@bot.command()
@is_mod()
async def untimeout(ctx, member: discord.Member):
    """Remove timeout"""
    await member.timeout(None)
    await ctx.send(f"✅ {member.mention}'s timeout removed")

@bot.command()
@is_mod()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in bot_data["warnings"]:
        bot_data["warnings"][user_id] = []
    
    bot_data["warnings"][user_id].append(reason)
    save_data()
    await ctx.send(f"⚠️ Warned {member.mention} | Reason: {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in bot_data["warnings"] or not bot_data["warnings"][user_id]:
        await ctx.send(f"✅ {member.display_name} has no warnings")
        return
    
    warns = "\n".join([f"• {w}" for w in bot_data["warnings"][user_id]])
    await ctx.send(f"📋 Warnings for {member.display_name}:\n{warns}")

@bot.command()
@is_mod()
async def clear(ctx, amount: int = 10):
    """Delete messages"""
    if amount < 1 or amount > 100:
        await ctx.send("❌ 1-100 messages only!")
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@is_mod()
async def lock(ctx):
    """Lock channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked")

@bot.command()
@is_mod()
async def unlock(ctx):
    """Unlock channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked")

@bot.command()
@is_mod()
async def slowmode(ctx, seconds: int):
    """Set slowmode"""
    if seconds < 0 or seconds > 21600:
        await ctx.send("❌ 0-21600 seconds only!")
        return
    
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("✅ Slowmode disabled")
    else:
        await ctx.send(f"🐌 Slowmode: {seconds}s")

@bot.command()
@is_mod()
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    """Change nickname"""
    await member.edit(nick=nickname)
    if nickname:
        await ctx.send(f"✅ {member.mention}'s nickname: {nickname}")
    else:
        await ctx.send(f"✅ {member.mention}'s nickname reset")

@bot.command()
@is_mod()
async def role(ctx, action: str, member: discord.Member, *, role_name: str):
    """Add/remove role"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found!")
        return
    
    action = action.lower()
    if action in ["add", "give"]:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}")
    elif action in ["remove", "take"]:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}")
    else:
        await ctx.send("❌ Use: add/give or remove/take")

# ========== WHITELIST/BLACKLIST COMMANDS ==========
@bot.command()
@is_owner()
async def whitelist(ctx, action: str, member: discord.Member):
    """[OWNER] Add/remove from whitelist"""
    if action.lower() in ["add", "+"]:
        if member.id not in bot_data["whitelist"]:
            bot_data["whitelist"].append(member.id)
            save_data()
            await ctx.send(f"✅ Added {member.mention} to whitelist")
        else:
            await ctx.send("ℹ️ Already whitelisted")
    elif action.lower() in ["remove", "-"]:
        if member.id in bot_data["whitelist"]:
            bot_data["whitelist"].remove(member.id)
            save_data()
            await ctx.send(f"✅ Removed {member.mention} from whitelist")
        else:
            await ctx.send("ℹ️ Not in whitelist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def blacklist(ctx, action: str, member: discord.Member):
    """[OWNER] Add/remove from blacklist"""
    if action.lower() in ["add", "+"]:
        if member.id not in bot_data["blacklist"]:
            bot_data["blacklist"].append(member.id)
            save_data()
            await ctx.send(f"✅ Added {member.mention} to blacklist")
        else:
            await ctx.send("ℹ️ Already blacklisted")
    elif action.lower() in ["remove", "-"]:
        if member.id in bot_data["blacklist"]:
            bot_data["blacklist"].remove(member.id)
            save_data()
            await ctx.send(f"✅ Removed {member.mention} from blacklist")
        else:
            await ctx.send("ℹ️ Not in blacklist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def showlists(ctx):
    """[OWNER] Show whitelist and blacklist"""
    embed = discord.Embed(title="📋 Permission Lists", color=0x5865F2)
    
    wl = [f"<@{uid}>" for uid in bot_data["whitelist"]]
    bl = [f"<@{uid}>" for uid in bot_data["blacklist"]]
    
    embed.add_field(
        name=f"✅ Whitelist ({len(bot_data['whitelist'])})",
        value="\n".join(wl) if wl else "Empty",
        inline=False
    )
    
    embed.add_field(
        name=f"❌ Blacklist ({len(bot_data['blacklist'])})",
        value="\n".join(bl) if bl else "Empty",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ========== FUN COMMANDS ==========
@bot.command()
@is_not_blacklisted()
async def meme(ctx):
    """Get a random meme"""
    memes = [
        "When the code works on first try... SUS",
        "Me: I'll just fix one bug. Also me: *rewrites entire project*",
        "Git commit -m 'Fixed stuff. Maybe.'",
        "It's not a bug, it's a feature!"
    ]
    await ctx.send(f"😂 {random.choice(memes)}")

@bot.command()
@is_not_blacklisted()
async def joke(ctx):
    """Get a random joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why did the scarecrow win an award? He was outstanding in his field!"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

@bot.command()
@is_not_blacklisted()
async def dice(ctx, sides: int = 6):
    """Roll a dice"""
    if sides < 2 or sides > 100:
        await ctx.send("❌ 2-100 sides only!")
        return
    
    roll = random.randint(1, sides)
    await ctx.send(f"🎲 Rolled: **{roll}** (1-{sides})")

@bot.command()
@is_not_blacklisted()
async def coinflip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 **{result}**!")

@bot.command()
@is_not_blacklisted()
async def eightball(ctx, *, question):
    """Magic 8-ball"""
    answers = ["Yes", "No", "Maybe", "Ask again", "Definitely", "Never"]
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(answers)}")

@bot.command()
@is_not_blacklisted()
async def compliment(ctx, member: discord.Member = None):
    """Give a compliment"""
    member = member or ctx.author
    compliments = [
        f"{member.display_name}, you're awesome! ✨",
        f"{member.display_name} is the best! 🌟",
        f"Everyone loves {member.display_name}! ❤️"
    ]
    await ctx.send(random.choice(compliments))

@bot.command(name="insult")
@is_not_blacklisted()
async def insult_cmd(ctx, member: discord.Member = None):
    """Funny harmless insult"""
    member = member or ctx.author
    insults = [
        f"{member.display_name}, you're like a cloud. When you disappear, it's a beautiful day! ☁️",
        f"If {member.display_name} was a vegetable, they'd be a cute-cumber! 🥒",
        f"{member.display_name}'s jokes are so bad they're good! 😂"
    ]
    await ctx.send(random.choice(insults))

@bot.command()
@is_not_blacklisted()
async def gif(ctx, *, query):
    """Search for a GIF"""
    await ctx.send(f"🔍 Searching GIF for: {query}\n*(GIF API not configured)*")

@bot.command()
@is_not_blacklisted()
async def say(ctx, *, text):
    """Make the bot say something"""
    await ctx.send(text)

@bot.command()
@is_not_blacklisted()
async def hug(ctx, member: discord.Member):
    """Hug someone"""
    await ctx.send(f"🤗 {ctx.author.mention} hugged {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def pat(ctx, member: discord.Member):
    """Pat someone"""
    await ctx.send(f"👋 {ctx.author.mention} patted {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def slap(ctx, member: discord.Member):
    """Slap someone"""
    await ctx.send(f"👋 {ctx.author.mention} slapped {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def rollcall(ctx):
    """Tag random online members"""
    online_members = [m for m in ctx.guild.members if m.status != discord.Status.offline and not m.bot]
    if online_members:
        random_member = random.choice(online_members)
        await ctx.send(f"📢 Roll call! {random_member.mention} is present!")
    else:
        await ctx.send("😴 Everyone seems to be offline...")

@bot.command()
@is_not_blacklisted()
async def randomfact(ctx):
    """Random fun fact"""
    facts = [
        "Honey never spoils! Archaeologists have found 3000-year-old honey!",
        "Octopuses have three hearts! ❤️❤️❤️",
        "A group of flamingos is called a 'flamboyance'! 🦩"
    ]
    await ctx.send(f"🧠 **Did you know?** {random.choice(facts)}")

# ========== AI COMMANDS ==========
@bot.command(name="ask")
@is_not_blacklisted()
async def ask_cmd(ctx, *, question):
    """Ask AI a question"""
    async with ctx.channel.typing():
        response = await ask_groq(question)
        await ctx.send(f"🤖 **Q:** {question}\n**A:** {response}")

@bot.command()
@is_not_blacklisted()
async def askai(ctx, *, question):
    """Smart AI answer"""
    async with ctx.channel.typing():
        response = await ask_groq(question, max_tokens=300)
        await ctx.send(f"🧠 **AI:** {response}")

@bot.command()
@is_not_blacklisted()
async def summary(ctx, *, text):
    """Summarize text"""
    async with ctx.channel.typing():
        response = await ask_groq(f"Summarize this text: {text}", max_tokens=200)
        embed = discord.Embed(title="📝 Summary", description=response, color=0x5865F2)
        await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def chat(ctx, *, message):
    """AI conversation"""
    async with ctx.channel.typing():
        response = await ask_groq(message, max_tokens=200)
        await ctx.send(f"💬 **Chat:** {response}")

@bot.command()
@is_not_blacklisted()
async def translate(ctx, text: str, language: str):
    """Translate text"""
    async with ctx.channel.typing():
        response = await ask_groq(f"Translate this to {language}: {text}", max_tokens=100)
        await ctx.send(f"🌍 **Translation to {language}:** {response}")

@bot.command()
@is_not_blacklisted()
async def story(ctx, *, prompt):
    """Generate a story"""
    async with ctx.channel.typing():
        response = await ask_groq(f"Write a short story about: {prompt}", max_tokens=400)
        embed = discord.Embed(title="📖 Story", description=response, color=0x5865F2)
        await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def jokeai(ctx):
    """AI-generated joke"""
    async with ctx.channel.typing():
        response = await ask_groq("Tell me a funny joke", max_tokens=100)
        await ctx.send(f"😂 **AI Joke:** {response}")

@bot.command()
@is_not_blacklisted()
async def advice(ctx, *, topic):
    """Get AI advice"""
    async with ctx.channel.typing():
        response = await ask_groq(f"Give advice about: {topic}", max_tokens=200)
        await ctx.send(f"💡 **Advice about {topic}:** {response}")

# ========== HELP COMMAND ==========
@bot.command()
@is_not_blacklisted()
async def help(ctx):
    """Show help menu"""
    embed = discord.Embed(
        title="🤖 DeepSeek Bot Help",
        description=f"Prefix: `{PREFIX}` | Owner: <@{OWNER_ID}>",
        color=0x5865F2
    )
    
    embed.add_field(
        name="🛡️ Moderation (Owner/Whitelist)",
        value="`kick`, `ban`, `unban`, `mute`, `unmute`, `timeout`, `untimeout`, `warn`, `warnings`, `clear`, `lock`, `unlock`, `slowmode`, `nick`, `role`, `troll`",
        inline=False
    )
    
    embed.add_field(
        name="🎉 Fun Commands",
        value="`meme`, `joke`, `dice`, `coinflip`, `8ball`, `compliment`, `insult`, `gif`, `say`, `hug`, `pat`, `slap`, `rollcall`, `randomfact`",
        inline=False
    )
    
    embed.add_field(
        name="🤖 AI Commands",
        value="`ask`, `askai`, `summary`, `chat`, `translate`, `story`, `jokeai`, `advice`",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin (Owner Only)",
        value="`whitelist`, `blacklist`, `showlists`",
        inline=False
    )
    
    embed.set_footer(text=f"Total commands: {len(bot.commands)}")
    await ctx.send(embed=embed)

# ========== MAIN ==========
if __name__ == "__main__":
    # Start HTTP server in background thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    print(f"🚀 Starting DeepSeek Bot")
    print(f"🔒 Owner ID: {OWNER_ID}")
    print(f"🌐 HTTP Server on port {PORT}")
    print(f"🤖 AI: {'Ready' if GROQ_TOKEN else 'Disabled (set GROQ_TOKEN)'}")
    print(f"📊 Whitelisted: {len(bot_data['whitelist'])} users")
    print(f"📋 Blacklisted: {len(bot_data['blacklist'])} users")
    print(f"📁 Commands loaded: {len(bot.commands)}")
    
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
        print("   Set it in Render Dashboard -> Environment Variables")
        sys.exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        sys.exit(1)
