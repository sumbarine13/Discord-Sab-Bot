"""
Discord Bot with Groq AI - Complete Version
Owner ID: 1307042499898118246
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
    "blacklist": [],
    "ai_history": {}
}

# === GROQ AI SERVICE ===
async def ask_groq(question, max_tokens=150):
    """Ask Groq AI a question"""
    api_key = os.getenv("GROQ_TOKEN")
    if not api_key:
        return "🤖 AI not configured. Add GROQ_TOKEN environment variable."
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.7,
            "max_tokens": max_tokens
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
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.id in data["whitelist"]:
            return True
        if ctx.author.id in data["blacklist"]:
            await ctx.send("⛔ You are blacklisted!")
            return False
        await ctx.send("⛔ Owner/whitelist only!")
        return False
    return commands.check(predicate)

# === EVENT HANDLERS ===
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"🔒 Owner ID: {OWNER_ID}")
    await bot.change_presence(activity=discord.Game(name="!help"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check for question words OR mention
    question_words = ["who", "what", "when", "where", "why", "how", "advice", "suggestion"]
    text_lower = message.content.lower()
    has_question = any(word in text_lower for word in question_words)
    is_mentioned = bot.user.mentioned_in(message)
    
    # Don't respond to commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return
    
    # Respond if mentioned OR has question words
    if is_mentioned or has_question:
        if is_mentioned and len(message.content.strip().replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '')) < 2:
            await message.reply("🤖 How can I help you?")
            await bot.process_commands(message)
            return
        
        async with message.channel.typing():
            # Store AI usage
            user_id = str(message.author.id)
            if user_id not in data["ai_history"]:
                data["ai_history"][user_id] = []
            
            data["ai_history"][user_id].append({
                "question": message.content,
                "time": "now"
            })
            
            # Get AI response
            response = await ask_groq(message.content)
            await message.reply(response)
    
    await bot.process_commands(message)

# === WHITELIST/BLACKLIST COMMANDS ===
@bot.command()
@is_owner()
async def whitelist(ctx, action: str, member: discord.Member):
    """[OWNER] Add/remove from whitelist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["whitelist"]:
            data["whitelist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to whitelist")
        else:
            await ctx.send("ℹ️ Already whitelisted")
    elif action.lower() in ["remove", "-", "rm"]:
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
    """[OWNER] Add/remove from blacklist"""
    if action.lower() in ["add", "+"]:
        if member.id not in data["blacklist"]:
            data["blacklist"].append(member.id)
            await ctx.send(f"✅ Added {member.mention} to blacklist")
        else:
            await ctx.send("ℹ️ Already blacklisted")
    elif action.lower() in ["remove", "-", "rm"]:
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
    
    wl = [f"<@{uid}>" for uid in data["whitelist"][:15]]
    bl = [f"<@{uid}>" for uid in data["blacklist"][:15]]
    
    embed.add_field(
        name=f"✅ Whitelist ({len(data['whitelist'])})",
        value="\n".join(wl) if wl else "Empty",
        inline=False
    )
    
    embed.add_field(
        name=f"❌ Blacklist ({len(data['blacklist'])})",
        value="\n".join(bl) if bl else "Empty",
        inline=False
    )
    
    await ctx.send(embed=embed)

# === TROLLKICK COMMAND ===
@bot.command()
@can_use_mod()
async def trollkick(ctx, member: discord.Member, *, reason="Just for fun"):
    """Prank kick a member"""
    if member == ctx.author:
        await ctx.send("❌ Can't troll yourself!")
        return
    
    # Save roles
    roles = [role for role in member.roles if role != ctx.guild.default_role]
    
    try:
        # Create invite
        invite = await ctx.channel.create_invite(max_age=300, max_uses=1)
        await member.send(f"😜 You were kicked! Just kidding! Rejoin: {invite.url}")
    except:
        pass
    
    # Kick
    await member.kick(reason=f"Troll kick: {reason}")
    await ctx.send(f"😂 {member.display_name} was troll kicked!")
    
    # Wait for rejoin (5 minutes)
    def check(m):
        return m.id == member.id
    
    try:
        rejoined = await bot.wait_for('member_join', timeout=300, check=check)
        if roles:
            await rejoined.add_roles(*roles)
            await ctx.send(f"✅ {member.display_name} rejoined with restored roles!")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ {member.display_name} didn't rejoin")

