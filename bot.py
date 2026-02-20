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
import logging
import ast
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= CONFIGURATION =================
TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_TOKEN = os.environ.get("GROQ_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
PREFIX = "!"
OWNER_ID = 1307042499898118246
BOT_START_TIME = time.time()

# ================= DATA STORAGE =================
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
            json.dump(bot_data, f, indent=4)
    except Exception as e:
        logging.error(f"Save error: {e}")

def load_data():
    try:
        with open("bot_data.json", "r") as f:
            data = json.load(f)
            bot_data.update(data)
    except:
        pass

load_data()

# ================= HTTP SERVER WITH ENHANCED HTML =================
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Real-time stats
            uptime_seconds = int(time.time() - BOT_START_TIME)
            uptime_str = str(timedelta(seconds=uptime_seconds))
            guilds = len(bot.guilds) if hasattr(bot, 'guilds') else 0
            
            # Build command lists
            mod_commands = ["kick", "ban", "timeout", "untimeout", "warn", "warnings", "clear", "lock", "unlock", "slowmode", "nick", "role", "mute", "unmute", "trollkick"]
            fun_commands = ["meme", "dice", "coinflip", "8ball", "joke", "rps", "randomfact", "compliment", "insult", "roast", "slap", "hug", "pat", "kiss", "cuddle", "tickle", "poke", "wave", "highfive", "dance", "cry", "laugh", "think", "shrug", "clap", "facepalm", "tableflip", "unflip"]
            util_commands = ["avatar", "serverinfo", "userinfo", "poll", "say", "echo", "embed", "ping", "uptime", "stats", "invite", "support", "math", "choose", "flip"]
            ai_commands = ["ask", "askai", "summary", "translate", "define", "aijoke", "aipoem", "aistory", "aicode", "aiexplain", "aiadvice", "aiidea", "aifact", "airiddle", "aiquote"]
            economy_commands = ["level", "rank", "leaderboard", "daily", "rep"]
            owner_commands = ["whitelist", "blacklist", "showlists"]
            
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>DeepSeek Bot · Dashboard</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                        font-family: 'Segoe UI', Roboto, system-ui, sans-serif;
                    }}
                    body {{
                        background: linear-gradient(145deg, #0a0c10 0%, #1a1e26 100%);
                        color: #e4e7eb;
                        min-height: 100vh;
                        display: flex;
                        justify-content: center;
                        padding: 2rem 1rem;
                    }}
                    .container {{
                        max-width: 1400px;
                        width: 100%;
                    }}
                    /* header */
                    .header {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 2.5rem;
                        padding-bottom: 1.5rem;
                        border-bottom: 1px solid #2a2f3a;
                    }}
                    .title h1 {{
                        font-size: 2.8rem;
                        background: linear-gradient(135deg, #9f7aea, #63b3ed);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        font-weight: 700;
                        letter-spacing: -0.5px;
                    }}
                    .title p {{
                        color: #9aa4b8;
                        margin-top: 0.25rem;
                        font-size: 1.1rem;
                    }}
                    .stats {{
                        display: flex;
                        gap: 2rem;
                        background: #1e222b;
                        padding: 1rem 2rem;
                        border-radius: 60px;
                        border: 1px solid #2f3542;
                        box-shadow: 0 8px 20px rgba(0,0,0,0.6);
                    }}
                    .stat-item {{
                        text-align: center;
                    }}
                    .stat-value {{
                        font-size: 1.8rem;
                        font-weight: 700;
                        color: white;
                        line-height: 1.2;
                    }}
                    .stat-label {{
                        font-size: 0.85rem;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        color: #8f9bb3;
                    }}
                    /* status bar */
                    .status-bar {{
                        background: #1a1e28;
                        border-radius: 40px;
                        padding: 1rem 2rem;
                        margin-bottom: 2.5rem;
                        display: flex;
                        align-items: center;
                        gap: 1.5rem;
                        flex-wrap: wrap;
                        border: 1px solid #2d3340;
                    }}
                    .badge {{
                        background: #10b981;
                        color: white;
                        font-weight: 600;
                        padding: 0.3rem 1rem;
                        border-radius: 30px;
                        font-size: 0.9rem;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                    }}
                    .badge.offline {{ background: #ef4444; }}
                    .info-row {{
                        display: flex;
                        gap: 2rem;
                        flex-wrap: wrap;
                    }}
                    .info-item {{
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        color: #b9c2d4;
                    }}
                    .info-item i {{ font-style: normal; color: #63b3ed; font-weight: 600; }}
                    /* command grid */
                    .section-title {{
                        font-size: 1.8rem;
                        font-weight: 600;
                        margin: 2rem 0 1.2rem 0;
                        color: white;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    .section-title span {{
                        background: #2f3542;
                        padding: 0.2rem 0.8rem;
                        border-radius: 40px;
                        font-size: 1rem;
                        color: #b9c2d4;
                    }}
                    .command-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                        gap: 12px;
                    }}
                    .command-card {{
                        background: #1a1e28;
                        border: 1px solid #2a2f3a;
                        border-radius: 16px;
                        padding: 0.75rem 1rem;
                        font-size: 0.95rem;
                        font-weight: 500;
                        color: #cfd9e8;
                        transition: 0.15s;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }}
                    .command-card:hover {{
                        border-color: #63b3ed;
                        background: #242a36;
                        transform: translateY(-2px);
                        color: white;
                    }}
                    .command-card .prefix {{
                        color: #9f7aea;
                        font-weight: 700;
                        margin-right: 4px;
                    }}
                    .footer {{
                        margin-top: 4rem;
                        text-align: center;
                        color: #6a7285;
                        font-size: 0.9rem;
                        border-top: 1px solid #262c38;
                        padding-top: 2rem;
                    }}
                    .footer a {{
                        color: #9f7aea;
                        text-decoration: none;
                    }}
                    @media (max-width: 700px) {{
                        .header {{
                            flex-direction: column;
                            align-items: start;
                            gap: 1rem;
                        }}
                        .stats {{
                            width: 100%;
                            justify-content: space-around;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- header -->
                    <div class="header">
                        <div class="title">
                            <h1>🤖 DeepSeek Bot</h1>
                            <p>Multi‑purpose Discord bot with 80+ commands</p>
                        </div>
                        <div class="stats">
                            <div class="stat-item">
                                <div class="stat-value">{guilds}</div>
                                <div class="stat-label">SERVERS</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{len(mod_commands)+len(fun_commands)+len(util_commands)+len(ai_commands)+len(economy_commands)+len(owner_commands)}</div>
                                <div class="stat-label">COMMANDS</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{uptime_str.split(':')[0]}h</div>
                                <div class="stat-label">UPTIME</div>
                            </div>
                        </div>
                    </div>

                    <!-- status -->
                    <div class="status-bar">
                        <div class="badge">🟢 ONLINE</div>
                        <div class="info-row">
                            <div class="info-item"><i>📋 Prefix</i> <code style="background:#2d3340; padding:4px 8px; border-radius:8px;">{PREFIX}</code></div>
                            <div class="info-item"><i>👑 Owner</i> <code>1307042499898118246</code></div>
                            <div class="info-item"><i>🤖 AI</i> {'✅ active' if GROQ_TOKEN else '❌ disabled'}</div>
                        </div>
                    </div>

                    <!-- command sections -->
                    <div class="section-title">🛡️ Moderation <span>{len(mod_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in mod_commands)}
                    </div>

                    <div class="section-title">🎉 Fun <span>{len(fun_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in fun_commands)}
                    </div>

                    <div class="section-title">🛠️ Utility <span>{len(util_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in util_commands)}
                    </div>

                    <div class="section-title">🤖 AI <span>{len(ai_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in ai_commands)}
                    </div>

                    <div class="section-title">💰 Economy <span>{len(economy_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in economy_commands)}
                    </div>

                    <div class="section-title">⚙️ Owner only <span>{len(owner_commands)}</span></div>
                    <div class="command-grid">
                        {''.join(f'<div class="command-card"><span class="prefix">!</span>{cmd}</div>' for cmd in owner_commands)}
                    </div>

                    <div class="footer">
                        ⚡ Powered by Groq AI · <a href="https://github.com/your-repo" target="_blank">GitHub</a> · Ready for production
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status_data = {
                "status": "online",
                "uptime": int(time.time() - BOT_START_TIME),
                "owner": OWNER_ID,
                "servers": len(bot.guilds) if hasattr(bot, 'guilds') else 0,
                "commands": len(bot.commands) if hasattr(bot, 'commands') else 0,
                "ai": bool(GROQ_TOKEN)
            }
            self.wfile.write(json.dumps(status_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

def run_http_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), BotHTTPServer)
        logging.info(f"🌐 HTTP server running on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logging.error(f"HTTP server error: {e}")

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ================= CHECKS =================
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
        return ctx.author.guild_permissions.manage_messages
    return commands.check(predicate)

def is_not_blacklisted():
    async def predicate(ctx):
        return ctx.author.id not in bot_data["blacklist"]
    return commands.check(predicate)

# ================= AI FUNCTION =================
async def ask_groq(question, max_tokens=150):
    if not GROQ_TOKEN:
        return "🤖 AI not configured. Ask the owner to set GROQ_TOKEN."
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
                timeout=15
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return f"⚠️ AI error (status {response.status})"
    except asyncio.TimeoutError:
        return "❌ AI request timed out."
    except Exception as e:
        return f"❌ AI failed: {e}"

# ================= EVENTS =================
@bot.event
async def on_ready():
    logging.info(f"✅ {bot.user} connected to Discord.")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Missing permission.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You are not allowed to use this command.")
    else:
        await ctx.send(f"❌ Error: {error}")

# ================= NEW AUTO-RESPOND FEATURE =================
@bot.event
async def on_message(message):
    # Ignore messages from bots (including itself)
    if message.author.bot:
        return

    # Check if message starts with command prefix (so commands are not auto-answered)
    is_command = message.content.startswith(PREFIX)

    # Auto-respond only in the designated channel, not a command, and not from bot
    if not is_command and message.channel.id == 1416480455670239232:
        # Detect question indicators
        content_lower = message.content.lower()
        question_words = ["who", "what", "when", "where", "why", "how"]
        has_question_word = any(word in content_lower for word in question_words)
        has_question_mark = "?" in message.content

        if has_question_word or has_question_mark:
            # Use AI to generate a response
            async with message.channel.typing():
                response = await ask_groq(message.content)
                await message.reply(response)  # Reply to the user's message

    # Always process commands (for prefix messages this will run the command; for others it does nothing)
    await bot.process_commands(message)

# ================= MODERATION COMMANDS (15) =================
@bot.command()
@is_mod()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    if not ctx.guild.me.guild_permissions.kick_members:
        await ctx.send("❌ I lack kick permissions.")
        return
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | {reason}")

@bot.command()
@is_mod()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    if not ctx.guild.me.guild_permissions.ban_members:
        await ctx.send("❌ I lack ban permissions.")
        return
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | {reason}")

@bot.command()
@is_mod()
async def timeout(ctx, member: discord.Member, minutes: int = 10):
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until)
    await ctx.send(f"⏰ {member.mention} timed out {minutes}m")

@bot.command()
@is_mod()
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"✅ Timeout removed for {member.mention}")

@bot.command()
@is_mod()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    user_id = str(member.id)
    if user_id not in bot_data["warnings"]:
        bot_data["warnings"][user_id] = []
    bot_data["warnings"][user_id].append(reason)
    save_data()
    await ctx.send(f"⚠️ Warned {member.mention} | {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)
    warns = bot_data["warnings"].get(user_id, [])
    if not warns:
        await ctx.send(f"✅ {member.display_name} has no warnings.")
    else:
        await ctx.send(f"📋 Warnings for {member.display_name}:\n" + "\n".join(f"• {w}" for w in warns))

@bot.command()
@is_mod()
async def clear(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Amount must be between 1 and 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted {len(deleted)-1} messages.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@is_mod()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked.")

@bot.command()
@is_mod()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")

@bot.command()
@is_mod()
async def slowmode(ctx, seconds: int):
    if seconds < 0 or seconds > 21600:
        await ctx.send("❌ Seconds must be 0-21600.")
        return
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐌 Slowmode set to {seconds}s.")

@bot.command()
@is_mod()
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    await member.edit(nick=nickname)
    await ctx.send(f"✅ Nickname changed.")

@bot.command()
@is_mod()
async def role(ctx, action: str, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return
    if action.lower() in ["add", "+"]:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}.")
    elif action.lower() in ["remove", "-"]:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}.")
    else:
        await ctx.send("❌ Use `add` or `remove`.")

@bot.command()
@is_mod()
async def mute(ctx, member: discord.Member):
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
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 Unmuted {member.mention}")
    else:
        await ctx.send("ℹ️ User is not muted.")

@bot.command()
@is_mod()
async def purge(ctx, amount: int):
    await clear(ctx, amount)

# ================= TROLL KICK (SPECIAL REQUEST) =================
@bot.command()
@is_mod()
async def trollkick(ctx, member: discord.Member):
    """
    Prank a user: send a fake ban message with a rejoin link (valid 10 min).
    """
    if member == ctx.author:
        await ctx.send("❌ You can't troll yourself.")
        return

    invite = await ctx.channel.create_invite(max_age=600, max_uses=1)

    embed = discord.Embed(
        title="🔨 You have been banned from sab hub",
        description=(
            "You have been banned from **sab hub** for violating server rules.\n\n"
            f"||jk heres the link come back: {invite.url}||"
        ),
        color=0xFF0000
    )
    embed.set_footer(text="This is a prank! You're not actually banned.")

    try:
        await member.send(embed=embed)
        await ctx.send(f"😈 Troll kick sent to {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ Couldn't DM that user.")

# ================= FUN COMMANDS (30) =================
@bot.command()
@is_not_blacklisted()
async def meme(ctx):
    memes = [
        "Git commit -m 'Fixed everything.'",
        "It works on my machine.",
        "99 little bugs in the code, 99 little bugs. Fix one bug, compile it again, 102 little bugs in the code.",
        "When the code runs without errors: 👁️👄👁️",
        "I don't always test my code, but when I do, I do it in production."
    ]
    await ctx.send(random.choice(memes))

@bot.command()
@is_not_blacklisted()
async def dice(ctx, sides: int = 6):
    if sides < 2 or sides > 100:
        await ctx.send("❌ Sides must be between 2 and 100.")
        return
    await ctx.send(f"🎲 You rolled **{random.randint(1, sides)}** (1-{sides})")

@bot.command()
@is_not_blacklisted()
async def coinflip(ctx):
    await ctx.send(f"🪙 **{random.choice(['Heads', 'Tails'])}**!")

@bot.command()
@is_not_blacklisted()
async def eightball(ctx, *, question):
    answers = [
        "Yes", "No", "Maybe", "Ask again later", "Definitely", 
        "I doubt it", "Absolutely", "Never", "Signs point to yes"
    ]
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(answers)}")

@bot.command()
@is_not_blacklisted()
async def joke(ctx):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What do you call a fake noodle? An impasta!"
    ]
    await ctx.send(random.choice(jokes))

@bot.command()
@is_not_blacklisted()
async def rps(ctx, choice: str):
    choices = ["rock", "paper", "scissors"]
    if choice.lower() not in choices:
        await ctx.send("❌ Choose `rock`, `paper`, or `scissors`.")
        return
    bot_choice = random.choice(choices)
    result = "It's a tie!"
    if (choice.lower() == "rock" and bot_choice == "scissors") or \
       (choice.lower() == "paper" and bot_choice == "rock") or \
       (choice.lower() == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    elif choice.lower() != bot_choice:
        result = "I win! 😎"
    await ctx.send(f"🤖 I chose **{bot_choice}**.\n{result}")

@bot.command()
@is_not_blacklisted()
async def randomfact(ctx):
    facts = [
        "Honey never spoils! Archaeologists found 3000-year-old honey.",
        "Octopuses have three hearts.",
        "A group of flamingos is called a 'flamboyance'.",
        "Bananas are berries, but strawberries aren't."
    ]
    await ctx.send(f"🧠 **Did you know?** {random.choice(facts)}")

@bot.command()
@is_not_blacklisted()
async def compliment(ctx, member: discord.Member = None):
    member = member or ctx.author
    compliments = [
        f"{member.mention}, you're awesome! ✨",
        f"{member.mention} is the best! 🌟",
        f"Everyone loves {member.mention}! ❤️",
        f"{member.mention} has a great taste in bots! 🤖"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
@is_not_blacklisted()
async def insult(ctx, member: discord.Member = None):
    member = member or ctx.author
    insults = [
        f"{member.mention}, you're like a cloud. When you disappear, it's a beautiful day! ☁️",
        f"If {member.mention} was a vegetable, they'd be a cute-cumber! 🥒",
        f"{member.mention}'s jokes are so bad they're good! 😂",
        f"{member.mention} is proof that even errors can be unique."
    ]
    await ctx.send(random.choice(insults))

@bot.command()
@is_not_blacklisted()
async def roast(ctx, member: discord.Member):
    roasts = [
        f"{member.mention}, you're not stupid; you just have bad luck thinking.",
        f"{member.mention}, you bring everyone so much joy—when you leave.",
        f"{member.mention}, I'd explain it to you, but I left my crayons at home.",
        f"{member.mention}, you're the reason the gene pool needs a lifeguard.",
        f"{member.mention}, if I wanted to hear from an idiot, I'd join a call with you."
    ]
    await ctx.send(random.choice(roasts))

# Interaction commands
@bot.command()
@is_not_blacklisted()
async def slap(ctx, member: discord.Member):
    await ctx.send(f"👋 {ctx.author.mention} slapped {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def hug(ctx, member: discord.Member):
    await ctx.send(f"🤗 {ctx.author.mention} hugged {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def pat(ctx, member: discord.Member):
    await ctx.send(f"👋 {ctx.author.mention} patted {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def kiss(ctx, member: discord.Member):
    await ctx.send(f"😘 {ctx.author.mention} kissed {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def cuddle(ctx, member: discord.Member):
    await ctx.send(f"🥰 {ctx.author.mention} cuddled {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def tickle(ctx, member: discord.Member):
    await ctx.send(f"😆 {ctx.author.mention} tickled {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def poke(ctx, member: discord.Member):
    await ctx.send(f"👉 {ctx.author.mention} poked {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def wave(ctx, member: discord.Member = None):
    target = member.mention if member else "everyone"
    await ctx.send(f"👋 {ctx.author.mention} waves at {target}!")

@bot.command()
@is_not_blacklisted()
async def highfive(ctx, member: discord.Member):
    await ctx.send(f"🖐️ {ctx.author.mention} high-fived {member.mention}!")

@bot.command()
@is_not_blacklisted()
async def dance(ctx):
    dances = ["💃", "🕺", "👯", "🤸", "🧍‍♂️💃"]
    await ctx.send(f"{ctx.author.mention} {random.choice(dances)}")

@bot.command()
@is_not_blacklisted()
async def cry(ctx):
    await ctx.send(f"{ctx.author.mention} cries... 😢")

@bot.command()
@is_not_blacklisted()
async def laugh(ctx):
    laughs = ["😂", "🤣", "😆", "😹", "💀"]
    await ctx.send(f"{ctx.author.mention} {random.choice(laughs)}")

@bot.command()
@is_not_blacklisted()
async def think(ctx, *, thought):
    await ctx.send(f"🤔 {ctx.author.mention} thinks: *{thought}*")

@bot.command()
@is_not_blacklisted()
async def shrug(ctx):
    await ctx.send(f"{ctx.author.mention} ¯\\_(ツ)_/¯")

@bot.command()
@is_not_blacklisted()
async def clap(ctx):
    await ctx.send(f"{ctx.author.mention} 👏")

@bot.command()
@is_not_blacklisted()
async def facepalm(ctx):
    await ctx.send(f"{ctx.author.mention} 🤦")

@bot.command()
@is_not_blacklisted()
async def tableflip(ctx):
    await ctx.send(f"{ctx.author.mention} (╯°□°）╯︵ ┻━┻")

@bot.command()
@is_not_blacklisted()
async def unflip(ctx):
    await ctx.send(f"{ctx.author.mention} ┬─┬ ノ( ゜-゜ノ)")

# ================= UTILITY COMMANDS (15) =================
@bot.command()
@is_not_blacklisted()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar")
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, description=guild.description, color=0x5865F2)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, style="R"))
    await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown")
    embed.add_field(name="Registered", value=discord.utils.format_dt(member.created_at, style="R"))
    roles = ", ".join([r.mention for r in member.roles[1:]]) or "None"
    embed.add_field(name="Roles", value=roles, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def poll(ctx, *, question):
    message = await ctx.send(f"📊 **{question}**\n\n👍 Yes  |  👎 No")
    await message.add_reaction("👍")
    await message.add_reaction("👎")

@bot.command()
@is_not_blacklisted()
async def say(ctx, *, text):
    await ctx.send(text)

@bot.command()
@is_not_blacklisted()
async def echo(ctx, channel: discord.TextChannel, *, text):
    await channel.send(text)
    await ctx.send(f"✅ Message sent to {channel.mention}")

@bot.command()
@is_not_blacklisted()
async def embed(ctx, *, text):
    embed = discord.Embed(description=text, color=0x5865F2)
    await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
@is_not_blacklisted()
async def uptime(ctx):
    uptime_seconds = int(time.time() - BOT_START_TIME)
    uptime_str = str(timedelta(seconds=uptime_seconds))
    await ctx.send(f"⏱️ Uptime: **{uptime_str}**")

@bot.command()
@is_not_blacklisted()
async def stats(ctx):
    embed = discord.Embed(title="📊 Bot Stats", color=0x5865F2)
    embed.add_field(name="Servers", value=len(bot.guilds))
    embed.add_field(name="Users", value=sum(g.member_count for g in bot.guilds))
    embed.add_field(name="Commands", value=len(bot.commands))
    embed.add_field(name="Uptime", value=str(timedelta(seconds=int(time.time()-BOT_START_TIME))))
    await ctx.send(embed=embed)

@bot.command()
@is_not_blacklisted()
async def invite(ctx):
    permissions = discord.Permissions(administrator=True)
    url = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    await ctx.send(f"🔗 Invite me:\n{url}")

@bot.command()
@is_not_blacklisted()
async def support(ctx):
    await ctx.send("📞 Join the support server: https://discord.gg/your-invite")

@bot.command()
@is_not_blacklisted()
async def math(ctx, *, expression):
    try:
        # Safe evaluation of literals only
        result = ast.literal_eval(expression)
        await ctx.send(f"🧮 `{expression}` = **{result}**")
    except:
        await ctx.send("❌ Invalid expression or unsafe operation.")

@bot.command()
@is_not_blacklisted()
async def choose(ctx, *options):
    if len(options) < 2:
        await ctx.send("❌ Provide at least two options separated by spaces.")
        return
    await ctx.send(f"🤔 I choose: **{random.choice(options)}**")

@bot.command()
@is_not_blacklisted()
async def flip(ctx, text: str):
    """Flip text upside down"""
    mapping = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                            "ɐqɔpǝɟbɥıظʞןɯuodbɹsʇnʌʍxʎzⱯᗺƆᗡƎℲ⅁HIſꞰ⅂WᴎOԀꝹᴚS⟘∩Ʌ⅄X⅄Z")
    flipped = text.translate(mapping)[::-1]
    await ctx.send(f"🔄 {flipped}")

# ================= AI COMMANDS (15) =================
@bot.command()
@is_not_blacklisted()
async def ask(ctx, *, question):
    async with ctx.channel.typing():
        response = await ask_groq(question)
        await ctx.send(f"🤖 **Answer:** {response}")

@bot.command()
@is_not_blacklisted()
async def askai(ctx, *, question):
    await ask(ctx, question=question)

@bot.command()
@is_not_blacklisted()
async def summary(ctx, *, text):
    async with ctx.channel.typing():
        response = await ask_groq(f"Summarize this: {text}", max_tokens=200)
        await ctx.send(f"📝 **Summary:** {response}")

@bot.command()
@is_not_blacklisted()
async def translate(ctx, lang: str, *, text):
    async with ctx.channel.typing():
        response = await ask_groq(f"Translate this to {lang}: {text}", max_tokens=200)
        await ctx.send(f"🌍 **Translation to {lang}:** {response}")

@bot.command()
@is_not_blacklisted()
async def define(ctx, *, word):
    async with ctx.channel.typing():
        response = await ask_groq(f"Define '{word}'", max_tokens=100)
        await ctx.send(f"📖 **Definition:** {response}")

@bot.command()
@is_not_blacklisted()
async def aijoke(ctx):
    async with ctx.channel.typing():
        response = await ask_groq("Tell me a funny joke", max_tokens=100)
        await ctx.send(f"😂 **AI Joke:** {response}")

@bot.command()
@is_not_blacklisted()
async def aipoem(ctx, *, topic):
    async with ctx.channel.typing():
        response = await ask_groq(f"Write a short poem about {topic}", max_tokens=200)
        await ctx.send(f"📜 **Poem about {topic}:**\n{response}")

@bot.command()
@is_not_blacklisted()
async def aistory(ctx, *, prompt):
    async with ctx.channel.typing():
        response = await ask_groq(f"Write a very short story about: {prompt}", max_tokens=300)
        await ctx.send(f"📖 **Story:** {response}")

@bot.command()
@is_not_blacklisted()
async def aicode(ctx, *, description):
    async with ctx.channel.typing():
        response = await ask_groq(f"Generate code snippet for: {description}. Provide only code with brief explanation.", max_tokens=400)
        await ctx.send(f"💻 **Code:**\n{response}")

@bot.command()
@is_not_blacklisted()
async def aiexplain(ctx, *, concept):
    async with ctx.channel.typing():
        response = await ask_groq(f"Explain '{concept}' in simple terms", max_tokens=200)
        await ctx.send(f"🔍 **Explanation:** {response}")

@bot.command()
@is_not_blacklisted()
async def aiadvice(ctx, *, topic):
    async with ctx.channel.typing():
        response = await ask_groq(f"Give me advice about {topic}", max_tokens=200)
        await ctx.send(f"💡 **Advice:** {response}")

@bot.command()
@is_not_blacklisted()
async def aiidea(ctx, *, category):
    async with ctx.channel.typing():
        response = await ask_groq(f"Give me a creative idea for {category}", max_tokens=150)
        await ctx.send(f"💭 **Idea:** {response}")

@bot.command()
@is_not_blacklisted()
async def aifact(ctx):
    async with ctx.channel.typing():
        response = await ask_groq("Tell me a random interesting fact", max_tokens=100)
        await ctx.send(f"🧠 **AI Fact:** {response}")

@bot.command()
@is_not_blacklisted()
async def airiddle(ctx):
    async with ctx.channel.typing():
        response = await ask_groq("Give me a riddle, then provide the answer after a pause", max_tokens=150)
        await ctx.send(f"🤔 **Riddle:** {response}")

@bot.command()
@is_not_blacklisted()
async def aiquote(ctx):
    async with ctx.channel.typing():
        response = await ask_groq("Give me an inspirational quote", max_tokens=100)
        await ctx.send(f"✨ **Quote:** {response}")

# ================= ECONOMY (MOCK) (5) =================
@bot.command()
@is_not_blacklisted()
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"📊 {member.mention} is level **{random.randint(1, 20)}**!")

@bot.command()
@is_not_blacklisted()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"🏆 {member.mention} is rank **#{random.randint(1, 100)}**!")

@bot.command()
@is_not_blacklisted()
async def leaderboard(ctx):
    members = random.sample([m for m in ctx.guild.members if not m.bot], min(5, len(ctx.guild.members)))
    lines = []
    for i, m in enumerate(members, 1):
        lines.append(f"{i}. {m.mention} - {random.randint(100, 5000)} XP")
    await ctx.send("📈 **Leaderboard**\n" + "\n".join(lines))

@bot.command()
@is_not_blacklisted()
async def daily(ctx):
    await ctx.send(f"✅ {ctx.author.mention}, you claimed **{random.randint(50, 200)}** coins!")

@bot.command()
@is_not_blacklisted()
async def rep(ctx, member: discord.Member):
    await ctx.send(f"⭐ {ctx.author.mention} gave reputation to {member.mention}!")

# ================= WHITELIST/BLACKLIST (OWNER ONLY) =================
@bot.command()
@is_owner()
async def whitelist(ctx, action: str, member: discord.Member):
    if action.lower() in ["add", "+"]:
        if member.id not in bot_data["whitelist"]:
            bot_data["whitelist"].append(member.id)
            save_data()
            await ctx.send(f"✅ Added {member.mention} to whitelist.")
        else:
            await ctx.send("ℹ️ Already whitelisted.")
    elif action.lower() in ["remove", "-"]:
        if member.id in bot_data["whitelist"]:
            bot_data["whitelist"].remove(member.id)
            save_data()
            await ctx.send(f"✅ Removed {member.mention} from whitelist.")
        else:
            await ctx.send("ℹ️ Not in whitelist.")
    else:
        await ctx.send("❌ Use `add` or `remove`.")

@bot.command()
@is_owner()
async def blacklist(ctx, action: str, member: discord.Member):
    if action.lower() in ["add", "+"]:
        if member.id not in bot_data["blacklist"]:
            bot_data["blacklist"].append(member.id)
            save_data()
            await ctx.send(f"✅ Added {member.mention} to blacklist.")
        else:
            await ctx.send("ℹ️ Already blacklisted.")
    elif action.lower() in ["remove", "-"]:
        if member.id in bot_data["blacklist"]:
            bot_data["blacklist"].remove(member.id)
            save_data()
            await ctx.send(f"✅ Removed {member.mention} from blacklist.")
        else:
            await ctx.send("ℹ️ Not in blacklist.")
    else:
        await ctx.send("❌ Use `add` or `remove`.")

@bot.command()
@is_owner()
async def showlists(ctx):
    embed = discord.Embed(title="📋 Permission Lists", color=0x5865F2)
    wl = [f"<@{uid}>" for uid in bot_data["whitelist"]]
    bl = [f"<@{uid}>" for uid in bot_data["blacklist"]]
    embed.add_field(name=f"✅ Whitelist ({len(wl)})", value="\n".join(wl) if wl else "Empty", inline=False)
    embed.add_field(name=f"❌ Blacklist ({len(bl)})", value="\n".join(bl) if bl else "Empty", inline=False)
    await ctx.send(embed=embed)

# ================= HELP COMMAND =================
@bot.command()
async def help(ctx, command: str = None):
    if command:
        cmd = bot.get_command(command)
        if not cmd:
            await ctx.send(f"❌ Command `{command}` not found.")
            return
        embed = discord.Embed(title=f"Help: {PREFIX}{cmd.name}", description=cmd.help or "No description.", color=0x5865F2)
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🤖 DeepSeek Bot Help",
        description=f"Prefix: `{PREFIX}` | Owner: <@{OWNER_ID}>",
        color=0x5865F2
    )
    embed.add_field(
        name="🛡️ Moderation (15)",
        value="`kick`, `ban`, `timeout`, `untimeout`, `warn`, `warnings`, `clear`/`purge`, `lock`, `unlock`, `slowmode`, `nick`, `role`, `mute`, `unmute`, `trollkick`",
        inline=False
    )
    embed.add_field(
        name="🎉 Fun (30)",
        value="`meme`, `dice`, `coinflip`, `8ball`, `joke`, `rps`, `randomfact`, `compliment`, `insult`, `roast`, `slap`, `hug`, `pat`, `kiss`, `cuddle`, `tickle`, `poke`, `wave`, `highfive`, `dance`, `cry`, `laugh`, `think`, `shrug`, `clap`, `facepalm`, `tableflip`, `unflip`",
        inline=False
    )
    embed.add_field(
        name="🛠️ Utility (15)",
        value="`avatar`, `serverinfo`, `userinfo`, `poll`, `say`, `echo`, `embed`, `ping`, `uptime`, `stats`, `invite`, `support`, `math`, `choose`, `flip`",
        inline=False
    )
    embed.add_field(
        name="🤖 AI (15)",
        value="`ask`/`askai`, `summary`, `translate`, `define`, `aijoke`, `aipoem`, `aistory`, `aicode`, `aiexplain`, `aiadvice`, `aiidea`, `aifact`, `airiddle`, `aiquote`",
        inline=False
    )
    embed.add_field(
        name="💰 Economy (Mock) (5)",
        value="`level`, `rank`, `leaderboard`, `daily`, `rep`",
        inline=False
    )
    embed.add_field(
        name="⚙️ Admin (Owner Only)",
        value="`whitelist`, `blacklist`, `showlists`",
        inline=False
    )
    embed.set_footer(text=f"Total commands: {len(bot.commands)}")
    await ctx.send(embed=embed)

# ================= MAIN =================
if __name__ == "__main__":
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    logging.info("🚀 Starting DeepSeek Bot...")

    if not TOKEN or TOKEN.strip() == "":
        logging.error("❌ DISCORD_TOKEN missing.")
        sys.exit(1)

    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"❌ Bot crashed: {e}")
        sys.exit(1)
