"""
Discord Bot - Owner Only Moderation
"""
import os
import discord
from discord.ext import commands
import random
import asyncio

# Owner ID
OWNER_ID = 1307042499898118246

# Bot setup - NO voice features
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Store data
data = {"economy": {}, "warnings": {}}

# === OWNER CHECK ===
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

# === GLOBAL CHECK ===
@bot.check
async def global_check(ctx):
    # Fun/utility commands that EVERYONE can use
    public_commands = [
        'ping', 'help', 'cmds', 'serverinfo', 'avatar',
        'coinflip', 'dice', 'rps', 'eightball', 'choose', 'ship',
        'balance', 'daily', 'work', 'gamble', 'pay'
    ]
    
    if ctx.command.name in public_commands:
        return True
    
    # Moderation commands (OWNER ONLY)
    owner_commands = [
        'kick', 'ban', 'purge', 'mute', 'unmute', 
        'warn', 'warnings', 'trollkick'
    ]
    
    if ctx.command.name in owner_commands:
        if ctx.author.id != OWNER_ID:
            await ctx.send(f"⛔ **Owner Only** - Only <@{OWNER_ID}> can use this command!")
            return False
        return True
    
    return True

# === BOT EVENTS ===
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f"🔒 Owner: {OWNER_ID}")

# === MODERATION COMMANDS (OWNER ONLY) ===
@bot.command()
@is_owner()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """[OWNER] Kick a member"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 **Owner Action:** Kicked {member}")

@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """[OWNER] Ban a member"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **Owner Action:** Banned {member}")

@bot.command()
@is_owner()
async def purge(ctx, amount: int = 10):
    """[OWNER] Delete messages"""
    if amount > 100:
        await ctx.send("❌ Max 100 messages")
        return
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 **Owner Action:** Deleted {len(deleted)} messages")
    await asyncio.sleep(2)
    await msg.delete()

@bot.command()
@is_owner()
async def mute(ctx, member: discord.Member):
    """[OWNER] Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await member.add_roles(mute_role)
    await ctx.send(f"🔇 **Owner Action:** Muted {member}")

@bot.command()
@is_owner()
async def unmute(ctx, member: discord.Member):
    """[OWNER] Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 **Owner Action:** Unmuted {member}")

@bot.command()
@is_owner()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    """[OWNER] Warn a member"""
    user_id = str(member.id)
    if user_id not in data["warnings"]:
        data["warnings"][user_id] = []
    
    data["warnings"][user_id].append({
        "reason": reason,
        "by": ctx.author.id,
        "time": "now"
    })
    
    await ctx.send(f"⚠️ **Owner Action:** Warned {member}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["warnings"] or not data["warnings"][user_id]:
        await ctx.send(f"✅ {member} has no warnings")
        return
    
    warn_list = "\n".join([f"• {w['reason']}" for w in data["warnings"][user_id][:10]])
    await ctx.send(f"📋 Warnings for {member}:\n{warn_list}")

# === TROLLKICK COMMAND (OWNER ONLY) ===
@bot.command()
@is_owner()
async def trollkick(ctx, member: discord.Member):
    """[OWNER] Prank kick a member"""
    if member.id == ctx.author.id:
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
    
    # Kick them
    await member.kick(reason="Troll kick by owner")
    await ctx.send(f"😂 **Owner Action:** {member} was troll kicked!")
    
    # Wait for rejoin (5 minutes)
    def check(m):
        return m.id == member.id
    
    try:
        rejoined = await bot.wait_for('member_join', timeout=300, check=check)
        if roles:
            await rejoined.add_roles(*roles)
            await ctx.send(f"✅ {member} rejoined with roles restored!")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ {member} didn't rejoin in time")

# === FUN COMMANDS (PUBLIC) ===
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
        await ctx.send("❌ Use NdN format (e.g., 2d6)")

@bot.command()
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choice = choice.lower()
    if choice not in ['rock', 'paper', 'scissors']:
        await ctx.send("❌ Choose: rock, paper, or scissors")
        return
    
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
    answers = ['Yes', 'No', 'Maybe', 'Ask again', 'Definitely', 'Never']
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(answers)}")