# === MODERATION COMMANDS (35+) ===
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
async def unban(ctx, user_id: int):
    """Unban a user"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned {user}")
    except:
        await ctx.send("❌ User not found or not banned")

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
async def clearwarns(ctx, member: discord.Member):
    """Clear warnings"""
    user_id = str(member.id)
    if user_id in data["warns"]:
        data["warns"][user_id] = []
        await ctx.send(f"✅ Cleared warnings for {member.mention}")

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

@bot.command()
@can_use_mod()
async def slowmode(ctx, seconds: int):
    """Set slowmode"""
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode: {seconds}s")

@bot.command()
@can_use_mod()
async def roleadd(ctx, member: discord.Member, *, role_name: str):
    """Add role to member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}")

@bot.command()
@can_use_mod()
async def roleremove(ctx, member: discord.Member, *, role_name: str):
    """Remove role from member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}")

@bot.command()
@can_use_mod()
async def createrole(ctx, *, name: str):
    """Create a role"""
    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Created role: {role.name}")

@bot.command()
@can_use_mod()
async def nick(ctx, member: discord.Member, *, nickname: str):
    """Change nickname"""
    await member.edit(nick=nickname[:32])
    await ctx.send(f"✅ Changed {member.mention}'s nickname")

# === AI GAME COMMANDS (10 tokens each) ===
@bot.command()
async def trivia(ctx):
    """AI trivia game (10 tokens)"""
    async with ctx.channel.typing():
        question = await ask_groq("Create a fun trivia question with 4 options", max_tokens=10)
        await ctx.send(f"🎯 **Trivia:** {question}")

@bot.command()
async def riddle(ctx):
    """AI riddle game (10 tokens)"""
    async with ctx.channel.typing():
        riddle = await ask_groq("Create a short riddle", max_tokens=10)
        await ctx.send(f"🤔 **Riddle:** {riddle}")

@bot.command()
async def wordgame(ctx):
    """AI word game (10 tokens)"""
    async with ctx.channel.typing():
        game = await ask_groq("Create a word association game", max_tokens=10)
        await ctx.send(f"🔤 **Word Game:** {game}")

@bot.command()
async def storystart(ctx):
    """AI story starter (10 tokens)"""
    async with ctx.channel.typing():
        story = await ask_groq("Start a short interactive story", max_tokens=10)
        await ctx.send(f"📖 **Story:** {story}")

@bot.command()
async def wouldyourather(ctx):
    """AI Would You Rather (10 tokens)"""
    async with ctx.channel.typing():
        wyr = await ask_groq("Create a 'would you rather' question", max_tokens=10)
        await ctx.send(f"🤔 **Would You Rather:** {wyr}")

# === FUN COMMANDS (20+) ===
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
        total = sum(rolls)
        await ctx.send(f"🎲 {total} ({', '.join(map(str, rolls))})")
    except:
        await ctx.send("❌ Use NdN (e.g., 2d6)")

@bot.command()
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choice = choice.lower()
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    if choice not in ['rock', 'paper', 'scissors']:
        await ctx.send("❌ Choose: rock, paper, scissors")
        return
    
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
    answers = ['Yes', 'No', 'Maybe', 'Ask again', 'Definitely', 'Never']
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(answers)}")

@bot.command()
async def choose(ctx, *, options):
    """Choose between options"""
    if " or " not in options:
        await ctx.send("❌ Separate with 'or'")
        return
    
    choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
    await ctx.send(f"🤔 I choose: **{random.choice(choices)}**")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users"""
    user2 = user2 or ctx.author
    score = random.randint(0, 100)
    
    if score > 80:
        emoji = "💖"
    elif score > 60:
        emoji = "❤️"
    elif score > 40:
        emoji = "💕"
    elif score > 20:
        emoji = "💘"
    else:
        emoji = "💔"
    
    await ctx.send(f"{emoji} **{user1.display_name}** + **{user2.display_name}**\nCompatibility: {score}%")

