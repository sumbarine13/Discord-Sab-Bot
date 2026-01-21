import os
import time
import threading
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
import uvicorn
from groq import Groq

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
OWNER_ID = 1307042499898118246
START_TIME = time.time()

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing")

if not GROQ_KEY:
    raise RuntimeError("GROQ_API_KEY is missing")

groq_client = Groq(api_key=GROQ_KEY)

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def owner_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================= MAIN COMMANDS (20) =================

@bot.tree.command(name="ping", description="Check latency")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"Pong! `{round(bot.latency * 1000)}ms`")

@bot.tree.command(name="set_status")
async def set_status(i: discord.Interaction, text: str):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await bot.change_presence(activity=discord.Game(name=text))
    await i.response.send_message("Status updated.", ephemeral=True)

@bot.tree.command(name="shutdown")
async def shutdown(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.response.send_message("Shutting down.")
    await bot.close()

@bot.tree.command(name="server_info")
async def server_info(i: discord.Interaction):
    g = i.guild
    await i.response.send_message(f"Name: {g.name}\nMembers: {g.member_count}")

@bot.tree.command(name="user_info")
async def user_info(i: discord.Interaction, user: discord.Member):
    await i.response.send_message(f"User: {user}\nID: {user.id}")

@bot.tree.command(name="announce")
async def announce(i: discord.Interaction, message: str):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.send(message)
    await i.response.send_message("Sent.", ephemeral=True)

@bot.tree.command(name="lock_channel")
async def lock_channel(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("Channel locked.")

@bot.tree.command(name="unlock_channel")
async def unlock_channel(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("Channel unlocked.")

@bot.tree.command(name="clear")
async def clear(i: discord.Interaction, amount: int):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.response.send_message("Cleared.", ephemeral=True)

@bot.tree.command(name="kick")
async def kick(i: discord.Interaction, user: discord.Member, reason: str = "No reason"):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await user.kick(reason=reason)
    await i.response.send_message("User kicked.")

@bot.tree.command(name="ban")
async def ban(i: discord.Interaction, user: discord.Member, reason: str = "No reason"):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await user.ban(reason=reason)
    await i.response.send_message("User banned.")

@bot.tree.command(name="unban")
async def unban(i: discord.Interaction, user_id: int):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    user = await bot.fetch_user(user_id)
    await i.guild.unban(user)
    await i.response.send_message("User unbanned.")

@bot.tree.command(name="slowmode")
async def slowmode(i: discord.Interaction, seconds: int):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message("Slowmode updated.")

@bot.tree.command(name="rename_channel")
async def rename_channel(i: discord.Interaction, name: str):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.channel.edit(name=name)
    await i.response.send_message("Channel renamed.")

@bot.tree.command(name="create_role")
async def create_role(i: discord.Interaction, name: str):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.guild.create_role(name=name)
    await i.response.send_message("Role created.")

@bot.tree.command(name="delete_role")
async def delete_role(i: discord.Interaction, role: discord.Role):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await role.delete()
    await i.response.send_message("Role deleted.")

@bot.tree.command(name="bot_info")
async def bot_info(i: discord.Interaction):
    await i.response.send_message(f"Servers: {len(bot.guilds)}")

@bot.tree.command(name="uptime")
async def uptime(i: discord.Interaction):
    seconds = int(time.time() - START_TIME)
    await i.response.send_message(f"Uptime: {seconds}s")

# ================= UNIQUE COMMANDS (15) =================

@bot.tree.command(name="panic_lock")
async def panic_lock(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    for c in i.guild.text_channels:
        await c.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("Server locked.")

@bot.tree.command(name="panic_unlock")
async def panic_unlock(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    for c in i.guild.text_channels:
        await c.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("Server unlocked.")

@bot.tree.command(name="ghost_mode")
async def ghost_mode(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.guild.me.edit(nick="‎")
    await i.response.send_message("Ghost mode enabled.")

@bot.tree.command(name="reset_nicks")
async def reset_nicks(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    for m in i.guild.members:
        try:
            await m.edit(nick=None)
        except:
            pass
    await i.response.send_message("Nicknames reset.")

@bot.tree.command(name="list_bots")
async def list_bots(i: discord.Interaction):
    bots = [m.name for m in i.guild.members if m.bot]
    await i.response.send_message(", ".join(bots) or "No bots.")

@bot.tree.command(name="owner_check")
async def owner_check(i: discord.Interaction):
    await i.response.send_message(str(owner_only(i)))

@bot.tree.command(name="bot_restart")
async def bot_restart(i: discord.Interaction):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)
    await i.response.send_message("Restarting...")
    os._exit(0)

@bot.tree.command(name="ai_ask")
async def ai_ask(i: discord.Interaction, prompt: str):
    if not owner_only(i):
        return await i.response.send_message("Not allowed.", ephemeral=True)

    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )

    await i.response.send_message(completion.choices[0].message.content)

# ================= KEEP-ALIVE WEB =================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "alive"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080)

threading.Thread(target=run_web, daemon=True).start()

bot.run(TOKEN)
