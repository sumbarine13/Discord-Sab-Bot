# =========================
# FULL DISCORD BOT WITH MODERATION & FUN COMMANDS
# PREFIX: !
# =========================

import discord
from discord.ext import commands
import asyncio
import aiohttp
import re
import os
import random

# =========================
# BOT SETUP
# =========================

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
OWNER_ID = 1307042499898118246
allowed_users = set()  # Whitelist for moderation
blacklisted_users = set()
maintenance_mode = False
mod_notes_dict = {}

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
    """
    Sends a question to Groq and returns a short safe answer.
    Only responds if the question is related to Discord server info.
    """
    headers = {"Authorization": f"Bearer {GROQ_TOKEN}"}
    payload = {"prompt": question, "max_tokens": 50}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.groq.com/v1/answer", headers=headers, json=payload) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("answer", "I cannot answer that.")
            return "I cannot answer that."

# =========================
# AUTO-RESPONSE SCANNER
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Maintenance mode blocks everything except owner
    if maintenance_mode and message.author.id != OWNER_ID:
        return

    # Check for Groq-trigger words
    pattern = re.compile(r"\b(who|what|when|where|why|how|advice|suggestion)\b", re.IGNORECASE)
    if pattern.search(message.content):
        # Only answer questions related to this Discord server
        question = f"Answer this about this Discord server only: {message.content}"
        reply = await ask_groq(question)
        if reply:
            await message.channel.send(reply)

    await bot.process_commands(message)
    # =========================
# WHITELIST / BLACKLIST COMMANDS
# =========================
@bot.command(name="whitelist")
async def whitelist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    allowed_users.add(member.id)
    await ctx.send(f"✅ {member.display_name} has been whitelisted for moderation commands.")

@bot.command(name="blacklist")
async def blacklist(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    if member.id in allowed_users:
        allowed_users.remove(member.id)
    blacklisted_users.add(member.id)
    await ctx.send(f"❌ {member.display_name} has been blacklisted from moderation commands.")

# =========================
# MODERATION COMMANDS (PREFIX) – BASIC
# =========================

# 1. Panic Lock – lock all channels
@bot.command(name="panic_lock")
async def panic_lock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 All channels locked! Panic mode activated.")

# 2. Panic Unlock – unlock all channels
@bot.command(name="panic_unlock")
async def panic_unlock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 All channels unlocked! Panic mode deactivated.")

# 3. Lock specific channel
@bot.command(name="lock_channel")
async def lock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 {channel.mention} is now locked.")

# 4. Unlock specific channel
@bot.command(name="unlock_channel")
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 {channel.mention} is now unlocked.")

# 5. Add role to member
@bot.command(name="add_role")
async def add_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.add_roles(role)
    await ctx.send(f"✅ Added role {role.name} to {member.display_name}")

# 6. Remove role from member
@bot.command(name="remove_role")
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    if not is_owner(ctx):
        return
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed role {role.name} from {member.display_name}")
    # 7. Server info
@bot.command(name="server_info")
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

# 8. Member info
@bot.command(name="member_info")
async def member_info(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title=f"{member.display_name} Info", color=discord.Color.green())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at)
    embed.add_field(name="Account Created", value=member.created_at)
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]))
    await ctx.send(embed=embed)

# 9. Role info
@bot.command(name="role_info")
async def role_info(ctx, role: discord.Role):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title=f"{role.name} Info", color=discord.Color.purple())
    embed.add_field(name="Role ID", value=role.id)
    embed.add_field(name="Members with Role", value=len(role.members))
    embed.add_field(name="Color", value=str(role.color))
    embed.add_field(name="Mentionable", value=role.mentionable)
    await ctx.send(embed=embed)

# 10. Mod ping
@bot.command(name="mod_ping")
async def mod_ping(ctx):
    if not is_owner(ctx):
        return
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

# 11. Clear messages
@bot.command(name="clear")
async def clear(ctx, amount: int = 10):
    if not is_owner(ctx):
        return
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)

# 12. Add mod note
@bot.command(name="mod_notes")
async def mod_notes(ctx, member: discord.Member, *, note):
    if not is_owner(ctx):
        return
    if member.id not in mod_notes_dict:
        mod_notes_dict[member.id] = []
    mod_notes_dict[member.id].append(note)
    await ctx.send(f"📝 Note added for {member.display_name}")

# 13. View mod notes
@bot.command(name="view_notes")
async def view_notes(ctx, member: discord.Member):
    if not is_owner(ctx):
        return
    notes = mod_notes_dict.get(member.id, [])
    await ctx.send(f"📝 Notes for {member.display_name}: {notes if notes else 'No notes'}")

# 14. Temp mute
@bot.command(name="temp_mute")
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