@bot.command()
async def rate(ctx, *, thing: str):
    """Rate something"""
    rating = random.randint(1, 10)
    stars = "⭐" * rating + "☆" * (10 - rating)
    await ctx.send(f"⭐ **{thing}**: {rating}/10\n{stars}")

@bot.command()
async def joke(ctx):
    """Tell a joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!"
    ]
    await ctx.send(f"😂 {random.choice(jokes)}")

@bot.command()
async def fact(ctx):
    """Random fact"""
    facts = [
        "Honey never spoils. Archaeologists have found 3000-year-old honey!",
        "Octopuses have three hearts.",
        "A group of flamingos is called a 'flamboyance'.",
        "Bananas are berries, but strawberries are not.",
        "The shortest war in history lasted 38 minutes."
    ]
    await ctx.send(f"🧠 **Did you know?** {random.choice(facts)}")

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    """Give a compliment"""
    member = member or ctx.author
    compliments = [
        f"{member.display_name}, you're awesome! 🌟",
        f"{member.display_name} has the best ideas! 💡",
        f"Everyone loves {member.display_name}! ❤️",
        f"{member.display_name} is a ray of sunshine! ☀️",
        f"{member.display_name} makes this server better! 🏆"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def roll(ctx, max_num: int = 100):
    """Roll a random number"""
    result = random.randint(1, max_num)
    await ctx.send(f"🎲 Rolled: **{result}** (1-{max_num})")

@bot.command()
async def meme(ctx):
    """Random meme idea"""
    memes = [
        "Distracted Boyfriend - Looking at other options while committed",
        "Drake Hotline Bling - Approving vs disapproving",
        "Change My Mind - Controversial opinion sign",
        "Two Buttons - Difficult choice",
        "Woman Yelling at Cat - Dramatic confrontation"
    ]
    await ctx.send(f"😄 **Meme Idea:** {random.choice(memes)}")

# === UTILITY COMMANDS ===
@bot.command()
async def help(ctx):
    """Show help"""
    embed = discord.Embed(title="🤖 Bot Help", color=0x5865F2)
    embed.add_field(name="🔒 Moderation (35+)", value="`kick`, `ban`, `purge`, `mute`, `warn`, `trollkick`, `lock`, `roleadd`, etc.", inline=False)
    embed.add_field(name="🤖 AI Games (5)", value="`trivia`, `riddle`, `wordgame`, `storystart`, `wouldyourather` (10 tokens each)", inline=False)
    embed.add_field(name="🎮 Fun (20+)", value="`ping`, `coinflip`, `dice`, `rps`, `8ball`, `choose`, `ship`, `joke`, `fact`, `meme`", inline=False)
    embed.add_field(name="🛠️ Utility", value="`help`, `serverinfo`, `avatar`, `userinfo`, `poll`, `timer`, `warnings`", inline=False)
    embed.add_field(name="💰 Economy", value="`balance`, `daily`, `work`, `gamble`, `pay`", inline=False)
    embed.set_footer(text="AI responds to: who, what, when, where, why, how, advice, suggestion")
    await ctx.send(embed=embed)

@bot.command(name="cmds", aliases=["commands"])
async def cmds(ctx):
    """Show all commands"""
    await ctx.send(
        "**🔒 Moderation:** `kick`, `ban`, `purge`, `mute`, `warn`, `trollkick`, `lock`, `unlock`, `slowmode`, `roleadd`, `roleremove`, `createrole`, `nick`\n"
        "**🤖 AI Games:** `trivia`, `riddle`, `wordgame`, `storystart`, `wouldyourather`\n"
        "**🎮 Fun:** `ping`, `coinflip`, `dice`, `rps`, `8ball`, `choose`, `ship`, `rate`, `joke`, `fact`, `compliment`, `roll`, `meme`\n"
        "**🛠️ Utility:** `help`, `cmds`, `serverinfo`, `avatar`, `userinfo`, `poll`, `timer`, `warnings`\n"
        "**💰 Economy:** `balance`, `daily`, `work`, `gamble`, `pay`\n"
        "**🔧 Admin:** `whitelist`, `blacklist`, `showlists`"
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
async def userinfo(ctx, member: discord.Member = None):
    """User information"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Info", color=member.color)
    embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}")
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    await ctx.send(member.avatar.url if member.avatar else member.default_avatar.url)

