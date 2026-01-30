# =========================
# DISCORD BOT WITH 55 COMMANDS
# =========================

import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import os
import random
import re

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
OWNER_ID = 1307042499898118246

allowed_users = set()  # Whitelist for moderation
blacklisted_users = set()
mod_notes_dict = {}
maintenance_mode = False

# =========================
# OWNER CHECK
# =========================
def is_owner(ctx):
    return ctx.author.id == OWNER_ID

# =========================
# GROQ / AI SETUP
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
    if not is_owner(ctx): return
    allowed_users.add(member.id)
    await ctx.send(f"✅ {member.display_name} whitelisted.")

@bot.command()
async def blacklist(ctx, member: discord.Member):
    if not is_owner(ctx): return
    allowed_users.discard(member.id)
    blacklisted_users.add(member.id)
    await ctx.send(f"❌ {member.display_name} blacklisted.")

# =========================
# MODERATION COMMANDS (Owner-only)
# =========================
@bot.command()
async def panic_lock(ctx):
    if not is_owner(ctx): return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 All channels locked!")

@bot.command()
async def panic_unlock(ctx):
    if not is_owner(ctx): return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 All channels unlocked!")

@bot.command()
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx): return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 {channel.mention} locked!")

@bot.command()
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx): return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 {channel.mention} unlocked!")

@bot.command()
async def add_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx): return
    await member.add_roles(role)
    await ctx.send(f"✅ Added role {role.name} to {member.display_name}")

@bot.command()
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx): return
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed role {role.name} from {member.display_name}")

@bot.command()
async def temp_mute(ctx, member: discord.Member, minutes: int = 10):
    if not is_owner(ctx): return
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for c in ctx.guild.channels:
            await c.set_permissions(muted_role, send_messages=False)
    await member.add_roles(muted_role)
    await ctx.send(f"🔇 {member.display_name} muted for {minutes} minutes")
    await asyncio.sleep(minutes*60)
    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.display_name} unmuted")

@bot.command()
async def temp_ban(ctx, member: discord.Member, minutes: int = 10):
    if not is_owner(ctx): return
    await member.ban(reason=f"Temp ban {minutes} min")
    await ctx.send(f"⛔ {member.display_name} banned for {minutes} minutes")
    await asyncio.sleep(minutes*60)
    await ctx.guild.unban(member)
    await ctx.send(f"✅ {member.display_name} unbanned")

@bot.command()
async def create_role(ctx, *, name):
    if not is_owner(ctx): return
    await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Role {name} created")

@bot.command()
async def delete_role(ctx, role: discord.Role):
    if not is_owner(ctx): return
    await role.delete()
    await ctx.send(f"❌ Role {role.name} deleted")

@bot.command()
async def create_channel(ctx, *, name):
    if not is_owner(ctx): return
    await ctx.guild.create_text_channel(name)
    await ctx.send(f"✅ Channel {name} created")

@bot.command()
async def delete_channel(ctx, channel: discord.TextChannel):
    if not is_owner(ctx): return
    await channel.delete()
    await ctx.send(f"❌ Channel {channel.name} deleted")

@bot.command()
async def server_lock(ctx):
    if not is_owner(ctx): return
    for c in ctx.guild.channels:
        await c.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Server locked!")

@bot.command()
async def server_unlock(ctx):
    if not is_owner(ctx): return
    for c in ctx.guild.channels:
        await c.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Server unlocked!")

@bot.command()
async def mod_notes(ctx, member: discord.Member, *, note):
    if not is_owner(ctx): return
    if member.id not in mod_notes_dict:
        mod_notes_dict[member.id] = []
    mod_notes_dict[member.id].append(note)
    await ctx.send(f"📝 Note added for {member.display_name}")

@bot.command()
async def view_notes(ctx, member: discord.Member):
    if not is_owner(ctx): return
    notes = mod_notes_dict.get(member.id, [])
    await ctx.send(f"📝 Notes for {member.display_name}: {notes if notes else 'No notes'}")

@bot.command()
async def maintenance(ctx):
    global maintenance_mode
    if not is_owner(ctx): return
    maintenance_mode = not maintenance_mode
    state = "ON" if maintenance_mode else "OFF"
    await ctx.send(f"⚙️ Maintenance mode is now {state}")

