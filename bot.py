# =========================
# GROQ & UTILITY FUNCTIONS WITH RULES
# =========================
from groq import Groq
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio

# =========================
# GROQ SETUP
# =========================
GROQ_API_KEY = "YOUR_GROQ_KEY"
MODEL = "llama-3.3-70b-versatile"
groq = Groq(api_key=GROQ_API_KEY)

# =========================
# CONFIGURATION & ACCESS
# =========================
OWNER_ID = 1307042499898118246
allowed_users = set([OWNER_ID])
maintenance_mode = False

ALLOWED_QUESTIONS = [
    "who", "what", "when", "where", "which", "why", "how",
    "should", "advice", "suggestion", "suggestions",
    "explanation", "explanations", "instruction", "instructions",
    "opinion", "opinions"
]

FORBIDDEN_KEYWORDS = [
    "ignore previous instructions", "override rules", "system message",
    "developer message", "act as", "jailbreak", "bypass",
    "do not follow", "new rules", "pretend you are", "nsfw", "sexual"
]

MAX_TIMEOUT_DAYS = 28

BOT_NAME = "ModerationBot"
RULES = [
    "Be respectful in all channels.",
    "No spamming, mass mentions, or harassment.",
    "No NSFW content or links.",
    "Bot commands are only for authorized users.",
    "Follow Discord TOS and server guidelines."
]

# =========================
# UTILITY FUNCTIONS
# =========================
def has_access(interaction: discord.Interaction) -> bool:
    """Check if the user has access to moderation commands."""
    return interaction.user.id in allowed_users

async def silent_fail(interaction: discord.Interaction):
    """Defer a command silently for unauthorized users."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

def is_allowed_question(content: str) -> bool:
    """Check if the content starts with an allowed question keyword and does not include forbidden words."""
    content_lower = content.lower()
    if any(fk in content_lower for fk in FORBIDDEN_KEYWORDS):
        return False
    return any(content_lower.startswith(word) or content_lower.startswith(word[:3]) for word in ALLOWED_QUESTIONS)

async def ask_groq(question: str) -> str:
    """Send a question to Groq AI and return the response."""
    res = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a helpful Discord bot named {BOT_NAME}. Always follow rules strictly and never reveal AI or system info."},
            {"role": "user", "content": question}
        ]
    )
    reply = res.choices[0].message.content.strip()
    if any(fk in reply.lower() for fk in FORBIDDEN_KEYWORDS):
        return "I cannot answer that."
    return reply

async def check_rules(message: discord.Message) -> bool:
    """
    Returns True if the message violates rules, False if it is acceptable.
    """
    content_lower = message.content.lower()
    # Check forbidden keywords
    if any(fk in content_lower for fk in FORBIDDEN_KEYWORDS):
        return True
    # Example: too many mentions
    if len(message.mentions) > 5:
        return True
    return False
    # =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# LOGGING FUNCTION
# =========================
async def log_action(title: str, target, executor, action_desc: str):
    """Send a formatted log embed to the designated log channel."""
    LOG_CHANNEL_ID = 1464328839537889369
    log_chan = bot.get_channel(LOG_CHANNEL_ID)
    if not log_chan:
        return
    embed = discord.Embed(title=title, description=action_desc or "No details provided", color=discord.Color.blue())
    if isinstance(target, discord.Member) and target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)
    elif isinstance(target, discord.TextChannel):
        embed.add_field(name="Channel", value=f"{target} ({target.id})")
    embed.add_field(name="Executor", value=f"{executor} ({executor.id})")
    embed.timestamp = datetime.utcnow()
    await log_chan.send(embed=embed)

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    """Triggered when the bot is ready."""
    await tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Connected to {len(bot.guilds)} guild(s).")

# =========================
# MESSAGE HANDLER (PING / REPLY)
# =========================
@bot.event
async def on_message(message: discord.Message):
    """Handle messages mentioning the bot or replying to it."""
    if message.author.bot:
        return
    ALLOWED_CHANNELS = [1416480455670239232, 1366452761633226826]
    if message.channel.id not in ALLOWED_CHANNELS:
        return
    if maintenance_mode:
        return

    # Clean content for processing
    content_clean = message.content.replace(f"<@{bot.user.id}>", "").strip()

    # Respond only if pinged or replied
    is_pinged = bot.user in message.mentions
    is_replied = (
        message.reference and
        isinstance(message.reference.resolved, discord.Message) and
        message.reference.resolved.author.id == bot.user.id
    )

    if not (is_pinged or is_replied):
        await bot.process_commands(message)
        return

    # Rule check
    if await check_rules(message):
        await message.reply("⚠️ I cannot respond to messages that violate the rules.")
        await log_action("Rule Violation Blocked", message.author, bot.user, message.content)
        return

    # Handle allowed questions
    if is_allowed_question(content_clean):
        reply = await ask_groq(content_clean)
        await message.reply(f"🤖 {BOT_NAME} says: {reply}")
        await log_action("Bot Reply Sent", message.author, bot.user, f"Replied to: {content_clean}")

    # Process commands if any
    await bot.process_commands(message)
    # =========================
# MAINTENANCE MODE & ACCESS CONTROL
# =========================

# Maintenance mode flag
maintenance_mode = False

# Users allowed to use moderation commands
OWNER_ID = 1307042499898118246
allowed_users = set([OWNER_ID])

# =========================
# UTILITY FUNCTIONS
# =========================
async def silent_fail(interaction: discord.Interaction):
    """Defer interaction if user does not have access."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    return

def has_access(interaction: discord.Interaction):
    """Check if a user has permission to use moderation commands."""
    return interaction.user.id in allowed_users

# =========================
# TOGGLE MAINTENANCE MODE
# =========================
@tree.command(name="maintenance", description="Toggle maintenance mode")
async def maintenance(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)
    
    global maintenance_mode
    maintenance_mode = not maintenance_mode
    status = "ON" if maintenance_mode else "OFF"
    await interaction.response.send_message(f"Maintenance mode is now {status}.", ephemeral=True)
    await log_action("Maintenance Mode Toggled", interaction.user, interaction.user, f"Mode set to {status}")

