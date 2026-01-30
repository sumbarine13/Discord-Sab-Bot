"""
Discord Bot with Groq AI
Owner: 1307042499898118246
"""
import os
import discord
from discord.ext import commands
import random
import asyncio
import aiohttp

# Owner ID
OWNER_ID = 1307042499898118246

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Store data
data = {
    "money": {},
    "warns": {},
    "whitelist": [],
    "blacklist": []
}

# === GROQ AI SERVICE ===
async def ask_groq(question):
    """Ask Groq AI a question"""
    api_key = os.getenv("GROQ_TOKEN") or os.getenv("GROQ_API_KEY")
    if not api_key:
        return "🤖 AI not configured. Add GROQ_TOKEN environment variable."
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{
                "role": "user",
                "content": question
            }],
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return "⚠️ AI service error"
    except:
        return "❌ Failed to connect to AI"

# === PERMISSION SYSTEM ===
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def can_use_mod():
    async def predicate(ctx):
        # Owner can always use
        if ctx.author.id == OWNER_ID:
            return True
        # Check whitelist
        if ctx.author.id in data["whitelist"]:
            return True
        # Check blacklist
        if ctx.author.id in data["blacklist"]:
            await ctx.send("⛔ You are blacklisted!")
            return False
        await ctx.send("⛔ Moderation commands are owner/whitelist only!")
        return False
    return commands.check(predicate)

# === EVENTS ===
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f"🔒 Owner: {OWNER_ID}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check for question words in ANY message (not just mentions)
    question_words = ["who", "what", "when", "where", "why", "how", "advice", "suggestion"]
    content_lower = message.content.lower()
    
    has_question_word = any(word in content_lower for word in question_words)
    is_mentioned = bot.user.mentioned_in(message)
    
    # Respond if mentioned OR has question words
    if is_mentioned or has_question_word:
        # For mentions without content
        if is_mentioned and len(message.content.strip()) < 5:
            await message.reply("🤖 How can I help you?")
            await bot.process_commands(message)
            return
        
        # Don't respond to commands
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return
        
        # Remove mention if present
        if is_mentioned:
            content = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        else:
            content = message.content.strip()
        
        if content:
            async with message.channel.typing():
                response = await ask_groq(content)
                await message.reply(response)
    
    await bot.process_commands(message)

# === WHITELIST/BLACKLIST COMMANDS ===
@bot.command()
@is_owner()
async def whitelist(ctx, action: str, member: discord.Member):
    """[OWNER] Manage whitelist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["whitelist"]:
            data["whitelist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to whitelist")
        else:
            await ctx.send("ℹ️ Already in whitelist")
    elif action.lower() in ["remove", "-"]:
        if member.id in data["whitelist"]:
            data["whitelist"].remove(member.id)
            await ctx.send(f"✅ Removed {member.mention} from whitelist")
        else:
            await ctx.send("ℹ️ Not in whitelist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def blacklist(ctx, action: str, member: discord.Member):
    """[OWNER] Manage blacklist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["blacklist"]:
            data["blacklist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to blacklist")
        else:
            await ctx.send("ℹ️ Already in blacklist")
    elif action.lower() in ["remove", "-"]:
        if member.id in data["blacklist"]:
            data["blacklist"].remove(member.id)
            await ctx.send(f"✅ Removed {member.mention} from blacklist")
        else:
            await ctx.send("ℹ️ Not in blacklist")
    else:
        await ctx.send("❌ Use: add/remove")

@bot.command()
@is_owner()
async def showlists(ctx):
    """[OWNER] Show whitelist and blacklist"""
    embed = discord.Embed(title="📋 Permission Lists", color=0x5865F2)
    
    wl = [f"<@{uid}>" for uid in data["whitelist"][:10]]
    bl = [f"<@{uid}>" for uid in data["blacklist"][:10]]
    
    embed.add_field(name=f"✅ Whitelist ({len(data['whitelist'])})", 
                   value="\n".join(wl) if wl else "Empty", inline=False)
    embed.add_field(name=f"❌ Blacklist ({len(data['blacklist'])})", 
                   value="\n".join(bl) if bl else "Empty", inline=False)
    
    await ctx.send(embed=embed)

