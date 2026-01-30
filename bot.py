# =========================
# FULL DISCORD BOT WITH MODERATION & FUN COMMANDS
# PREFIX: !
# =========================

import discord
from discord.ext import commands
import asyncio
import aiohttp
import os
import random

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
OWNER_ID = 1307042499898118246
allowed_users = set()
blacklisted_users = set()
maintenance_mode = False
mod_notes_dict = {}

# =========================
# OWNER CHECK
# =========================
def is_owner(ctx):
    return ctx.author.id == OWNER_ID

# =========================
# GROQ / AI SETUP (Optional)
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

    pattern_words = ["who", "what", "when", "where", "why", "how", "advice", "suggestion"]
    if any(word in message.content.lower() for word in pattern_words):
        question = f"Answer this about this Discord server only: {message.content}"
        reply = await ask_groq(question)
        if reply:
            await message.channel.send(reply)

    await bot.process_commands(message)

# =========================
# WHITELIST / BLACKLIST COMMANDS
# =========================
@bot.command()
async def whitelist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    allowed_users.add(member.id)
    await ctx.send(f"✅ {member.display_name} whitelisted for moderation.")

@bot.command()
async def blacklist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    if member.id in allowed_users:
        allowed_users.remove(member.id)
    blacklisted_users.add(member.id)
    await ctx.send(f"❌ {member.display_name} blacklisted from moderation.")

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
    await ctx.send(f"🔒 {channel.mention} locked!")

@bot.command()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 {channel.mention} unlocked!")

@bot.command()
async def add_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.add_roles(role)
    await ctx.send(f"✅ Added {role.name} to {member.display_name}")

@bot.command()
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed {role.name} from {member.display_name}")

@bot.command()
async def troll(ctx, member: discord.Member):
    if not is_owner(ctx):
        return

    old_roles = [role for role in member.roles if role.name != "@everyone"]
    invite = await ctx.channel.create_invite(max_age=600, max_uses=1, unique=True)

    try:
        embed = discord.Embed(
            title=f"You have been banned from {ctx.guild.name}!",
            description=(
                f"Reason: messing around 😜\n\n"
                f"LOL JK! Use this invite to return: {invite.url}\n"
                "Your roles will be restored if you rejoin."
            ),
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
    except:
        await member.send(f"You have been banned from {ctx.guild.name}! LOL JK! Use this invite: {invite.url}")

    await member.kick(reason="Messing around")

    def check(m):
        return m.id == member.id and m.guild == ctx.guild

    try:
        rejoined = await bot.wait_for("member_join", timeout=600, check=check)
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} rejoined and roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} did not rejoin in 10 minutes.")

# =========================
# FUN COMMANDS
# =========================
@bot.command()
async def coin(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 {result}")

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

# (Add all other fun commands here in proper multi-line format)
# Examples:
@bot.command()
async def joke(ctx):
    jokes = [
        "Why did the scarecrow win an award? Because he was outstanding!",
        "Why don't scientists trust atoms? They make up everything!",
        "I told my computer I needed a break, and it said 'No problem!'"
    ]
    selected = random.choice(jokes)
    await ctx.send(f"😂 {selected}")

@bot.command()
async def compliment(ctx):
    compliments = ["You're awesome!", "You're amazing!", "You're a star!", "Keep shining!", "You're wonderful!"]
    await ctx.send(f"💖 {random.choice(compliments)}")

# =========================
# BOT RUNNER
# =========================
async def set_default_status():
    await bot.wait_until_ready()
    await bot.change_presence(
        activity=discord.Game(name="Solving mysteries!"),
        status=discord.Status.online
    )

if __name__ == "__main__":
    import asyncio
    TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_BOT_TOKEN"
    bot.loop.create_task(set_default_status())
    bot.run(TOKEN)
