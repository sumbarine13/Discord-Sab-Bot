import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
import uvicorn

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_DISCORD_BOT_TOKEN"
OWNER_ID = 1307042499898118246

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Required for message responses

bot = commands.Bot(command_prefix="!", intents=intents)

def owner_only(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID

# ================= DISCORD ASSISTANT RULES =================
ALLOWED_PREFIXES = (
    "who", "what", "when", "where", "which",
    "should", "why", "how", "advice", "suggestions",
    "explanations", "instructions", "opinions"
)

async def rule_check_response(interaction: discord.Interaction, content: str):
    if content.strip().lower().startswith(ALLOWED_PREFIXES):
        await interaction.response.send_message(content)
    else:
        await interaction.response.send_message(
            "Cannot answer: question not allowed by rules.", ephemeral=True
        )

# ================= EVENTS =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Only respond to messages in guilds
    content = message.content
    if any(content.lower().startswith(p) for p in ALLOWED_PREFIXES):
        await message.channel.send(f"Received allowed question: {content}")
    else:
        await message.channel.send("I can only answer allowed question types.")

# ================== MAIN SLASH COMMANDS (20) ==================
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! `{round(bot.latency*1000)}ms`")

@bot.tree.command(name="set_status", description="Set bot status")
async def set_status(interaction: discord.Interaction, text: str):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await bot.change_presence(activity=discord.Game(name=text))
    await interaction.response.send_message("Status updated.", ephemeral=True)

@bot.tree.command(name="shutdown", description="Shutdown bot")
async def shutdown(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await interaction.response.send_message("Shutting down.")
    await bot.close()

@bot.tree.command(name="server_info", description="Server info")
async def server_info(interaction: discord.Interaction):
    g = interaction.guild
    await interaction.response.send_message(f"Name: {g.name}\nMembers: {g.member_count}")

@bot.tree.command(name="user_info", description="User info")
async def user_info(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message(f"User: {user}\nID: {user.id}")

@bot.tree.command(name="announce", description="Send announcement")
async def announce(interaction: discord.Interaction, message: str):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await interaction.channel.send(message)
    await interaction.response.send_message("Sent.", ephemeral=True)

@bot.tree.command(name="lock_channel", description="Lock channel")
async def lock_channel(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Channel locked.")

@bot.tree.command(name="unlock_channel", description="Unlock channel")
async def unlock_channel(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Channel unlocked.")

@bot.tree.command(name="clear", description="Clear messages")
async def clear(interaction: discord.Interaction, amount: int):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message("Cleared.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick user")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str="No reason"):
    if not owner_only(interaction):
        return await interaction.response.send_message("Not allowed.", ephemeral=True)
    await user.kick(reason=reason)
    await interaction.response.send_message("User kicked.")

# Add remaining 10 main commands (ban, unban, slowmode, etc.) using same format
# ================= UNIQUE COMMANDS (15) ==================
# Example: panic_lock, ghost_mode, etc., same format with owner_only check

# ================= FASTAPI DASHBOARD =================
app = FastAPI()
BOT_STATUS = {"online": True}

@app.get("/")
async def root():
    return {"status": "alive", "bot_online": BOT_STATUS["online"]}

@app.get("/toggle")
async def toggle():
    BOT_STATUS["online"] = not BOT_STATUS["online"]
    return {"bot_online": BOT_STATUS["online"]}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080)

threading.Thread(target=run_web, daemon=True).start()

# ================= RUN BOT =================
bot.run(TOKEN)