# === TROLLKICK COMMAND ===
@bot.command()
@can_use_mod()
async def trollkick(ctx, member: discord.Member, *, reason="Trolling"):
    """Prank kick a member"""
    # Save roles
    roles = [role for role in member.roles if role != ctx.guild.default_role]
    
    try:
        # Create invite
        invite = await ctx.channel.create_invite(max_age=300, max_uses=1)
        await member.send(f"😜 You've been kicked! Just kidding! Rejoin: {invite.url}")
    except:
        pass
    
    # Kick
    await member.kick(reason=f"Troll kick: {reason}")
    await ctx.send(f"😂 {member.display_name} was troll kicked!")
    
    # Wait for rejoin
    def check(m):
        return m.id == member.id
    
    try:
        rejoined = await bot.wait_for('member_join', timeout=300, check=check)
        if roles:
            await rejoined.add_roles(*roles)
            await ctx.send(f"✅ {member.display_name} rejoined with roles!")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ {member.display_name} didn't rejoin")

# === MODERATION COMMANDS ===
@bot.command()
@can_use_mod()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """Kick a member"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@can_use_mod()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """Ban a member"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}")

@bot.command()
@can_use_mod()
async def purge(ctx, amount: int = 10):
    """Delete messages"""
    if amount > 100:
        await ctx.send("❌ Max 100 messages")
        return
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 Deleted {len(deleted)} messages")
    await asyncio.sleep(2)
    await msg.delete()

@bot.command()
@can_use_mod()
async def mute(ctx, member: discord.Member):
    """Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await member.add_roles(mute_role)
    await ctx.send(f"🔇 Muted {member.mention}")

@bot.command()
@can_use_mod()
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 Unmuted {member.mention}")

@bot.command()
@can_use_mod()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in data["warns"]:
        data["warns"][user_id] = []
    
    data["warns"][user_id].append(reason)
    await ctx.send(f"⚠️ Warned {member.mention}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["warns"] or not data["warns"][user_id]:
        await ctx.send(f"✅ {member.display_name} has no warnings")
        return
    
    warns = "\n".join([f"• {w}" for w in data["warns"][user_id][:10]])
    await ctx.send(f"📋 Warnings for {member.display_name}:\n{warns}")

@bot.command()
@can_use_mod()
async def lock(ctx):
    """Lock channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked")

@bot.command()
@can_use_mod()
async def unlock(ctx):
    """Unlock channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked")

# === FUN COMMANDS ===
@bot.command()
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def coinflip(ctx):
    """Flip a coin"""
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

@bot.command()
async def dice(ctx, dice: str = "1d6"):
    """Roll dice"""
    try:
        num, sides = map(int, dice.split('d'))
        rolls = [random.randint(1, sides) for _ in range(num)]
        await ctx.send(f"🎲 {sum(rolls)} ({', '.join(map(str, rolls))})")
    except:
        await ctx.send("❌ Use NdN (e.g., 2d6)")

@bot.command()
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choice = choice.lower()
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    if choice == bot_choice:
        result = "Tie! 🤝"
    elif (choice == 'rock' and bot_choice == 'scissors') or \
         (choice == 'paper' and bot_choice == 'rock') or \
         (choice == 'scissors' and bot_choice == 'paper'):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(f"**You:** {choice}\n**Bot:** {bot_choice}\n**{result}**")

@bot.command()
async def eightball(ctx, *, question):
    """Magic 8-ball"""
    answers = ['Yes', 'No', 'Maybe', 'Ask again']
    await ctx.send(f"🎱 {random.choice(answers)}")

@bot.command()
async def choose(ctx, *, options):
    """Choose between options"""
    choices = [opt.strip() for opt in options.split('or') if opt.strip()]
    await ctx.send(f"🤔 I choose: **{random.choice(choices)}**")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users"""
    user2 = user2 or ctx.author
    score = random.randint(0, 100)
    await ctx.send(f"💖 {user1} + {user2} = {score}%")