# =========================
# GRANT ACCESS TO A USER
# =========================
@tree.command(name="grant_access", description="Grant a user permission to use commands")
async def grant_access(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)

    allowed_users.add(user.id)
    await interaction.response.send_message(f"Access granted to {user}.", ephemeral=True)
    await log_action("Access Granted", user, interaction.user, f"{user} can now use bot commands")

# =========================
# REVOKE ACCESS FROM A USER
# =========================
@tree.command(name="revoke_access", description="Revoke a user's permission to use commands")
async def revoke_access(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)

    allowed_users.discard(user.id)
    await interaction.response.send_message(f"Access revoked from {user}.", ephemeral=True)
    await log_action("Access Revoked", user, interaction.user, f"{user} can no longer use bot commands")
    # =========================
# PUBLIC FUN / UTILITY COMMANDS (EPHEMERAL)
# =========================

# 1. Compliment
@tree.command(name="compliment", description="Get a personalized compliment from Groq")
async def compliment(interaction: discord.Interaction):
    question = f"Give a kind compliment to {interaction.user.display_name} in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Compliment Generated", interaction.user, interaction.user, reply)

# 2. Fact
@tree.command(name="fact", description="Get a random interesting fact from Groq")
async def fact(interaction: discord.Interaction):
    question = "Give one interesting fact in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Fact Generated", interaction.user, interaction.user, reply)

# 3. Joke
@tree.command(name="joke", description="Get a clean joke from Groq")
async def joke(interaction: discord.Interaction):
    question = "Tell a clean, short joke in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Joke Generated", interaction.user, interaction.user, reply)

# 4. Quote
@tree.command(name="quote", description="Get a motivational quote from Groq")
async def quote(interaction: discord.Interaction):
    question = "Give a motivational quote in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Quote Generated", interaction.user, interaction.user, reply)

# 5. Advice
@tree.command(name="advice", description="Get personalized advice from Groq")
async def advice(interaction: discord.Interaction, *, situation: str):
    question = f"Give short advice for this situation: {situation}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Advice Generated", interaction.user, interaction.user, reply)
    # =========================
# MODERATION COMMANDS (AUTHORIZED USERS ONLY)
# =========================