# 15. Temp ban
@bot.command(name="temp_ban")
async def temp_ban(ctx, member: discord.Member, minutes: int = 10):
    if not is_owner(ctx):
        return
    await member.ban(reason=f"Temp ban {minutes} min")
    await ctx.send(f"⛔ {member.display_name} temp banned for {minutes} min")
    await asyncio.sleep(minutes*60)
    await ctx.guild.unban(member)
    await ctx.send(f"✅ {member.display_name} unbanned")

# 16. Add emoji
@bot.command(name="add_emoji")
async def add_emoji(ctx, name: str, url: str):
    if not is_owner(ctx):
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            image = await r.read()
            emoji = await ctx.guild.create_custom_emoji(name=name, image=image)
    await ctx.send(f"✅ Emoji {emoji.name} added!")

# 17. Remove emoji
@bot.command(name="remove_emoji")
async def remove_emoji(ctx, emoji: discord.Emoji):
    if not is_owner(ctx):
        return
    await emoji.delete()
    await ctx.send(f"❌ Emoji {emoji.name} removed")

# 18. Server lock
@bot.command(name="server_lock")
async def server_lock(ctx):
    if not is_owner(ctx):
        return
    for c in ctx.guild.channels:
        await c.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Server locked!")

# 19. Server unlock
@bot.command(name="server_unlock")
async def server_unlock(ctx):
    if not is_owner(ctx):
        return
    for c in ctx.guild.channels:
        await c.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Server unlocked!")

# 20. Create role
@bot.command(name="create_role")
async def create_role(ctx, *, name):
    if not is_owner(ctx):
        return
    await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Role {name} created")

# 21. Delete role
@bot.command(name="delete_role")
async def delete_role(ctx, role: discord.Role):
    if not is_owner(ctx):
        return
    await role.delete()
    await ctx.send(f"❌ Role {role.name} deleted")
    # 22. Create channel
@bot.command(name="create_channel")
async def create_channel(ctx, *, name):
    if not is_owner(ctx):
        return
    await ctx.guild.create_text_channel(name)
    await ctx.send(f"✅ Channel {name} created")

# 23. Delete channel
@bot.command(name="delete_channel")
async def delete_channel(ctx, channel: discord.TextChannel):
    if not is_owner(ctx):
        return
    await channel.delete()
    await ctx.send(f"❌ Channel {channel.name} deleted")

# 24. Top boosters
@bot.command(name="top_boosters")
async def top_boosters(ctx):
    if not is_owner(ctx):
        return
    boosters = sorted(ctx.guild.premium_subscribers, key=lambda m: m.joined_at)[:5]
    names = [b.display_name for b in boosters]
    await ctx.send(f"Top boosters: {', '.join(names) if names else 'None'}")

# 25. Channel type
@bot.command(name="channel_type")
async def channel_type(ctx, channel: discord.TextChannel = None):
    if not is_owner(ctx):
        return
    channel = channel or ctx.channel
    await ctx.send(f"{channel.name} type: {type(channel).__name__}")

# 26. Server creation date
@bot.command(name="server_created")
async def server_created(ctx):
    if not is_owner(ctx):
        return
    created = ctx.guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
    await ctx.send(f"{ctx.guild.name} created on {created}")

# 27. My roles
@bot.command(name="my_roles")
async def my_roles(ctx):
    roles = [r.name for r in ctx.author.roles if r.name != "@everyone"]
    await ctx.send(f"Your roles: {', '.join(roles) if roles else 'None'}")

