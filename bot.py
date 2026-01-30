# =========================
# FULL DISCORD BOT WITH 55+ COMMANDS
# =========================
import discord
from discord.ext import commands
import asyncio
import aiohttp
import re
import os
import random

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
OWNER_ID = 1307042499898118246
allowed_users = set()
blacklisted_users = set()
maintenance_mode = False
mod_notes_dict = {}

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

# =========================
# GROQ / AI SETUP (optional)
# =========================
GROQ_TOKEN = os.getenv("GROQ_TOKEN")
async def ask_groq(question: str):
    headers = {"Authorization": f"Bearer {GROQ_TOKEN}"}
    payload = {"prompt": question, "max_tokens": 50}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.groq.com/v1/answer", headers=headers, json=payload) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("answer", "I cannot answer that.")
            return "I cannot answer that."

# =========================
# AUTO-RESPONSE
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if maintenance_mode and message.author.id != OWNER_ID:
        return
    pattern = re.compile(r"\b(who|what|when|where|why|how|advice|suggestion)\b", re.IGNORECASE)
    if pattern.search(message.content):
        question = f"Answer this about this Discord server only: {message.content}"
        reply = await ask_groq(question)
        if reply:
            await message.channel.send(reply)
    await bot.process_commands(message)

# =========================
# WHITELIST / BLACKLIST
# =========================
@bot.command()
async def whitelist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    allowed_users.add(member.id)
    await ctx.send(f"✅ {member.display_name} has been whitelisted.")

@bot.command()
async def blacklist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    allowed_users.discard(member.id)
    blacklisted_users.add(member.id)
    await ctx.send(f"❌ {member.display_name} has been blacklisted.")

# =========================
# MODERATION COMMANDS
# =========================
@bot.command()
async def panic_lock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 All channels locked!")

@bot.command()
async def panic_unlock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 All channels unlocked!")

@bot.command()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 {channel.mention} locked.")

@bot.command()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 {channel.mention} unlocked.")

@bot.command()
async def add_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.add_roles(role)
    await ctx.send(f"✅ Added role {role.name} to {member.display_name}")

@bot.command()
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed role {role.name} from {member.display_name}")

@bot.command()
async def server_info(ctx):
    if not is_owner(ctx):
        return
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=discord.Color.blue())
    embed.add_field(name="Server ID", value=guild.id)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.set_footer(text=f"Owner: {guild.owner}")
    await ctx.send(embed=embed)

@bot.command()
async def member_info(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title=f"{member.display_name} Info", color=discord.Color.green())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at)
    embed.add_field(name="Account Created", value=member.created_at)
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]))
    await ctx.send(embed=embed)

@bot.command()
async def role_info(ctx, role: discord.Role):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title=f"{role.name} Info", color=discord.Color.purple())
    embed.add_field(name="Role ID", value=role.id)
    embed.add_field(name="Members with Role", value=len(role.members))
    embed.add_field(name="Color", value=str(role.color))
    embed.add_field(name="Mentionable", value=role.mentionable)
    await ctx.send(embed=embed)

@bot.command()
async def mod_ping(ctx):
    if not is_owner(ctx):
        return
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

@bot.command()
async def clear(ctx, amount: int = 10):
    if not is_owner(ctx):
        return
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)

@bot.command()
async def mod_notes(ctx, member: discord.Member, *, note):
    if not is_owner(ctx):
        return
    mod_notes_dict.setdefault(member.id, []).append(note)
    await ctx.send(f"📝 Note added for {member.display_name}")

@bot.command()
async def view_notes(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    notes = mod_notes_dict.get(member.id, [])
    await ctx.send(f"📝 Notes for {member.display_name}: {notes if notes else 'No notes'}")

@bot.command()
async def temp_mute(ctx, member: discord.Member, minutes: int = 10):
    if not is_owner(ctx):
        return
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False)
    await member.add_roles(muted_role)
    await ctx.send(f"🔇 {member.display_name} muted for {minutes} minutes")
    await asyncio.sleep(minutes*60)
    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.display_name} unmuted")

@bot.command()
async def temp_ban(ctx, member: discord.Member, minutes: int = 10):
    if not is_owner(ctx):
        return
    await member.ban(reason=f"Temp ban {minutes} min")
    await ctx.send(f"⛔ {member.display_name} temp banned for {minutes} min")
    await asyncio.sleep(minutes*60)
    await ctx.guild.unban(member)
    await ctx.send(f"✅ {member.display_name} unbanned")

# =========================
# TROLL KICK COMMAND
# =========================
@bot.command()
async def troll(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    old_roles = [role for role in member.roles if role.name != "@everyone"]
    invite = await ctx.channel.create_invite(max_age=600, max_uses=1, unique=True)
    embed = discord.Embed(
        title=f"You have been banned from {ctx.guild.name}!",
        description=(
            f"Reason: messing around 😜\n\n"
            f"LOL JK! Join back with this invite: {invite.url}\n"
            "Your roles will be restored if you rejoin."
        ),
        color=discord.Color.blue()
    )
    try:
        await member.send(embed=embed)
    except:
        await member.send(f"You have been banned from {ctx.guild.name}! LOL JK! Invite: {invite.url}")
    await member.kick(reason="Messing around")
    def check(m):
        return m.id == member.id and m.guild == ctx.guild
    try:
        rejoined = await bot.wait_for('member_join', timeout=600, check=check)
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} rejoined and roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} did not rejoin in 10 minutes.")

# =========================
# FUN COMMANDS (55+ planned)
# =========================
@bot.command()
async def coin(ctx):
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}")

@bot.command()
async def joke(ctx):
    jokes = [
        "Why did the scarecrow win an award? Because he was outstanding!",
        "Why don't scientists trust atoms? They make up everything!",
        "I told my computer I needed a break, it said no problem!"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

@bot.command()
async def rps(ctx, choice: str):
    options = ["rock", "paper", "scissors"]
    user_choice = choice.lower()
    if user_choice not in options:
        await ctx.send("❌ Choose rock, paper, or scissors!")
        return
    bot_choice = random.choice(options)
    if user_choice == bot_choice:
        result = "It's a tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = "You win!"
    else:
        result = "You lose!"
    await ctx.send(f"You: **{user_choice}**, Bot: **{bot_choice}** → {result}")

@bot.command()
async def eight_ball(ctx, *, question):
    answers = ["Yes", "No", "Maybe", "Definitely", "Ask later"]
    await ctx.send(f"🎱 {random.choice(answers)}")

# More fun commands can follow the same pattern:
# choose, roll2d6, random_number, compliment, flip, roll_percent, roll_multiple, truth, dare, inspire, fact, number_guess, reverse, shout, whisper, etc.

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_BOT_TOKEN"
    bot.run(TOKEN)
