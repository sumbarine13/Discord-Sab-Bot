import os
import asyncio
import re
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from aiohttp import web
from groq import Groq
from dotenv import load_dotenv

# =====================================================
# ENVIRONMENT
# =====================================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_TOKEN = os.getenv("GROQ_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
OWNER_ID = 1307042499898118246

if not DISCORD_TOKEN or not GROQ_TOKEN:
    raise RuntimeError("Missing required environment variables")

# =====================================================
# DISCORD SETUP
# =====================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =====================================================
# GROQ SETUP
# =====================================================
ai = Groq(api_key=GROQ_TOKEN)
GROQ_MODEL = "llama-3.3-70b-versatile"

# =====================================================
# RULES
# =====================================================
ALLOWED_PREFIXES = [
    "who", "what", "when", "where", "which",
    "why", "how", "should", "advice",
    "suggestion", "suggestions",
    "explanation", "explanations",
    "instruction", "instructions",
    "opinion", "opinions"
]

FORBIDDEN_INPUT = [
    "ignore instructions", "override", "system",
    "developer", "jailbreak", "bypass",
    "rules", "how were you made", "are you ai",
    "chatgpt", "openai", "model", "prompt"
]

FORBIDDEN_OUTPUT = [
    "as an ai", "language model", "openai",
    "groq", "model", "prompt", "system",
    "i was trained", "i cannot"
]

SEXUAL_TERMS = [
    "sex", "nsfw", "porn", "nude",
    "explicit", "erotic"
]

# =====================================================
# HELPERS
# =====================================================
def is_allowed_question(text: str) -> bool:
    t = text.lower().strip()
    if any(x in t for x in FORBIDDEN_INPUT):
        return False
    if any(x in t for x in SEXUAL_TERMS):
        return False
    for p in ALLOWED_PREFIXES:
        if t.startswith(p) or t.startswith(p[:3]):
            return True
    return False

def response_is_safe(text: str) -> bool:
    t = text.lower()
    if any(x in t for x in FORBIDDEN_OUTPUT):
        return False
    if any(x in t for x in SEXUAL_TERMS):
        return False
    return True

def owner_only(i: discord.Interaction) -> bool:
    return i.user.id == OWNER_ID

# =====================================================
# AI CALL
# =====================================================
async def ask_ai(question: str) -> Optional[str]:
    if not is_allowed_question(question):
        return None

    try:
        completion = ai.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": question}
            ],
            temperature=0.4,
            max_tokens=300
        )

        answer = completion.choices[0].message.content.strip()

        if not response_is_safe(answer):
            return None

        return answer

    except Exception:
        return None

# =====================================================
# EVENTS
# =====================================================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if not is_allowed_question(message.content):
        return

    reply = await ask_ai(message.content)
    if reply:
        await message.channel.send(reply)

    await bot.process_commands(message)

# =====================================================
# SLASH COMMANDS (OWNER)
# =====================================================
@tree.command(name="lock_channel")
async def lock_channel(i: discord.Interaction):
    if not owner_only(i):
        return
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("Channel locked.", ephemeral=True)

@tree.command(name="unlock_channel")
async def unlock_channel(i: discord.Interaction):
    if not owner_only(i):
        return
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("Channel unlocked.", ephemeral=True)

@tree.command(name="slowmode")
async def slowmode(i: discord.Interaction, seconds: int):
    if not owner_only(i):
        return
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message("Slowmode set.", ephemeral=True)

@tree.command(name="un_slowmode")
async def un_slowmode(i: discord.Interaction):
    if not owner_only(i):
        return
    await i.channel.edit(slowmode_delay=0)
    await i.response.send_message("Slowmode disabled.", ephemeral=True)

@tree.command(name="kick")
async def kick(i: discord.Interaction, member: discord.Member):
    if not owner_only(i):
        return
    await member.kick()
    await i.response.send_message("Member kicked.", ephemeral=True)

@tree.command(name="un_kick")
async def un_kick(i: discord.Interaction):
    if not owner_only(i):
        return
    await i.response.send_message("Kick cannot be undone.", ephemeral=True)

@tree.command(name="ban")
async def ban(i: discord.Interaction, member: discord.Member):
    if not owner_only(i):
        return
    await member.ban()
    await i.response.send_message("Member banned.", ephemeral=True)

@tree.command(name="un_ban")
async def un_ban(i: discord.Interaction):
    if not owner_only(i):
        return
    await i.response.send_message("Ban cannot be undone.", ephemeral=True)

# (You can add more un_/toggle commands using this same pattern)

# =====================================================
# REAL HTTP SERVER (RENDER PORT)
# =====================================================
async def health(request):
    return web.Response(text="OK")

async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT
    )
    await site.start()
    print(f"HTTP server running on port {PORT}")

# =====================================================
# MAIN
# =====================================================
async def main():
    await start_web()
    await bot.start(DISCORD_TOKEN)

asyncio.run(main())
