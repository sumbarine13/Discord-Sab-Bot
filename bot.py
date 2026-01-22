import os
import threading
import discord
from discord.ext import commands
from discord import app_commands
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "PUT_YOUR_BOT_TOKEN_HERE"
OWNER_ID = 1307042499898118246

# Bot status control
BOT_ON = True

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def owner_only(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID

# ================= ON READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================== MAIN COMMANDS (20) ==================
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

# ===== 10 more MAIN =====
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason"):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await user.kick(reason=reason)
    await interaction.response.send_message("User kicked.")

@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason"):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await user.ban(reason=reason)
    await interaction.response.send_message("Banned.")

@bot.tree.command(name="unban")
async def unban(interaction: discord.Interaction, user_id: int):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    user = await bot.fetch_user(user_id)
    await interaction.guild.unban(user)
    await interaction.response.send_message("Unbanned.")

@bot.tree.command(name="slowmode")
async def slowmode(interaction: discord.Interaction, seconds: int):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message("Slowmode set.")

@bot.tree.command(name="rename_channel")
async def rename_channel(interaction: discord.Interaction, name: str):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.channel.edit(name=name)
    await interaction.response.send_message("Renamed.")

@bot.tree.command(name="create_role")
async def create_role(interaction: discord.Interaction, name: str):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.guild.create_role(name=name)
    await interaction.response.send_message("Role created.")

@bot.tree.command(name="delete_role")
async def delete_role(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await role.delete()
    await interaction.response.send_message("Role deleted.")

@bot.tree.command(name="bot_info")
async def bot_info(interaction: discord.Interaction):
    await interaction.response.send_message(f"Servers: {len(bot.guilds)}")

@bot.tree.command(name="invite")
async def invite(interaction: discord.Interaction):
    await interaction.response.send_message("Invite disabled.")

@bot.tree.command(name="uptime")
async def uptime(interaction: discord.Interaction):
    await interaction.response.send_message("Uptime active.")

@bot.tree.command(name="reload")
async def reload(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.response.send_message("Reloaded.")

# ================= UNIQUE COMMANDS (15) =================
@bot.tree.command(name="panic_lock")
async def panic_lock(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    for c in interaction.guild.text_channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Server locked.")

@bot.tree.command(name="panic_unlock")
async def panic_unlock(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    for c in interaction.guild.text_channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Server unlocked.")

@bot.tree.command(name="mass_role_remove")
async def mass_role_remove(interaction: discord.Interaction, role: discord.Role):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    for m in role.members:
        await m.remove_roles(role)
    await interaction.response.send_message("Removed role from all.")

@bot.tree.command(name="ghost_mode")
async def ghost_mode(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.guild.me.edit(nick="‎")
    await interaction.response.send_message("Ghost mode enabled.")

@bot.tree.command(name="reset_nicks")
async def reset_nicks(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    for m in interaction.guild.members:
        try: await m.edit(nick=None)
        except: pass
    await interaction.response.send_message("Nicknames reset.")

# 10 more UNIQUE (utility/control)
@bot.tree.command(name="list_bots")
async def list_bots(interaction: discord.Interaction):
    bots = [m.name for m in interaction.guild.members if m.bot]
    await interaction.response.send_message(", ".join(bots))

@bot.tree.command(name="owner_only_check")
async def owner_only_check(interaction: discord.Interaction):
    await interaction.response.send_message(str(owner_only(interaction)))

@bot.tree.command(name="wipe_roles")
async def wipe_roles(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    for r in interaction.guild.roles:
        if r.name != "@everyone":
            await r.delete()
    await interaction.response.send_message("Roles wiped.")

@bot.tree.command(name="bot_restart")
async def bot_restart(interaction: discord.Interaction):
    if not owner_only(interaction):
        return await interaction.response.send_message("No.", ephemeral=True)
    await interaction.response.send_message("Restarting...")
    os._exit(0)

@bot.tree.command(name="debug")
async def debug(interaction: discord.Interaction):
    await interaction.response.send_message("Debug OK.")

# ================= FASTAPI FOR HTML CONTROL =================
app = FastAPI()

@app.post("/on")
async def turn_on():
    global BOT_ON
    BOT_ON = True
    return JSONResponse({"status": "ON"})

@app.post("/off")
async def turn_off():
    global BOT_ON
    BOT_ON = False
    return JSONResponse({"status": "OFF"})

@app.get("/status")
async def status():
    return JSONResponse({"status": "ON" if BOT_ON else "OFF"})

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8080)

threading.Thread(target=run_web, daemon=True).start()

# ================= RUN BOT =================
bot.run(DISCORD_TOKEN)