# 1. Change a member's nickname
@tree.command(name="nick_member", description="Change a member's nickname")
async def nick_member(interaction: discord.Interaction, member: discord.Member, *, nickname: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    old_nick = member.display_name
    await member.edit(nick=nickname)
    await interaction.response.send_message(f"{member} nickname changed from '{old_nick}' to '{nickname}'", ephemeral=True)
    await log_action("Nickname Changed", member, interaction.user, f"{old_nick} -> {nickname}")

# 2. Reset a member's nickname
@tree.command(name="un_nick_member", description="Reset a member's nickname")
async def un_nick_member(interaction: discord.Interaction, member: discord.Member):
    if not has_access(interaction):
        return await silent_fail(interaction)
    old_nick = member.display_name
    await member.edit(nick=None)
    await interaction.response.send_message(f"{member} nickname reset from '{old_nick}'", ephemeral=True)
    await log_action("Nickname Reset", member, interaction.user, f"Reset from {old_nick}")

# 3. Set a channel topic
@tree.command(name="set_topic", description="Set the topic for the current text channel")
async def set_topic(interaction: discord.Interaction, *, topic: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    old_topic = interaction.channel.topic
    await interaction.channel.edit(topic=topic)
    await interaction.response.send_message(f"Channel topic changed from '{old_topic}' to '{topic}'", ephemeral=True)
    await log_action("Channel Topic Changed", interaction.channel, interaction.user, f"{old_topic} -> {topic}")
    # =========================
# MODERATION COMMANDS (AUTHORIZED USERS ONLY) – PART 2
# =========================

# 4. Lock all channels in a category
@tree.command(name="lock_category", description="Lock all channels in a category")
async def lock_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    if not has_access(interaction):
        return await silent_fail(interaction)
    for c in category.channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=False, speak=False)
    await interaction.response.send_message(f"All channels in category '{category.name}' locked.", ephemeral=True)
    await log_action("Category Locked", category, interaction.user, "Locked all channels in category")

# 5. Unlock all channels in a category
@tree.command(name="unlock_category", description="Unlock all channels in a category")
async def unlock_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    if not has_access(interaction):
        return await silent_fail(interaction)
    for c in category.channels:
        await c.set_permissions(interaction.guild.default_role, send_messages=True, speak=True)
    await interaction.response.send_message(f"All channels in category '{category.name}' unlocked.", ephemeral=True)
    await log_action("Category Unlocked", category, interaction.user, "Unlocked all channels in category")

# 6. Get info about a role
@tree.command(name="role_info", description="Get detailed information about a role")
async def role_info(interaction: discord.Interaction, role: discord.Role):
    if not has_access(interaction):
        return await silent_fail(interaction)
    embed = discord.Embed(title=f"Role Info: {role.name}", color=discord.Color.blue())
    embed.add_field(name="Role ID", value=role.id)
    embed.add_field(name="Members", value=len(role.members))
    embed.add_field(name="Color", value=role.color)
    embed.add_field(name="Mentionable", value=role.mentionable)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_action("Role Info Viewed", role, interaction.user, None)

# 7. Kick a member
@tree.command(name="kick_member", description="Kick a member from the server")
async def kick_member(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} has been kicked. Reason: {reason}", ephemeral=True)
    await log_action("Member Kicked", member, interaction.user, f"Reason: {reason}")

# 8. Rename a role
@tree.command(name="rename_role", description="Rename a role in the server")
async def rename_role(interaction: discord.Interaction, role: discord.Role, *, new_name: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    old_name = role.name
    await role.edit(name=new_name)
    await interaction.response.send_message(f"Role '{old_name}' renamed to '{new_name}'", ephemeral=True)
    await log_action("Role Renamed", role, interaction.user, f"{old_name} -> {new_name}")

# 9. Change server icon
@tree.command(name="server_icon_change", description="Change the server's icon")
async def server_icon_change(interaction: discord.Interaction, url: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await interaction.response.send_message("Failed to fetch image.", ephemeral=True)
                return
            img_bytes = await resp.read()
    await interaction.guild.edit(icon=img_bytes)
    await interaction.response.send_message("Server icon updated.", ephemeral=True)
    await log_action("Server Icon Changed", interaction.guild, interaction.user, f"URL: {url}")

# 10. Troll kick (example, safe logging only)
@tree.command(name="troll_kick", description="Playful kick (for logging and fun, safe)")
async def troll_kick(interaction: discord.Interaction, member: discord.Member):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await interaction.response.send_message(f"{member} got troll-kicked! (Not actually kicked)", ephemeral=True)
    await log_action("Troll Kick Used", member, interaction.user, "Fun command used")
    # =========================
# MODERATION COMMANDS (AUTHORIZED USERS ONLY) – PART 3
# =========================

# 11. Timeout a member (with max chunking)
@tree.command(name="timeout_member", description="Temporarily timeout a member")
async def timeout_member(interaction: discord.Interaction, member: discord.Member, days: int = 1):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await apply_timeout(member, days)
    await interaction.response.send_message(f"{member} has been timed out for {days} day(s).", ephemeral=True)
    await log_action("Member Timed Out", member, interaction.user, f"Timeout for {days} day(s)")

# 12. Remove timeout from a member
@tree.command(name="remove_timeout", description="Remove timeout from a member")
async def remove_timeout(interaction: discord.Interaction, member: discord.Member):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await member.edit(timeout=None)
    await interaction.response.send_message(f"Timeout removed from {member}.", ephemeral=True)
    await log_action("Timeout Removed", member, interaction.user, "Timeout cleared")




# 15. Ban a member
@tree.command(name="ban_member", description="Ban a member from the server")
async def ban_member(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} has been banned. Reason: {reason}", ephemeral=True)
    await log_action("Member Banned", member, interaction.user, f"Reason: {reason}")

# 16. Unban a member
@tree.command(name="unban_member", description="Unban a member from the server")
async def unban_member(interaction: discord.Interaction, user_id: int):
    if not has_access(interaction):
        return await silent_fail(interaction)
    banned_users = await interaction.guild.bans()
    user = next((u.user for u in banned_users if u.user.id == user_id), None)
    if user:
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"{user} has been unbanned.", ephemeral=True)
        await log_action("Member Unbanned", user, interaction.user, "Unbanned successfully")
    else:
        await interaction.response.send_message("User not found in ban list.", ephemeral=True)

# 17. Slowmode a channel
@tree.command(name="set_slowmode", description="Set slowmode for a channel")
async def set_slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    if not has_access(interaction):
        return await silent_fail(interaction)
    channel = channel or interaction.channel
    await channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds} second(s) for {channel.mention}", ephemeral=True)
    await log_action("Slowmode Set", channel, interaction.user, f"{seconds}s")

# 18. Clear messages
@tree.command(name="clear_messages", description="Delete messages from a channel")
async def clear_messages(interaction: discord.Interaction, amount: int = 5, channel: discord.TextChannel = None):
    if not has_access(interaction):
        return await silent_fail(interaction)
    channel = channel or interaction.channel
    deleted = await channel.purge(limit=amount)
    await interaction.response.send_message(f"Deleted {len(deleted)} messages in {channel.mention}", ephemeral=True)
    await log_action("Messages Cleared", channel, interaction.user, f"{len(deleted)} messages")

@tree.command(name="pin_message", description="Pin a specific message")
@app_commands.describe(channel="Channel of the message", message_id="ID of the message to pin")
async def pin_message(interaction: discord.Interaction, channel: discord.TextChannel, message_id: int):
    msg = await channel.fetch_message(message_id)
    await msg.pin()
    await interaction.response.send_message(f"Pinned message {message_id} in {channel.mention}", ephemeral=True)

# 20. Unpin a message
@tree.command(name="unpin_message", description="Unpin a specific message")
async def unpin_message(interaction: discord.Interaction, message: discord.Message):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await message.unpin()
    await interaction.response.send_message("Message unpinned.", ephemeral=True)
    await log_action("Message Unpinned", message.channel, interaction.user, f"Message ID: {message.id}")
    # =========================
# MODERATION COMMANDS (AUTHORIZED USERS ONLY) – PART 4
# =========================

# 21. Mute a member (text only)
@tree.command(name="mute_member", description="Mute a member in text channels")
async def mute_member(interaction: discord.Interaction, member: discord.Member):
    if not has_access(interaction):
        return await silent_fail(interaction)
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await interaction.guild.create_role(name="Muted", reason="Automatic mute role")
        for channel in interaction.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    await member.add_roles(muted_role)
    await interaction.response.send_message(f"{member} has been muted.", ephemeral=True)
    await log_action("Member Muted", member, interaction.user, "Muted with role 'Muted'")

# 22. Unmute a member
@tree.command(name="unmute_member", description="Unmute a member")
async def unmute_member(interaction: discord.Interaction, member: discord.Member):
    if not has_access(interaction):
        return await silent_fail(interaction)
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await interaction.response.send_message(f"{member} has been unmuted.", ephemeral=True)
        await log_action("Member Unmuted", member, interaction.user, "Removed 'Muted' role")
    else:
        await interaction.response.send_message(f"{member} is not muted.", ephemeral=True)

# 23. Lock a channel
@tree.command(name="lock_channel", description="Lock a text channel")
async def lock_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not has_access(interaction):
        return await silent_fail(interaction)
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"{channel.mention} is now locked.", ephemeral=True)
    await log_action("Channel Locked", channel, interaction.user, "Send messages disabled for @everyone")