# 28. My info
@bot.command(name="my_info")
async def my_info(ctx):
    embed = discord.Embed(title=f"{ctx.author.display_name} Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=ctx.author.id)
    embed.add_field(name="Joined Server", value=ctx.author.joined_at)
    embed.add_field(name="Account Created", value=ctx.author.created_at)
    await ctx.send(embed=embed)

# 29. Bot info
@bot.command(name="bot_info")
async def bot_info(ctx):
    embed = discord.Embed(title="Bot Info", color=discord.Color.blue())
    embed.add_field(name="Bot Name", value=bot.user.name)
    embed.add_field(name="ID", value=bot.user.id)
    embed.add_field(name="Servers", value=len(bot.guilds))
    await ctx.send(embed=embed)

# 30. Emoji list
@bot.command(name="emoji_list")
async def emoji_list(ctx):
    emojis = [str(e) for e in ctx.guild.emojis]
    await ctx.send(f"Emojis: {' '.join(emojis) if emojis else 'None'}")

# 31. Emoji count
@bot.command(name="emoji_count")
async def emoji_count(ctx):
    count = len(ctx.guild.emojis)
    await ctx.send(f"Total emojis: {count}")

# 32. Maintenance mode toggle
@bot.command(name="maintenance")
async def maintenance(ctx):
    global maintenance_mode
    if not is_owner(ctx):
        return
    maintenance_mode = not maintenance_mode
    state = "ON" if maintenance_mode else "OFF"
    await ctx.send(f"⚙️ Maintenance mode is now {state}")

# 33. View audit log (last 10 entries)
@bot.command(name="audit_log")
async def audit_log(ctx, limit: int = 10):
    if not is_owner(ctx):
        return
    entries = await ctx.guild.audit_logs(limit=limit).flatten()
    log_list = [f"{e.user} {e.action} -> {e.target}" for e in entries]
    await ctx.send(f"🗂️ Last {len(log_list)} audit log entries:\n" + "\n".join(log_list))

# 34. Server boost level
@bot.command(name="boost_level")
async def boost_level(ctx):
    if not is_owner(ctx):
        return
    await ctx.send(f"Server boost level: {ctx.guild.premium_tier}, Boosts: {ctx.guild.premium_subscription_count}")

# 35. List all roles
@bot.command(name="list_roles")
async def list_roles(ctx):
    if not is_owner(ctx):
        return
    roles = [r.name for r in ctx.guild.roles]
    await ctx.send(f"All server roles ({len(roles)}): {', '.join(roles)}")

# 36. Troll member (kick & DM joke)
@bot.command(name="troll")
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
                f"LOL JK! Join back with this invite: {invite.url}\n"
                "Your roles will be restored if you rejoin."
            ),
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
    except:
        await member.send(f"You have been banned from {ctx.guild.name}! LOL JK! Use this invite to come back: {invite.url}")

    await member.kick(reason="Messing about")
    def check(m):
        return m.id == member.id and m.guild == ctx.guild

    try:
        rejoined = await bot.wait_for('member_join', timeout=600, check=check)
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} has rejoined and roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} did not rejoin within 10 minutes.")
    import random

# 1. !coin – flip a coin
@bot.command(name="coin")
async def coin(ctx):
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

# 2. !rps – rock paper scissors
@bot.command(name="rps")
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

# 3. !8ball – random answer
@bot.command(name="8ball")
async def eight_ball(ctx, *, question):
    answers = ["Yes", "No", "Maybe", "Definitely", "Ask later"]
    await ctx.send(f"🎱 {random.choice(answers)}")

# 4. !choose – pick one option
@bot.command(name="choose")
async def choose(ctx, *, options):
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if not opts:
        await ctx.send("❌ Provide options separated by commas.")
        return
    await ctx.send(f"✅ I choose: {random.choice(opts)}")

# 5. !roll2d6 – roll two dice
@bot.command(name="roll2d6")
async def roll2d6(ctx):
    rolls = [random.randint(1, 6), random.randint(1, 6)]
    await ctx.send(f"🎲 You rolled: {rolls[0]} and {rolls[1]} (Total: {sum(rolls)})")

# 6. !random_number – pick a number between start and end
@bot.command(name="random_number")
async def random_number(ctx, start: int = 1, end: int = 100):
    await ctx.send(f"🔢 Your random number is: {random.randint(start, end)}")

# 7. !compliment – give a random compliment
@bot.command(name="compliment")
async def compliment(ctx):
    compliments = [
        "You're awesome!", "You're amazing!", "You're a star!",
        "Keep shining!", "You're wonderful!"
    ]
    await ctx.send(f"💖 {random.choice(compliments)}")