@bot.command()
async def choose(ctx, *, options):
    """Choose between options"""
    if " or " not in options:
        await ctx.send("❌ Separate options with 'or'")
        return
    
    choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
    if len(choices) < 2:
        await ctx.send("❌ Need at least 2 options")
        return
    
    await ctx.send(f"🤔 I choose: **{random.choice(choices)}**")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users"""
    user2 = user2 or ctx.author
    score = random.randint(0, 100)
    
    # Pick emoji based on score
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

# === UTILITY COMMANDS (PUBLIC) ===
@bot.command(name="cmds", aliases=["cmd", "commands"])
async def cmds(ctx):
    """Show all commands"""
    embed = discord.Embed(
        title="📚 All Commands",
        description=f"**Owner:** <@{OWNER_ID}>\nModeration commands are owner-only",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔒 Owner Commands",
        value="`kick`, `ban`, `purge`, `mute`, `unmute`, `warn`, `trollkick`",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Fun Commands",
        value="`ping`, `coinflip`, `dice`, `rps`, `8ball`, `choose`, `ship`",
        inline=False
    )
    
    embed.add_field(
        name="💰 Economy",
        value="`balance`, `daily`, `work`, `gamble`, `pay`",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Utility",
        value="`help`, `cmds`, `serverinfo`, `avatar`",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx, command=None):
    """Show help"""
    if command:
        await ctx.send(f"Use `!cmds` to see all commands or `!help` for general help")
    else:
        await ctx.send(
            "**🤖 Bot Help**\n"
            f"• Owner: <@{OWNER_ID}>\n"
            "• Moderation commands are owner-only\n"
            "• Fun commands are public for everyone\n\n"
            "**Commands:**\n"
            "• `!cmds` - See all commands\n"
            "• `!help` - This message\n\n"
            "**Popular:**\n"
            "• `!ping` `!coinflip` `!daily` `!balance` `!ship`"
        )

@bot.command()
async def serverinfo(ctx):
    """Server information"""
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=0x5865F2)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    await ctx.send(member.avatar.url if member.avatar else member.default_avatar.url)

# === ECONOMY COMMANDS (PUBLIC) ===
@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Check balance"""
    member = member or ctx.author
    user_id = str(member.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = 100
    await ctx.send(f"💰 **{member.display_name}:** ${data['economy'][user_id]:,}")

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Daily reward"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = 100
    reward = random.randint(50, 200)
    data["economy"][user_id] += reward
    await ctx.send(f"🎁 +${reward}! New balance: ${data['economy'][user_id]:,}")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work for money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = 100
    jobs = ["Developer", "Designer", "Streamer", "Chef"]
    job = random.choice(jobs)
    earned = random.randint(30, 150)
    data["economy"][user_id] += earned
    await ctx.send(f"💼 Worked as **{job}** and earned **${earned}**!")

@bot.command()
async def gamble(ctx, amount: int):
    """Gamble money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = 100
    
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    if amount > data["economy"][user_id]:
        await ctx.send("❌ Not enough money!")
        return
    
    if random.random() < 0.45:
        data["economy"][user_id] += amount
        await ctx.send(f"🎉 Won **${amount}**!")
    else:
        data["economy"][user_id] -= amount
        await ctx.send(f"😢 Lost **${amount}**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    """Pay another user"""
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    if member == ctx.author:
        await ctx.send("❌ Can't pay yourself")
        return
    
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    if sender_id not in data["economy"]:
        data["economy"][sender_id] = 100
    if receiver_id not in data["economy"]:
        data["economy"][receiver_id] = 100
    
    if amount > data["economy"][sender_id]:
        await ctx.send("❌ Not enough money!")
        return
    
    data["economy"][sender_id] -= amount
    data["economy"][receiver_id] += amount
    
    await ctx.send(f"💰 Paid **${amount}** to {member.mention}!")

# === ERROR HANDLING ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    elif isinstance(error, commands.CheckFailure):
        # Already handled
        pass
    else:
        await ctx.send("❌ An error occurred")

# === START BOT ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found!")
    else:
        print("🚀 Starting bot...")
        print(f"🔒 Owner ID: {OWNER_ID}")
        print("🎮 Fun commands: Public")
        print("🔨 Mod commands: Owner-only")
        bot.run(token)
