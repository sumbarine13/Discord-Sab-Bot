import os
import discord
from discord.ext import commands
from discord import app_commands
from groq import Groq
import re
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_TOKEN = os.getenv("GROQ_TOKEN")
OWNER_ID = 1307042499898118246  # Change to your ID

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
ai_client = Groq(api_key=GROQ_TOKEN)

# ================= RULES =================
ALLOWED_QUESTIONS = [
    "who", "what", "when", "where", "which",
    "why", "how", "should", "advice",
    "suggestion", "suggestions", "explanation",
    "explanations", "instruction", "instructions",
    "opinion", "opinions"
]

FORBIDDEN_KEYWORDS = [
    "ignore previous instructions", "override rules", "system message",
    "developer message", "act as", "jailbreak", "bypass",
    "do not follow", "new rules", "pretend you are",
    "sexual", "sex", "nsfw"
]

def is_allowed_question(content: str) -> bool:
    content_lower = content.lower()
    if any(k in content_lower for k in FORBIDDEN_KEYWORDS):
        return False
    for word in ALLOWED_QUESTIONS:
        if content_lower.startswith(word) or content_lower.startswith(word[:3]):
            return True
    return False

async def get_ai_response(question: str) -> str:
    if not is_allowed_question(question):
        return None
    try:
        response = ai_client.ask(question)
        response_text = str(response)
        # Filter AI answer for forbidden content
        if any(k in response_text.lower() for k in FORBIDDEN_KEYWORDS):
            return None
        return response_text
    except Exception:
        return None

def owner_only(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID

# ================= EVENTS =================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} | ID: {bot.user.id}")

# ================= AI QUESTION COMMAND =================
@tree.command(name="ask", description="Ask the bot a question")
async def ask(interaction: discord.Interaction, question: str):
    answer = await get_ai_response(question)
    if answer:
        await interaction.response.send_message(answer, ephemeral=True)

# ================= CHANNEL COMMANDS =================
@tree.command(name="lock_channel", description="Lock this channel")
async def lock_channel(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Channel locked.", ephemeral=True)

@tree.command(name="unlock_channel", description="Unlock this channel")
async def unlock_channel(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Channel unlocked.", ephemeral=True)

@tree.command(name="panic_lock", description="Lock all channels")
async def panic_lock(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    for c in interaction.guild.text_channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("All channels locked.", ephemeral=True)

@tree.command(name="panic_unlock", description="Unlock all channels")
async def panic_unlock(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    for c in interaction.guild.text_channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("All channels unlocked.", ephemeral=True)

@tree.command(name="rename_channel", description="Rename this channel")
async def rename_channel(interaction: discord.Interaction, name: str):
    if not owner_only(interaction):
        return
    await interaction.channel.edit(name=name)
    await interaction.response.send_message(f"Channel renamed to {name}.", ephemeral=True)

@tree.command(name="un_rename_channel", description="Cannot undo rename")
async def un_rename_channel(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.response.send_message("Cannot undo rename.", ephemeral=True)

@tree.command(name="slowmode", description="Set slowmode for this channel")
async def slowmode(interaction: discord.Interaction, seconds: int):
    if not owner_only(interaction):
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds} seconds.", ephemeral=True)

@tree.command(name="un_slowmode", description="Disable slowmode")
async def un_slowmode(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.channel.edit(slowmode_delay=0)
    await interaction.response.send_message("Slowmode disabled.", ephemeral=True)

# ================= MEMBER COMMANDS =================
@tree.command(name="kick_member", description="Kick a member")
async def kick_member(interaction: discord.Interaction, member: discord.Member):
    if not owner_only(interaction):
        return
    await member.kick()
    await interaction.response.send_message(f"{member} kicked.", ephemeral=True)

@tree.command(name="un_kick_member", description="Cannot undo kick")
async def un_kick_member(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.response.send_message("Cannot undo kick.", ephemeral=True)

@tree.command(name="ban_member", description="Ban a member")
async def ban_member(interaction: discord.Interaction, member: discord.Member):
    if not owner_only(interaction):
        return
    await member.ban()
    await interaction.response.send_message(f"{member} banned.", ephemeral=True)

@tree.command(name="un_ban_member", description="Cannot undo ban")
async def un_ban_member(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.response.send_message("Cannot undo ban.", ephemeral=True)

# ================= EXTRA COMMANDS (examples) =================
@tree.command(name="mute_member", description="Mute a member")
async def mute_member(interaction: discord.Interaction, member: discord.Member):
    if not owner_only(interaction):
        return
    await member.edit(mute=True)
    await interaction.response.send_message(f"{member} muted.", ephemeral=True)

@tree.command(name="un_mute_member", description="Unmute a member")
async def un_mute_member(interaction: discord.Interaction, member: discord.Member):
    if not owner_only(interaction):
        return
    await member.edit(mute=False)
    await interaction.response.send_message(f"{member} unmuted.", ephemeral=True)

@tree.command(name="delete_message", description="Delete a message")
async def delete_message(interaction: discord.Interaction, message_id: str):
    if not owner_only(interaction):
        return
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        await msg.delete()
        await interaction.response.send_message("Message deleted.", ephemeral=True)
    except Exception:
        await interaction.response.send_message("Could not delete message.", ephemeral=True)

@tree.command(name="un_delete_message", description="Cannot undo deletion")
async def un_delete_message(interaction: discord.Interaction):
    if not owner_only(interaction):
        return
    await interaction.response.send_message("Cannot undo deletion.", ephemeral=True)

# ================= AI PROTECTION =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not is_allowed_question(message.content):
        return  # Silent reject
    answer = await get_ai_response(message.content)
    if answer:
        await message.channel.send(answer)
    await bot.process_commands(message)

# ================= RUN BOT =================
bot.run(DISCORD_TOKEN)
# at the end of bot.py
import os
import asyncio
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running")

app = web.Application()
app.router.add_get("/", handle)

# Use Render's assigned PORT or default 10000
web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