# =========================
# INFO COMMANDS
# =========================
@bot.command()
async def server_info(ctx):
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
    embed = discord.Embed(title=f"{member.display_name} Info", color=discord.Color.green())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at)
    embed.add_field(name="Account Created", value=member.created_at)
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]))
    await ctx.send(embed=embed)

@bot.command()
async def role_info(ctx, role: discord.Role):
    embed = discord.Embed(title=f"{role.name} Info", color=discord.Color.purple())
    embed.add_field(name="ID", value=role.id)
    embed.add_field(name="Members with Role", value=len(role.members))
    embed.add_field(name="Color", value=str(role.color))
    embed.add_field(name="Mentionable", value=role.mentionable)
    await ctx.send(embed=embed)

@bot.command()
async def my_info(ctx):
    embed = discord.Embed(title=f"{ctx.author.display_name} Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=ctx.author.id)
    embed.add_field(name="Joined Server", value=ctx.author.joined_at)
    embed.add_field(name="Account Created", value=ctx.author.created_at)
    await ctx.send(embed=embed)

@bot.command()
async def my_roles(ctx):
    roles = [r.name for r in ctx.author.roles if r.name != "@everyone"]
    await ctx.send(f"Your roles: {', '.join(roles) if roles else 'None'}")

@bot.command()
async def server_created(ctx):
    await ctx.send(f"{ctx.guild.name} was created on {ctx.guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

# =========================
# FUN / UTILITY COMMANDS (Total 55)
# =========================
@bot.command()
async def coin(ctx): await ctx.send(f"🪙 {random.choice(['Heads','Tails'])}")
@bot.command()
async def rps(ctx, choice: str):
    options = ["rock","paper","scissors"]; choice=choice.lower()
    if choice not in options: await ctx.send("❌ Choose rock, paper, or scissors!"); return
    bot_choice=random.choice(options)
    if choice==bot_choice: result="It's a tie!"
    elif (choice=="rock" and bot_choice=="scissors") or (choice=="paper" and bot_choice=="rock") or (choice=="scissors" and bot_choice=="paper"): result="You win!"
    else: result="You lose!"
    await ctx.send(f"You: **{choice}**, Bot: **{bot_choice}** → {result}")

@bot.command() async def joke(ctx): await ctx.send(f"😂 {random.choice(['Why did the scarecrow win an award? Because he was outstanding!','Why don\'t scientists trust atoms? They make up everything!','I told my computer I needed a break, it said no problem!'])}")
@bot.command() async def compliment(ctx): await ctx.send(f"💖 {random.choice(['You\'re awesome!','You\'re amazing!','You\'re a star!','Keep shining!','You\'re wonderful!'])}")
@bot.command() async def roll_dice(ctx, sides:int=6): await ctx.send(f"🎲 You rolled: {random.randint(1,sides)}")
@bot.command() async def roll_multiple(ctx,count:int=2,sides:int=6): await ctx.send(f"🎲 Rolls: {[random.randint(1,sides) for _ in range(count)]}")
@bot.command() async def flip(ctx,opt1:str,opt2:str): await ctx.send(f"🎲 I choose: {random.choice([opt1,opt2])}")
@bot.command() async def roll_percent(ctx): await ctx.send(f"📊 You got {random.randint(1,100)}%!")
@bot.command() async def random_color(ctx): await ctx.send(f"🎨 {random.choice(['Red','Blue','Green','Yellow','Purple','Orange','Pink'])}")
@bot.command() async def magic_number(ctx): await ctx.send(f"✨ {random.randint(1,50)}")
@bot.command() async def echo(ctx,*,text): await ctx.send(f"🗣️ {text}")
@bot.command() async def say_hi(ctx): await ctx.send(f"👋 Hello {ctx.author.display_name}!")
@bot.command() async def truth(ctx): await ctx.send(f"🤔 {random.choice(['Biggest fear?','Ever lied to friend?','Most embarrassing moment?','Secret hobby?'])}")
@bot.command() async def dare(ctx): await ctx.send(f"😎 {random.choice(['Do 10 pushups','Send funny selfie','Say something nice','Imitate an animal!'])}")
@bot.command() async def inspire(ctx): await ctx.send(f"💡 {random.choice(['Believe you can','Mind is limit','Dream big','Every day second chance'])}")
@bot.command() async def fact(ctx): await ctx.send(f"🧠 {random.choice(['Bananas are berries','Honey never spoils','Octopus has 3 hearts','Sharks existed before trees'])}")
@bot.command() async def number_guess(ctx,guess:int): await ctx.send(f"{'🎉 Correct!' if guess==random.randint(1,10) else '❌ Wrong!'}")
@bot.command() async def reverse(ctx,*,text): await ctx.send(f"🔄 {text[::-1]}")
@bot.command() async def shout(ctx,*,text): await ctx.send(f"📢 {text.upper()}")
@bot.command() async def whisper(ctx,*,text): await ctx.send(f"🤫 {text.lower()}")
@bot.command() async def roll_range(ctx,start:int,end:int): await ctx.send(f"🎲 {random.randint(start,end)}")
@bot.command() async def flip_coin_multiple(ctx,times:int=3): await ctx.send(f"🪙 {', '.join([random.choice(['Heads','Tails']) for _ in range(times)])}")
@bot.command() async def roll_1d20(ctx): await ctx.send(f"🎲 {random.randint(1,20)}")
@bot.command() async def roll_2d6(ctx): await ctx.send(f"🎲 {[random.randint(1,6) for _ in range(2)]}")
@bot.command() async def roll_3d6(ctx): await ctx.send(f"🎲 {[random.randint(1,6) for _ in range(3)]}")
@bot.command() async def random_pet(ctx): await ctx.send(f"🐾 {random.choice(['Dog','Cat','Rabbit','Hamster','Parrot','Turtle'])}")
@bot.command() async def choose(ctx,*,options): opts=[o.strip() for o in options.split(',') if o.strip()]; await ctx.send(f"✅ {random.choice(opts) if opts else 'No options'}")
@bot.command() async def mod_ping(ctx): await ctx.send(f"Pong! {round(bot.latency*1000)}ms")
@bot.command() async def top_boosters(ctx): boosters=sorted(ctx.guild.premium_subscribers,key=lambda m:m.joined_at)[:5]; await ctx.send(f"Top boosters: {', '.join([b.display_name for b in boosters]) if boosters else 'None'}")
@bot.command() async def list_roles(ctx): await ctx.send(f"{', '.join([r.name for r in ctx.guild.roles])}")
@bot.command() async def channel_type(ctx,channel:discord.TextChannel=None): channel=channel or ctx.channel; await ctx.send(f"{channel.name} type: {type(channel).__name__}")
@bot.command() async def boost_level(ctx): await ctx.send(f"Server boost level: {ctx.guild.premium_tier}, boosts: {ctx.guild.premium_subscription_count}")
@bot.command() async def audit_log(ctx,limit:int=10): entries=await ctx.guild.audit_logs(limit=limit).flatten(); await ctx.send(f"🗂️ Last {len(entries)} entries:\n" + "\n".join([f"{e.user} {e.action} -> {e.target}" for e in entries]))
@bot.command() async def bot_info(ctx): await ctx.send(f"Bot: {bot.user.name}, ID: {bot.user.id}, Servers: {len(bot.guilds)}")
@bot.command(name="troll_kick")
async def troll_kick(ctx, member: discord.Member):
    if not is_owner(ctx):
        return

    # Save current roles (except @everyone)
    old_roles = [role for role in member.roles if role.name != "@everyone"]

    # Create a one-time invite to the channel
    invite = await ctx.channel.create_invite(max_age=600, max_uses=1, unique=True)

    # Blue embed message
    embed = discord.Embed(
        title=f"You have been banned from {ctx.guild.name}!",
        description=(
            "Reason: Messing around 😜\n\n"
            f"LOL JK! Use this invite to come back: {invite.url}\n"
            "Your roles will be restored if you rejoin."
        ),
        color=discord.Color.blue()
    )

    # Try sending DM to member
    try:
        await member.send(embed=embed)
    except:
        # Fallback if DMs are closed
        await member.send(f"You have been banned from {ctx.guild.name}! LOL JK! Use this invite to come back: {invite.url}")

    # Kick member
    await member.kick(reason="Messing around")

    # Wait for them to rejoin
    def check(m):
        return m.id == member.id and m.guild == ctx.guild

    try:
        rejoined = await bot.wait_for('member_join', timeout=600, check=check)
        # Restore roles
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} has rejoined and roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} did not rejoin within 10 minutes.")
# =========================
# BOT READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="Monitoring the server!"), status=discord.Status.online)

# =========================
# RUN BOT
# =========================
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_BOT_TOKEN"
bot.run(TOKEN)
