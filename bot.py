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
# MODERATION COMMANDS (PREFIX) – 35
# =========================

# Example: Panic Lock / Unlock
@bot.command(name="panic_lock")
async def panic_lock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 All channels locked! Panic mode activated.")

@bot.command(name="panic_unlock")
async def panic_unlock(ctx):
    if not is_owner(ctx):
        return
    for channel in ctx.guild.channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 All channels unlocked! Panic mode deactivated.")

# Additional moderation commands would include:
# 3. lock_channel
# 4. unlock_channel
# 5. add_role
# 6. remove_role
# 7. server_info
# 8. member_info
# 9. role_info
# 10. mod_ping
# 11. clear
# 12. mod_notes
# 13. view_notes
# 14. temp_mute
# 15. temp_ban
# 16. add_emoji
# 17. remove_emoji
# 18. server_lock
# 19. server_unlock
# 20. create_role
# 21. delete_role
# 22. create_channel
# 23. delete_channel
# 24. top_boosters
# 25. channel_type
# 26. server_created
# 27. my_roles
# 28. my_info
# 29. bot_info
# 30. emoji_list
# 31. emoji_count
# 32. maintenance
# 33-35. Additional utility/mod commands as needed

# =========================
# PUBLIC FUN COMMANDS (PREFIX) – 20
# =========================

# Example fun commands
@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    import random
    await ctx.send(f"🎲 You rolled a {random.randint(1, sides)}")

@bot.command(name="rps")
async def rps(ctx, choice: str):
    import random
    options = ["rock", "paper", "scissors"]
    choice = choice.lower()
    if choice not in options:
        return await ctx.send("❌ Pick rock, paper, or scissors!")
    bot_choice = random.choice(options)
    result = "Tie!"
    if (choice == "rock" and bot_choice == "scissors") or \
       (choice == "paper" and bot_choice == "rock") or \
       (choice == "scissors" and bot_choice == "paper"):
        result = "You win!"
    elif choice != bot_choice:
        result = "You lose!"
    await ctx.send(f"You chose {choice}, bot chose {bot_choice}. {result}")

# AI-powered fun games using Groq (5/20 public)
@bot.command(name="would_you_rather")
async def would_you_rather(ctx):
    question = "Generate a fun 'Would you rather' question related to Discord servers."
    reply = await ask_groq(question)
    await ctx.send(reply)

@bot.command(name="trivia")
async def trivia(ctx):
    question = "Give a fun Discord-related trivia question with one answer."
    reply = await ask_groq(question)
    await ctx.send(reply)

@bot.command(name="riddle")
async def riddle(ctx):
    question = "Give a short Discord-themed riddle."
    reply = await ask_groq(question)
    await ctx.send(reply)

@bot.command(name="joke_game")
async def joke_game(ctx):
    question = "Tell a clean short Discord joke."
    reply = await ask_groq(question)
    await ctx.send(reply)

@bot.command(name="fact_game")
async def fact_game(ctx):
    question = "Give a surprising fact about Discord servers."
    reply = await ask_groq(question)
    await ctx.send(reply)

# Additional 15 public fun commands (randomized games, messages, etc.) can follow the same pattern# =========================
# MODERATION COMMANDS CONTINUED (PREFIX) 3–35
# OWNER ONLY
# =========================

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

# 12. Mod notes (add)
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

# 18. Server lock (prevents @everyone messaging)
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
    if not is_owner(ctx):
        return
    roles = [r.name for r in ctx.author.roles if r.name != "@everyone"]
    await ctx.send(f"Your roles: {', '.join(roles) if roles else 'None'}")

# 28. My info
@bot.command(name="my_info")
async def my_info(ctx):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title=f"{ctx.author.display_name} Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=ctx.author.id)
    embed.add_field(name="Joined Server", value=ctx.author.joined_at)
    embed.add_field(name="Account Created", value=ctx.author.created_at)
    await ctx.send(embed=embed)

# 29. Bot info
@bot.command(name="bot_info")
async def bot_info(ctx):
    if not is_owner(ctx):
        return
    embed = discord.Embed(title="Bot Info", color=discord.Color.blue())
    embed.add_field(name="Bot Name", value=bot.user.name)
    embed.add_field(name="ID", value=bot.user.id)
    embed.add_field(name="Servers", value=len(bot.guilds))
    await ctx.send(embed=embed)

# 30. Emoji list
@bot.command(name="emoji_list")
async def emoji_list(ctx):
    if not is_owner(ctx):
        return
    emojis = [str(e) for e in ctx.guild.emojis]
    await ctx.send(f"Emojis: {' '.join(emojis) if emojis else 'None'}")

# 31. Emoji count
@bot.command(name="emoji_count")
async def emoji_count(ctx):
    if not is_owner(ctx):
        return
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

# 33–35. Additional utility/mod commands placeholders
# Add custom owner-only commands here as needed
# =========================
# MODERATION COMMANDS CONTINUED (33–35)
# =========================

# 33. View audit log (recent 10 actions)
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


# =========================
# PUBLIC FUN COMMANDS – 20 TOTAL
# 15 fun/randomized, 5 AI (Groq) games
# =========================

# 1. !roll – roll a dice
@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    number = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a {number}!")

# 2. !coin – flip a coin
@bot.command(name="coin")
async def coin(ctx):
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

# 3. !rps – rock paper scissors
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