# 24. Unlock a channel
@tree.command(name="unlock_channel", description="Unlock a text channel")
async def unlock_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not has_access(interaction):
        return await silent_fail(interaction)
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"{channel.mention} is now unlocked.", ephemeral=True)
    await log_action("Channel Unlocked", channel, interaction.user, "Send messages enabled for @everyone")

# 25. Change server name
@tree.command(name="change_server_name", description="Change the server's name")
async def change_server_name(interaction: discord.Interaction, *, name: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    old_name = interaction.guild.name
    await interaction.guild.edit(name=name)
    await interaction.response.send_message(f"Server name changed from '{old_name}' to '{name}'", ephemeral=True)
    await log_action("Server Name Changed", interaction.guild, interaction.user, f"{old_name} -> {name}")

# 26. Change server icon
@tree.command(name="change_server_icon", description="Change the server icon")
async def change_server_icon(interaction: discord.Interaction, url: str):
    if not has_access(interaction):
        return await silent_fail(interaction)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await interaction.response.send_message("Failed to fetch image.", ephemeral=True)
                return
            img_bytes = await resp.read()
    await interaction.guild.edit(icon=img_bytes)
    await interaction.response.send_message("Server icon updated.", ephemeral=True)
    await log_action("Server Icon Changed", interaction.guild, interaction.user, f"URL: {url}")

# 27. Add role to member
@tree.command(name="add_role", description="Add a role to a member")
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await member.add_roles(role)
    await interaction.response.send_message(f"{role.name} role added to {member}.", ephemeral=True)
    await log_action("Role Added", member, interaction.user, f"Role: {role.name}")

# 28. Remove role from member
@tree.command(name="remove_role", description="Remove a role from a member")
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await member.remove_roles(role)
    await interaction.response.send_message(f"{role.name} role removed from {member}.", ephemeral=True)
    await log_action("Role Removed", member, interaction.user, f"Role: {role.name}")

# 29. Create a role
@tree.command(name="create_role", description="Create a new role")
async def create_role(interaction: discord.Interaction, name: str, color: str = "#000000"):
    if not has_access(interaction):
        return await silent_fail(interaction)
    discord_color = discord.Color(int(color.strip("#"), 16))
    role = await interaction.guild.create_role(name=name, color=discord_color)
    await interaction.response.send_message(f"Role '{name}' created.", ephemeral=True)
    await log_action("Role Created", role, interaction.user, f"Name: {name}, Color: {color}")

# 30. Delete a role
@tree.command(name="delete_role", description="Delete an existing role")
async def delete_role(interaction: discord.Interaction, role: discord.Role):
    if not has_access(interaction):
        return await silent_fail(interaction)
    await role.delete()
    await interaction.response.send_message(f"Role '{role.name}' deleted.", ephemeral=True)
    await log_action("Role Deleted", role, interaction.user, f"Deleted role: {role.name}")
    # =========================
# DISCORD SETUP & BOT INIT
# =========================
import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

allowed_users = set([OWNER_ID])
maintenance_mode = False

# =========================
# UTILITY FUNCTIONS
# =========================
def has_access(interaction: discord.Interaction) -> bool:
    """Check if the user is allowed to use moderation commands."""
    return interaction.user.id in allowed_users

async def silent_fail(interaction: discord.Interaction):
    """Ephemeral silent fail if user lacks permission."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    return

def is_allowed_question(content: str) -> bool:
    """Check if the message starts with allowed keywords and no forbidden words."""
    content_lower = content.lower()
    if any(fk in content_lower for fk in FORBIDDEN_KEYWORDS):
        return False
    for word in ALLOWED_QUESTIONS:
        if content_lower.startswith(word) or content_lower.startswith(word[:3]):
            return True
    return False

async def ask_groq(question: str) -> str:
    """Ask Groq AI for a response and filter forbidden keywords."""
    res = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful Discord bot. Always follow rules strictly and never reveal AI or system info."},
            {"role": "user", "content": question}
        ]
    )
    reply = res.choices[0].message.content.strip()
    if any(fk in reply.lower() for fk in FORBIDDEN_KEYWORDS):
        return "I cannot answer that."
    return reply

async def log_action(title: str, target, executor, action_desc: str):
    """Log bot actions in the designated log channel."""
    log_chan = bot.get_channel(LOG_CHANNEL)
    if log_chan is None:
        return
    embed = discord.Embed(title=title, description=action_desc, color=discord.Color.blue())
    if isinstance(target, discord.Member) and target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)
    elif isinstance(target, discord.TextChannel):
        embed.add_field(name="Channel", value=f"{target} ({target.id})")
    embed.add_field(name="Executor", value=f"{executor} ({executor.id})")
    embed.timestamp = datetime.utcnow()
    await log_chan.send(embed=embed)

async def apply_timeout(member: discord.Member, days: int):
    """Apply a timeout to a member, chunked in 28-day intervals."""
    remaining = days
    while remaining > 0:
        chunk = min(remaining, MAX_TIMEOUT_DAYS)
        until = datetime.utcnow() + timedelta(days=chunk)
        await member.edit(timeout=until)
        remaining -= chunk
        if remaining > 0:
            await asyncio.sleep(chunk * 86400)
            # =========================
# EVENTS & MESSAGE HANDLING
# =========================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots
    if message.author.bot:
        return

    # Only respond in allowed channels
    if message.channel.id not in ALLOWED_CHANNELS:
        return

    # Respect maintenance mode
    if maintenance_mode:
        return

    # Remove bot mention from content
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()

    # Detect if the bot is pinged or message is a reply to the bot
    is_pinged = bot.user in message.mentions
    is_replied = (
        message.reference
        and isinstance(message.reference.resolved, discord.Message)
        and message.reference.resolved.author.id == bot.user.id
    )

    # Only proceed if pinged or replied to
    if not (is_pinged or is_replied):
        await bot.process_commands(message)
        return

    # Check for rule violations
    if await check_rules(message):
        await message.reply("⚠️ I cannot respond to messages that violate the rules.")
        await log_action("Rule Violation Blocked", message.author, bot.user, message.content)
        return

    # Special case: personal questions like "Who am I?"
    if content.lower() == "who am i":
        await message.reply(f"🤖 You are {message.author} with ID {message.author.id}.")
        await log_action("Who Am I Answered", message.author, bot.user, message.content)
        return

    # Otherwise, ask Groq for a reply if content is allowed
    if is_allowed_question(content):
        try:
            reply = await ask_groq(content)
        except Exception as e:
            reply = "⚠️ Something went wrong while generating a response."
            await log_action("AI Error", message.author, bot.user, str(e))

        await message.reply(f"🤖 {BOT_NAME} says: {reply}")
        await log_action("Bot Reply Sent", message.author, bot.user, f"Replied to: {content}")

    # Process any commands after AI response
    await bot.process_commands(message)
    # =========================
# MAINTENANCE & ACCESS CONTROL
# =========================
@tree.command(name="maintenance", description="Toggle maintenance mode (owner only)")
async def maintenance(interaction: discord.Interaction):
    global maintenance_mode
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)

    maintenance_mode = not maintenance_mode
    await interaction.response.send_message(
        f"Maintenance mode: {maintenance_mode}", ephemeral=True
    )
    await log_action(
        "Maintenance Mode Toggled", interaction.user, interaction.user, f"Mode set to {maintenance_mode}"
    )

@tree.command(name="grant_access", description="Grant user access to bot commands (owner only)")
async def grant_access(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)

    allowed_users.add(user.id)
    await interaction.response.send_message(
        f"Access granted to {user}", ephemeral=True
    )
    await log_action("Access Granted", user, interaction.user, f"{user} can now use bot commands")

@tree.command(name="revoke_access", description="Revoke user access to bot commands (owner only)")
async def revoke_access(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        return await silent_fail(interaction)

    allowed_users.discard(user.id)
    await interaction.response.send_message(
        f"Access revoked from {user}", ephemeral=True
    )
    await log_action("Access Revoked", user, interaction.user, f"{user} can no longer use bot commands")
    # =========================
# PUBLIC FUN / UTILITY COMMANDS (EPHEMERAL)
# =========================

# 1. Compliment
@tree.command(name="compliment", description="Get a personalized compliment from Groq")
async def compliment(interaction: discord.Interaction):
    question = f"Give a kind compliment to {interaction.user.display_name} in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Compliment Generated", interaction.user, interaction.user, reply)

# 2. Fact
@tree.command(name="fact", description="Get a random interesting fact from Groq")
async def fact(interaction: discord.Interaction):
    question = "Give one interesting fact in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Fact Generated", interaction.user, interaction.user, reply)

# 3. Joke
@tree.command(name="joke", description="Get a joke from Groq")
async def joke(interaction: discord.Interaction):
    question = "Tell a clean, short joke in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Joke Generated", interaction.user, interaction.user, reply)

# 4. Quote
@tree.command(name="quote", description="Get a motivational quote from Groq")
async def quote(interaction: discord.Interaction):
    question = "Give a motivational quote in one sentence."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Quote Generated", interaction.user, interaction.user, reply)

# 5. Advice
@tree.command(name="advice", description="Get personalized advice from Groq")
async def advice(interaction: discord.Interaction, *, situation: str):
    question = f"Give short advice for this situation: {situation}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Advice Generated", interaction.user, interaction.user, reply)

# 6. Suggestion
@tree.command(name="suggestion", description="Get a suggestion from Groq")
async def suggestion(interaction: discord.Interaction, *, topic: str):
    question = f"Give a helpful suggestion for: {topic}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Suggestion Generated", interaction.user, interaction.user, reply)

# 7. Explanation
@tree.command(name="explanation", description="Get an explanation from Groq")
async def explanation(interaction: discord.Interaction, *, topic: str):
    question = f"Explain briefly: {topic}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Explanation Generated", interaction.user, interaction.user, reply)

# 8. Opinion
@tree.command(name="opinion", description="Get an opinion from Groq")
async def opinion(interaction: discord.Interaction, *, topic: str):
    question = f"What is your opinion on: {topic}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Opinion Generated", interaction.user, interaction.user, reply)

# 9. Instruction
@tree.command(name="instruction", description="Get instructions from Groq")
async def instruction(interaction: discord.Interaction, *, task: str):
    question = f"Provide step-by-step instructions for: {task}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Instruction Generated", interaction.user, interaction.user, reply)

# 10. Suggestion List
@tree.command(name="suggestions", description="Get multiple suggestions from Groq")
async def suggestions(interaction: discord.Interaction, *, topic: str):
    question = f"Give 3 suggestions about: {topic}"
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Suggestions Generated", interaction.user, interaction.user, reply)
    # =========================
# PUBLIC FUN / GAME COMMANDS (EPHEMERAL)
# =========================
import random

# 1. Flip a coin
@tree.command(name="flip_coin", description="Flip a coin: heads or tails")
async def flip_coin(interaction: discord.Interaction):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await interaction.response.send_message(f"You flipped: {result}", ephemeral=True)
    await log_action("Coin Flipped", interaction.user, interaction.user, result)

# 2. Roll a dice
@tree.command(name="roll_dice", description="Roll a 6-sided dice")
async def roll_dice(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"You rolled a {result} 🎲", ephemeral=True)
    await log_action("Dice Rolled", interaction.user, interaction.user, f"Rolled {result}")

# 3. Random number
@tree.command(name="random_number", description="Generate a random number between 1 and 100")
async def random_number(interaction: discord.Interaction):
    number = random.randint(1, 100)
    await interaction.response.send_message(f"Your random number: {number}", ephemeral=True)
    await log_action("Random Number Generated", interaction.user, interaction.user, str(number))

# 4. Rock Paper Scissors
@tree.command(name="rps", description="Play Rock Paper Scissors")
async def rps(interaction: discord.Interaction, choice: str):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    user_choice = choice.lower()
    if user_choice not in choices:
        await interaction.response.send_message("Invalid choice! Use rock, paper, or scissors.", ephemeral=True)
        return
    if user_choice == bot_choice:
        result = "It's a tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "You lose! 😢"
    await interaction.response.send_message(f"You chose {user_choice}, I chose {bot_choice}. {result}", ephemeral=True)
    await log_action("RPS Played", interaction.user, interaction.user, f"{user_choice} vs {bot_choice} => {result}")

# 5. 8 Ball
@tree.command(name="8ball", description="Ask the magic 8-ball a question")
async def eight_ball(interaction: discord.Interaction, *, question: str):
    responses = [
        "Yes ✅", "No ❌", "Maybe 🤔", "Absolutely! 🌟", "Definitely not! 🚫",
        "Ask again later ⏳", "It is certain ✔️", "Very doubtful ❓"
    ]
    reply = random.choice(responses)
    await interaction.response.send_message(f"Question: {question}\nAnswer: {reply}", ephemeral=True)
    await log_action("8Ball Question Asked", interaction.user, interaction.user, f"{question} => {reply}")

# 6. Roll a custom dice
@tree.command(name="roll_custom", description="Roll a dice with custom sides")
async def roll_custom(interaction: discord.Interaction, sides: int):
    if sides < 2 or sides > 1000:
        await interaction.response.send_message("Sides must be between 2 and 1000!", ephemeral=True)
        return
    result = random.randint(1, sides)
    await interaction.response.send_message(f"You rolled a {result} on a {sides}-sided dice 🎲", ephemeral=True)
    await log_action("Custom Dice Rolled", interaction.user, interaction.user, f"{result}/{sides}")

# 7. Random choice
@tree.command(name="choose", description="Pick randomly from a list of options")
async def choose(interaction: discord.Interaction, *, options: str):
    items = [o.strip() for o in options.split(",") if o.strip()]
    if not items:
        await interaction.response.send_message("Provide at least one option separated by commas.", ephemeral=True)
        return
    pick = random.choice(items)
    await interaction.response.send_message(f"I chose: {pick}", ephemeral=True)
    await log_action("Random Choice Made", interaction.user, interaction.user, pick)

# 8. Coin streak
@tree.command(name="coin_streak", description="Try a coin streak")
async def coin_streak(interaction: discord.Interaction, flips: int = 5):
    if flips < 1 or flips > 20:
        await interaction.response.send_message("You can flip between 1 and 20 coins.", ephemeral=True)
        return
    results = [random.choice(["Heads", "Tails"]) for _ in range(flips)]
    await interaction.response.send_message(f"Coin streak ({flips} flips): {', '.join(results)}", ephemeral=True)
    await log_action("Coin Streak Flipped", interaction.user, interaction.user, ", ".join(results))

# 9. Guess number
@tree.command(name="guess_number", description="Try to guess a random number")
async def guess_number(interaction: discord.Interaction, guess: int):
    number = random.randint(1, 100)
    if guess == number:
        result = "Amazing! You guessed it! 🎉"
    elif guess < number:
        result = "Too low! 📉"
    else:
        result = "Too high! 📈"
    await interaction.response.send_message(f"The number was {number}. {result}", ephemeral=True)
    await log_action("Guess Number Played", interaction.user, interaction.user, f"Guessed {guess}, number {number} => {result}")

# 10. Random word
@tree.command(name="random_word", description="Get a random word")
async def random_word(interaction: discord.Interaction):
    words = ["Python", "Discord", "Groq", "Bot", "Fun", "Game", "Challenge", "Magic", "Code", "Random"]
    word = random.choice(words)
    await interaction.response.send_message(f"Random word: {word}", ephemeral=True)
    await log_action("Random Word Generated", interaction.user, interaction.user, word)

# 11. Roll multiple dice
@tree.command(name="roll_multiple", description="Roll multiple 6-sided dice")
async def roll_multiple(interaction: discord.Interaction, count: int = 2):
    if count < 1 or count > 20:
        await interaction.response.send_message("You can roll between 1 and 20 dice.", ephemeral=True)
        return
    results = [random.randint(1, 6) for _ in range(count)]
    await interaction.response.send_message(f"Rolled {count} dice: {', '.join(map(str, results))}", ephemeral=True)
    await log_action("Multiple Dice Rolled", interaction.user, interaction.user, ", ".join(map(str, results)))

# 12. Pick a card
@tree.command(name="pick_card", description="Draw a random playing card")
async def pick_card(interaction: discord.Interaction):
    suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    card = f"{random.choice(ranks)} of {random.choice(suits)}"
    await interaction.response.send_message(f"You drew: {card} 🃏", ephemeral=True)
    await log_action("Card Picked", interaction.user, interaction.user, card)

# 13. Roll percentile
@tree.command(name="roll_percentile", description="Roll a percentile dice (1-100)")
async def roll_percentile(interaction: discord.Interaction):
    result = random.randint(1, 100)
    await interaction.response.send_message(f"Percentile roll: {result}", ephemeral=True)
    await log_action("Percentile Rolled", interaction.user, interaction.user, str(result))

# 14. Spin wheel
@tree.command(name="spin_wheel", description="Spin a wheel of fortune")
async def spin_wheel(interaction: discord.Interaction):
    segments = ["Win 🎉", "Lose 😢", "Try Again 🔄", "Jackpot 💰", "Nothing 😐"]
    result = random.choice(segments)
    await interaction.response.send_message(f"Wheel result: {result}", ephemeral=True)
    await log_action("Wheel Spun", interaction.user, interaction.user, result)

# 15. Magic number
@tree.command(name="magic_number", description="Get a magic number between 1-50")
async def magic_number(interaction: discord.Interaction):
    number = random.randint(1, 50)
    await interaction.response.send_message(f"Your magic number is {number} ✨", ephemeral=True)
    await log_action("Magic Number Generated", interaction.user, interaction.user, str(number))
    # =========================
# PUBLIC SERVER INFO / UTILITY COMMANDS (EPHEMERAL)
# =========================

# 1. Server name
@tree.command(name="server_name", description="Show the server's name")
async def server_name(interaction: discord.Interaction):
    await interaction.response.send_message(f"This server's name is: {interaction.guild.name}", ephemeral=True)
    await log_action("Server Name Viewed", interaction.channel, interaction.user, interaction.guild.name)

# 2. Server ID
@tree.command(name="server_id", description="Show the server's ID")
async def server_id(interaction: discord.Interaction):
    await interaction.response.send_message(f"This server's ID is: {interaction.guild.id}", ephemeral=True)
    await log_action("Server ID Viewed", interaction.channel, interaction.user, str(interaction.guild.id))

# 3. Member count
@tree.command(name="member_count", description="Show the number of members in the server")
async def member_count(interaction: discord.Interaction):
    count = interaction.guild.member_count
    await interaction.response.send_message(f"This server has {count} members.", ephemeral=True)
    await log_action("Member Count Viewed", interaction.channel, interaction.user, str(count))

# 4. Channel count
@tree.command(name="channel_count", description="Show total number of channels in server")
async def channel_count(interaction: discord.Interaction):
    total = len(interaction.guild.channels)
    await interaction.response.send_message(f"This server has {total} channels.", ephemeral=True)
    await log_action("Channel Count Viewed", interaction.channel, interaction.user, str(total))

# 5. Role count
@tree.command(name="role_count", description="Show total number of roles in server")
async def role_count(interaction: discord.Interaction):
    total = len(interaction.guild.roles)
    await interaction.response.send_message(f"This server has {total} roles.", ephemeral=True)
    await log_action("Role Count Viewed", interaction.channel, interaction.user, str(total))

# 6. Emoji list
@tree.command(name="emoji_list", description="Show all emojis in the server")
async def emoji_list(interaction: discord.Interaction):
    emojis = [str(e) for e in interaction.guild.emojis]
    await interaction.response.send_message(f"Emojis: {' '.join(emojis) if emojis else 'None'}", ephemeral=True)
    await log_action("Emoji List Viewed", interaction.channel, interaction.user, None)

# 7. Emoji count
@tree.command(name="emoji_count", description="Show the number of emojis in server")
async def emoji_count(interaction: discord.Interaction):
    count = len(interaction.guild.emojis)
    await interaction.response.send_message(f"This server has {count} emojis.", ephemeral=True)
    await log_action("Emoji Count Viewed", interaction.channel, interaction.user, str(count))

# 8. Server owner
@tree.command(name="server_owner", description="Show server owner")
async def server_owner(interaction: discord.Interaction):
    owner = interaction.guild.owner
    await interaction.response.send_message(f"Server owner: {owner} ({owner.id})", ephemeral=True)
    await log_action("Server Owner Viewed", interaction.channel, interaction.user, str(owner.id))

# 9. Server creation date
@tree.command(name="server_created", description="Show server creation date")
async def server_created(interaction: discord.Interaction):
    created = interaction.guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(f"{interaction.guild.name} was created on {created}", ephemeral=True)
    await log_action("Server Creation Date Viewed", interaction.channel, interaction.user, created)

# 10. Top boosters
@tree.command(name="top_boosters", description="List top 5 server boosters")
async def top_boosters(interaction: discord.Interaction):
    boosters = sorted(interaction.guild.premium_subscribers, key=lambda m: m.joined_at)[:5]
    names = [b.display_name for b in boosters]
    await interaction.response.send_message(f"Top Boosters: {', '.join(names) if names else 'None'}", ephemeral=True)
    await log_action("Top Boosters Viewed", interaction.channel, interaction.user, ", ".join(names) if names else "None")

# 11. Random text channel
@tree.command(name="random_channel", description="Pick a random text channel")
async def random_channel(interaction: discord.Interaction):
    text_channels = [c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
    channel = random.choice(text_channels)
    await interaction.response.send_message(f"Random channel: {channel.mention}", ephemeral=True)
    await log_action("Random Channel Picked", interaction.channel, interaction.user, str(channel.id))

# 12. My roles
@tree.command(name="my_roles", description="Show your roles")
async def my_roles(interaction: discord.Interaction):
    roles = [r.name for r in interaction.user.roles if r.name != "@everyone"]
    await interaction.response.send_message(f"Your roles: {', '.join(roles) if roles else 'None'}", ephemeral=True)
    await log_action("User Roles Viewed", interaction.channel, interaction.user, ", ".join(roles) if roles else "None")

# 13. My info
@tree.command(name="my_info", description="Show your Discord account info")
async def my_info(interaction: discord.Interaction):
    embed = discord.Embed(title=f"{interaction.user.display_name} Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=interaction.user.id)
    embed.add_field(name="Joined Server", value=interaction.user.joined_at)
    embed.add_field(name="Account Created", value=interaction.user.created_at)
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else "")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_action("My Info Viewed", interaction.channel, interaction.user, None)

# 14. Bot info
@tree.command(name="bot_info", description="Show bot info")
async def bot_info(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Info", color=discord.Color.blue())
    embed.add_field(name="Bot Name", value=bot.user.name)
    embed.add_field(name="ID", value=bot.user.id)
    embed.add_field(name="Servers", value=len(bot.guilds))
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_action("Bot Info Viewed", interaction.channel, interaction.user, None)

# 15. Channel type
@tree.command(name="channel_type", description="Check the type of a channel")
async def channel_type(interaction: discord.Interaction, channel: discord.abc.GuildChannel = None):
    channel = channel or interaction.channel
    await interaction.response.send_message(f"Channel {channel.name} is of type {type(channel).__name__}", ephemeral=True)
    await log_action("Channel Type Viewed", interaction.channel, interaction.user, str(channel.id))
    # =========================
# AI-GENERATED FUN / GAME COMMANDS (15)
# =========================
import random

# 1. Would You Rather
@tree.command(name="would_you_rather", description="Get a fun 'Would you rather' question")
async def would_you_rather(interaction: discord.Interaction):
    question = "Generate a fun and safe 'Would you rather' question. Answer as a friendly bot, do not mention AI or Groq."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Would You Rather Generated", interaction.user, interaction.user, reply)

# 2. Flip Coin
@tree.command(name="flip_coin", description="Flip a coin")
async def flip_coin(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 The coin landed on **{result}**!", ephemeral=True)
    await log_action("Coin Flipped", interaction.user, interaction.user, result)

# 3. Roll Dice
@tree.command(name="roll_dice", description="Roll a six-sided dice")
async def roll_dice(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 You rolled a **{result}**!", ephemeral=True)
    await log_action("Dice Rolled", interaction.user, interaction.user, str(result))

# 4. Random Number
@tree.command(name="random_number", description="Generate a random number")
async def random_number(interaction: discord.Interaction, min: int = 1, max: int = 100):
    number = random.randint(min, max)
    await interaction.response.send_message(f"🔢 Random number between {min} and {max}: **{number}**", ephemeral=True)
    await log_action("Random Number Generated", interaction.user, interaction.user, str(number))

# 5. Rock Paper Scissors
@tree.command(name="rps", description="Play Rock Paper Scissors")
async def rps(interaction: discord.Interaction, choice: str):
    options = ["rock", "paper", "scissors"]
    user_choice = choice.lower()
    if user_choice not in options:
        await interaction.response.send_message("❌ Invalid choice! Pick rock, paper, or scissors.", ephemeral=True)
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
    await interaction.response.send_message(f"You chose **{user_choice}**, bot chose **{bot_choice}**. {result}", ephemeral=True)
    await log_action("RPS Played", interaction.user, interaction.user, f"{user_choice} vs {bot_choice}: {result}")

# 6. AI Trivia
@tree.command(name="trivia", description="Get a random trivia question")
async def trivia(interaction: discord.Interaction):
    question = "Generate a fun trivia question with one correct answer. Present it as a friendly bot without mentioning AI or Groq."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Trivia Question Generated", interaction.user, interaction.user, reply)

# 7. AI Riddle
@tree.command(name="riddle", description="Get a riddle to solve")
async def riddle(interaction: discord.Interaction):
    question = "Give a short riddle in one sentence. Do not mention AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Riddle Generated", interaction.user, interaction.user, reply)

# 8. AI Joke Game
@tree.command(name="joke_game", description="Get a short joke")
async def joke_game(interaction: discord.Interaction):
    question = "Tell a clean, funny, short joke in one sentence. Do not reveal AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Joke Generated", interaction.user, interaction.user, reply)

# 9. AI Fact Game
@tree.command(name="fact_game", description="Get a fun fact")
async def fact_game(interaction: discord.Interaction):
    question = "Give a fun, surprising fact in one sentence. Do not reveal AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Fact Generated", interaction.user, interaction.user, reply)

# 10. AI Advice Game
@tree.command(name="advice_game", description="Get random advice")
async def advice_game(interaction: discord.Interaction):
    question = "Give a small piece of fun, safe advice. Do not reveal AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Advice Generated", interaction.user, interaction.user, reply)

# 11. AI Story Starter
@tree.command(name="story_starter", description="Get a story prompt")
async def story_starter(interaction: discord.Interaction):
    question = "Give a one-sentence story prompt for creativity. Do not mention AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Story Prompt Generated", interaction.user, interaction.user, reply)

# 12. AI Compliment Game
@tree.command(name="compliment_game", description="Get a compliment")
async def compliment_game(interaction: discord.Interaction):
    question = f"Give a short, kind compliment for {interaction.user.display_name}. Do not mention AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Compliment Generated", interaction.user, interaction.user, reply)

# 13. AI “This or That”
@tree.command(name="this_or_that", description="Get a fun 'this or that' question")
async def this_or_that(interaction: discord.Interaction):
    question = "Generate a fun 'this or that' question in one sentence. Do not reveal AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("This or That Generated", interaction.user, interaction.user, reply)

# 14. AI True or False
@tree.command(name="true_or_false", description="Get a random true or false statement")
async def true_or_false(interaction: discord.Interaction):
    question = "Give a fun true or false statement in one sentence. Do not mention AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("True or False Generated", interaction.user, interaction.user, reply)

# 15. AI Prediction
@tree.command(name="prediction", description="Get a fun random prediction")
async def prediction(interaction: discord.Interaction):
    question = "Give a short, fun, harmless prediction in one sentence. Do not reveal AI."
    reply = await ask_groq(question)
    await interaction.response.send_message(reply, ephemeral=True)
    await log_action("Prediction Generated", interaction.user, interaction.user, reply)
    import os

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not DISCORD_BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    
    try:
        print("Starting bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")
# =========================
# BOT RUN & GUILD-SYNC SETUP
# =========================
GUILD_IDS = [1366452760467472405, 1398723077004722206]  # Your server IDs

@bot.event
async def on_ready():
    # Sync commands to all your guilds for instant availability
    for guild_id in GUILD_IDS:
        guild_obj = discord.Object(id=guild_id)
        await tree.sync(guild=guild_obj)
    print(f"Logged in as {bot.user} | Commands synced to guilds: {GUILD_IDS}")
    print("Bot is ready. Whitelisted users can access all commands.")

# Utility to check command visibility
def is_command_visible(user_id: int, command_type: str = "public") -> bool:
    """
    Returns True if the command should show to this user.
    - command_type: "public" or "moderation"
    """
    if command_type == "public":
        return True
    elif command_type == "moderation":
        return user_id in allowed_users
    return False

# =========================
# RUN BOT
# =========================
import os
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot.run(DISCORD_BOT_TOKEN)