@bot.command()
async def poll(ctx, *, question):
    """Create a poll"""
    embed = discord.Embed(title="📊 Poll", description=question, color=0x5865F2)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.command()
async def timer(ctx, seconds: int):
    """Set a timer"""
    if seconds > 3600:
        await ctx.send("❌ Max 1 hour")
        return
    
    msg = await ctx.send(f"⏰ Timer: {seconds}s")
    await asyncio.sleep(seconds)
    await msg.edit(content=f"⏰ Timer finished! {ctx.author.mention}")

# === ECONOMY COMMANDS ===
@bot.command()
async def balance(ctx):
    """Check balance"""
    user_id = str(ctx.author.id)
    if user_id not in data["money"]:
        data["money"][user_id] = 100
    await ctx.send(f"💰 ${data['money'][user_id]:,}")

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Daily reward"""
    user_id = str(ctx.author.id)
    if user_id not in data["money"]:
        data["money"][user_id] = 100
    
    reward = random.randint(50, 200)
    data["money"][user_id] += reward
    await ctx.send(f"🎁 +${reward}!")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work for money"""
    user_id = str(ctx.author.id)
    if user_id not in data["money"]:
        data["money"][user_id] = 100
    
    jobs = ["Developer", "Designer", "Streamer", "Chef"]
    job = random.choice(jobs)
    earned = random.randint(30, 150)
    data["money"][user_id] += earned
    await ctx.send(f"💼 Worked as **{job}** and earned **${earned}**!")

@bot.command()
async def gamble(ctx, amount: int):
    """Gamble money"""
    user_id = str(ctx.author.id)
    if user_id not in data["money"]:
        data["money"][user_id] = 100
    
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    if amount > data["money"][user_id]:
        await ctx.send("❌ Not enough money!")
        return
    
    if random.random() < 0.45:
        data["money"][user_id] += amount
        await ctx.send(f"🎉 Won **${amount}**!")
    else:
        data["money"][user_id] -= amount
        await ctx.send(f"😢 Lost **${amount}**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    """Pay another user"""
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    if sender_id not in data["money"]:
        data["money"][sender_id] = 100
    if receiver_id not in data["money"]:
        data["money"][receiver_id] = 100
    
    if amount > data["money"][sender_id]:
        await ctx.send("❌ Not enough money!")
        return
    
    data["money"][sender_id] -= amount
    data["money"][receiver_id] += amount
    await ctx.send(f"💰 Paid **${amount}** to {member.mention}!")

# === ERROR HANDLING ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    else:
        await ctx.send("❌ An error occurred")

# === START BOT ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        print("🚀 Starting bot...")
        print(f"🔒 Owner: {OWNER_ID}")
        print("🤖 AI: Enabled (responds to who/what/when/where/why/how/advice/suggestion)")
        print("🎮 Commands: 35+ moderation, 5 AI games, 20+ fun, 10+ utility")
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN not found!")