# 8. !joke – tell a joke
@bot.command(name="joke")
async def joke(ctx):
    jokes = [
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my computer I needed a break, and it said 'No problem — I’ll go to sleep!'"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

# 9. !flip – choose between two options
@bot.command(name="flip")
async def flip(ctx, option1: str, option2: str):
    await ctx.send(f"🎲 I choose: {random.choice([option1, option2])}")

# 10. !roll_percent – roll a number 1–100
@bot.command(name="roll_percent")
async def roll_percent(ctx):
    await ctx.send(f"📊 You got {random.randint(1, 100)}%!")

# 11. !random_color – pick a color
@bot.command(name="random_color")
async def random_color(ctx):
    colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Pink"]
    await ctx.send(f"🎨 Random color: {random.choice(colors)}")

# 12. !magic_number – pick a number 1–50
@bot.command(name="magic_number")
async def magic_number(ctx):
    await ctx.send(f"✨ Your magic number is {random.randint(1, 50)}")

# 13. !echo – repeat a message
@bot.command(name="echo")
async def echo(ctx, *, text):
    await ctx.send(f"🗣️ {text}")

# 14. !say_hi – simple greeting
@bot.command(name="say_hi")
async def say_hi(ctx):
    await ctx.send(f"👋 Hello {ctx.author.display_name}!")

# 15. !roll_dice – roll a single dice with optional sides
@bot.command(name="roll_dice")
async def roll_dice(ctx, sides: int = 6):
    await ctx.send(f"🎲 You rolled a {random.randint(1, sides)}")
    # 16. !roll_multiple – roll multiple dice with optional sides
@bot.command(name="roll_multiple")
async def roll_multiple(ctx, count: int = 2, sides: int = 6):
    rolls = [random.randint(1, sides) for _ in range(count)]
    await ctx.send(f"🎲 You rolled: {rolls} (Total: {sum(rolls)})")

# 17. !truth – give a random truth question
@bot.command(name="truth")
async def truth(ctx):
    truths = [
        "What's your biggest fear?",
        "Have you ever lied to your best friend?",
        "What's your most embarrassing moment?",
        "Do you have a secret hobby?"
    ]
    await ctx.send(f"🤔 Truth: {random.choice(truths)}")

# 18. !dare – give a random dare
@bot.command(name="dare")
async def dare(ctx):
    dares = [
        "Do 10 pushups right now!",
        "Send a funny selfie in this channel.",
        "Say something nice to the person on your left.",
        "Imitate your favorite animal for 30 seconds."
    ]
    await ctx.send(f"😎 Dare: {random.choice(dares)}")

# 19. !inspire – send a random inspirational quote
@bot.command(name="inspire")
async def inspire(ctx):
    quotes = [
        "Believe you can and you're halfway there.",
        "The only limit is your mind.",
        "Dream big. Work hard. Stay humble.",
        "Every day is a second chance."
    ]
    await ctx.send(f"💡 {random.choice(quotes)}")

# 20. !fact – random fun fact
@bot.command(name="fact")
async def fact(ctx):
    facts = [
        "Bananas are berries, but strawberries are not.",
        "Honey never spoils.",
        "Octopuses have three hearts.",
        "Sharks existed before trees."
    ]
    await ctx.send(f"🧠 Fun fact: {random.choice(facts)}")

# 21. !number_guess – simple guess a number game
@bot.command(name="number_guess")
async def number_guess(ctx, guess: int):
    answer = random.randint(1, 10)
    if guess == answer:
        await ctx.send(f"🎉 Correct! The number was {answer}.")
    else:
        await ctx.send(f"❌ Wrong! The number was {answer}.")

# 22. !reverse – reverse a message
@bot.command(name="reverse")
async def reverse(ctx, *, text):
    await ctx.send(f"🔄 {text[::-1]}")

# 23. !shout – make text uppercase
@bot.command(name="shout")
async def shout(ctx, *, text):
    await ctx.send(f"📢 {text.upper()}")

# 24. !whisper – make text lowercase
@bot.command(name="whisper")
async def whisper(ctx, *, text):
    await ctx.send(f"🤫 {text.lower()}")

# 25. !random_emote – pick a random server emoji
@bot.command(name="random_emote")
async def random_emote(ctx):
    if ctx.guild.emojis:
        await ctx.send(f"🎭 {random.choice(ctx.guild.emojis)}")
    else:
        await ctx.send("⚠️ No custom emojis on this server.")

# 26. !roll_range – roll a number within a custom range
@bot.command(name="roll_range")
async def roll_range(ctx, start: int, end: int):
    await ctx.send(f"🎲 Rolled: {random.randint(start, end)}")

# 27. !flip_coin_multiple – flip coin multiple times
@bot.command(name="flip_coin_multiple")
async def flip_coin_multiple(ctx, times: int = 3):
    results = [random.choice(["Heads", "Tails"]) for _ in range(times)]
    await ctx.send(f"🪙 Results: {', '.join(results)}")

# 28. !roll_1d20 – roll a d20 (for RPGs)
@bot.command(name="roll_1d20")
async def roll_1d20(ctx):
    await ctx.send(f"🎲 Rolled a d20: {random.randint(1, 20)}")

# 29. !roll_3d6 – roll three 6-sided dice
@bot.command(name="roll_3d6")
async def roll_3d6(ctx):
    rolls = [random.randint(1, 6) for _ in range(3)]
    await ctx.send(f"🎲 Rolled: {rolls} (Total: {sum(rolls)})")

# 30. !random_pet – pick a random animal
@bot.command(name="random_pet")
async def random_pet(ctx):
    pets = ["Dog 🐶", "Cat 🐱", "Rabbit 🐰", "Hamster 🐹", "Parrot 🦜", "Turtle 🐢"]
    await ctx.send(f"🐾 Random pet: {random.choice(pets)}")
# =========================
# BOT RUNNER
# =========================

if __name__ == "__main__":
    import os

    # Optional: set a default activity/status
    import asyncio

    async def set_default_status():
        await bot.wait_until_ready()
        await bot.change_presence(
            activity=discord.Game(name="Solving mysteries!"), 
            status=discord.Status.online
        )



    # Run the bot
    TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_BOT_TOKEN"
    bot.run(TOKEN)