@bot.command()
async def joke(ctx):
    """Tell a joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What do you call a bear with no teeth? A gummy bear!"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

# === AI COMMANDS ===
@bot.command()
async def ask(ctx, *, question):
    """Ask AI a question"""
    async with ctx.channel.typing():
        answer = await ask_groq(question)
        await ctx.send(f"**🤖 AI:** {answer}")

@bot.command()
async def who(ctx, *, question):
    """Ask 'who' questions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"who: {question}")
        await ctx.send(f"**👤 Who?** {answer}")

@bot.command()
async def what(ctx, *, question):
    """Ask 'what' questions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"what: {question}")
        await ctx.send(f"**❓ What?** {answer}")

@bot.command()
async def when(ctx, *, question):
    """Ask 'when' questions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"when: {question}")
        await ctx.send(f"**⏰ When?** {answer}")

@bot.command()
async def where(ctx, *, question):
    """Ask 'where' questions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"where: {question}")
        await ctx.send(f"**📍 Where?** {answer}")

@bot.command()
async def why(ctx, *, question):
    """Ask 'why' questions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"why: {question}")
        await ctx.send(f"**🤔 Why?** {answer}")

@bot.command()
async def advice(ctx, *, topic):
    """Get advice"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"Give advice about {topic}")
        await ctx.send(f"**💡 Advice:** {answer}")

@bot.command()
async def suggestion(ctx, *, topic):
    """Get suggestions"""
    async with ctx.channel.typing():
        answer = await ask_groq(f"Suggest something about {topic}")
        await ctx.send(f"**💡 Suggestion:** {answer}")

# === UTILITY COMMANDS ===
@bot.command()
async def help(ctx):
    """Show help"""
    embed = discord.Embed(title="🤖 Bot Help", color=0x5865F2)
    embed.add_field(name="🔒 Moderation", value="`kick`, `ban`, `purge`, `mute`, `warn`, `trollkick`, `lock`, `unlock`", inline=False)
    embed.add_field(name="🤖 AI Commands", value="`ask`, `who`, `what`, `when`, `where`, `why`, `advice`, `suggestion`", inline=False)
    embed.add_field(name="🎮 Fun", value="`ping`, `coinflip`, `dice`, `rps`, `8ball`, `choose`, `ship`, `joke`", inline=False)
    embed.add_field(name="🛠️ Utility", value="`help`, `serverinfo`, `avatar`, `warnings`", inline=False)
    embed.set_footer(text="AI responds to messages with who/what/when/where/why/advice/suggestion")
    await ctx.send(embed=embed)

@bot.command()
async def cmds(ctx):
    """Show all commands"""
    await ctx.send(
        "**🔒 Moderation:** `!kick`, `!ban`, `!purge`, `!mute`, `!warn`, `!trollkick`, `!lock`, `!unlock`\n"
        "**🤖 AI:** `!ask`, `!who`, `!what`, `!when`, `!where`, `!why`, `!advice`, `!suggestion`\n"
        "**🎮 Fun:** `!ping`, `!coinflip`, `!dice`, `!rps`, `!8ball`, `!choose`, `!ship`, `!joke`\n"
        "**🛠️ Utility:** `!help`, `!serverinfo`, `!avatar`, `!warnings`\n\n"
        "**AI also responds to messages containing:** who, what, when, where, why, advice, suggestion"
    )

@bot.command()
async def serverinfo(ctx):
    """Server information"""
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=0x5865F2)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    await ctx.send(member.avatar.url if member.avatar else member.default_avatar.url)

# === ERROR HANDLING ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    else:
        await ctx.send("❌ An error occurred")

# === START ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        print("🚀 Starting bot...")
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