# 4. !8ball – random answer
@bot.command(name="8ball")
async def eight_ball(ctx, *, question):
    answers = ["Yes", "No", "Maybe", "Definitely", "Ask later"]
    await ctx.send(f"🎱 {random.choice(answers)}")

# 5. !choose – pick one option
@bot.command(name="choose")
async def choose(ctx, *, options):
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if not opts:
        await ctx.send("❌ Provide options separated by commas.")
        return
    await ctx.send(f"✅ I choose: {random.choice(opts)}")

# 6. !roll2d6 – roll two dice
@bot.command(name="roll2d6")
async def roll2d6(ctx):
    rolls = [random.randint(1, 6), random.randint(1, 6)]
    await ctx.send(f"🎲 You rolled: {rolls[0]} and {rolls[1]} (Total: {sum(rolls)})")

# 7. !random_number
@bot.command(name="random_number")
async def random_number(ctx, start: int = 1, end: int = 100):
    await ctx.send(f"🔢 Your random number is: {random.randint(start, end)}")

# 8. !compliment
@bot.command(name="compliment")
async def compliment(ctx):
    compliments = [
        "You're awesome!", "You're amazing!", "You're a star!",
        "Keep shining!", "You're wonderful!"
    ]
    await ctx.send(f"💖 {random.choice(compliments)}")

# 9. !joke
@bot.command(name="joke")
async def joke(ctx):
    jokes = [
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my computer I needed a break, and it said 'No problem — I’ll go to sleep!'"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

# 10. !flip – choose between two options
@bot.command(name="flip")
async def flip(ctx, option1: str, option2: str):
    await ctx.send(f"🎲 I choose: {random.choice([option1, option2])}")

# 11. !would_you_rather (AI/Groq)
@bot.command(name="would_you_rather")
async def would_you_rather(ctx):
    question = "Generate a fun 'Would you rather' question about Discord or servers."
    reply = await ask_groq(question)
    await ctx.send(f"🤔 {reply}")

# 12. !trivia (AI/Groq)
@bot.command(name="trivia")
async def trivia(ctx):
    question = "Generate a short fun trivia question with one correct answer."
    reply = await ask_groq(question)
    await ctx.send(f"❓ {reply}")

# 13. !riddle (AI/Groq)
@bot.command(name="riddle")
async def riddle(ctx):
    question = "Give a short riddle in one sentence."
    reply = await ask_groq(question)
    await ctx.send(f"🧩 {reply}")

# 14. !advice (AI/Groq)
@bot.command(name="advice")
async def advice(ctx):
    question = "Give a small piece of fun safe advice for Discord users."
    reply = await ask_groq(question)
    await ctx.send(f"💡 {reply}")

# 15. !story (AI/Groq)
@bot.command(name="story")
async def story(ctx):
    question = "Give a one-sentence story prompt for Discord creativity."
    reply = await ask_groq(question)
    await ctx.send(f"📖 {reply}")

# 16. !echo
@bot.command(name="echo")
async def echo(ctx, *, text):
    await ctx.send(f"🗣️ {text}")

# 17. !say_hi
@bot.command(name="say_hi")
async def say_hi(ctx):
    await ctx.send(f"👋 Hello {ctx.author.display_name}!")

# 18. !roll_percent
@bot.command(name="roll_percent")
async def roll_percent(ctx):
    await ctx.send(f"📊 You got {random.randint(1, 100)}%!")

# 19. !random_color
@bot.command(name="random_color")
async def random_color(ctx):
    colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Pink"]
    await ctx.send(f"🎨 Random color: {random.choice(colors)}")

# 20. !magic_number
@bot.command(name="magic_number")
async def magic_number(ctx):
    await ctx.send(f"✨ Your magic number is {random.randint(1, 50)}")
@bot.command(name="troll")
async def troll(ctx, member: discord.Member):
    if not is_owner(ctx):
        return  # Only owner can use

    # Save the member's current roles (excluding @everyone)
    old_roles = [role for role in member.roles if role.name != "@everyone"]

    # Create a temporary invite (valid for 10 minutes, 1 use)
    invite = await ctx.channel.create_invite(max_age=600, max_uses=1, unique=True)

    # DM the member
    try:
        embed = discord.Embed(
            title=f"You have been banned from <@907711912375095367> Server: Sab Hub🎄",
            description=(
                "Reason: not doing work, never come back here\n\n"
                "LOL I'm jk! Join back, I'll restore your roles. Don't mess about though.\n"
                f"Invite link (10 mins): {invite.url}"
            ),
            color=discord.Color.blue()
        )
        await member.send(embed=embed)
    except:
        # fallback if embed fails in DMs
        await member.send(
            f"You have been banned from <@907711912375095367> Server: Sab Hub🎄\n"
            "Reason: not doing work, never come back here\n\n"
            "LOL I'm jk! Join back, I'll restore your roles. Don't mess about though.\n"
            f"Invite link (10 mins): {invite.url}"
        )

    # Kick the member after DM
    await member.kick(reason="Messing about")

    # Wait for them to rejoin, then restore roles
    def check(m):
        return m.id == member.id and m.guild == ctx.guild

    try:
        rejoined = await bot.wait_for('member_join', timeout=600, check=check)
        if old_roles:
            await rejoined.add_roles(*old_roles)
            await ctx.send(f"✅ {member.display_name} has rejoined and roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⚠️ {member.display_name} did not rejoin within 10 minutes.")
        import os

if __name__ == "__main__":
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not DISCORD_BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    
    try:
        print("Starting bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")
