"""
Discord Bot - Owner Restricted Moderation
Only owner (1307042499898118246) can use mod commands
Everyone can use fun commands
"""
import os
import discord
from discord.ext import commands
import random
import asyncio
import datetime
import json

# Disable voice completely
discord.voice_client.VoiceClient = None

# Owner ID
OWNER_ID = 1307042499898118246

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Store data
data = {"economy": {}, "warnings": {}}

# === OWNER CHECK DECORATOR ===
def is_owner():
    """Check if user is the owner"""
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_mod_command(ctx):
    """Check if command is a moderation command"""
    mod_commands = ['kick', 'ban', 'purge', 'mute', 'unmute', 'warn', 'warnings', 'trollkick']
    return ctx.command.name in mod_commands

# === GLOBAL CHECK ===
@bot.check
async def global_check(ctx):
    """Global check for all commands"""
    # Allow all fun and utility commands for everyone
    fun_commands = ['ping', 'help', 'cmds', 'cmd', 'commands', 'cmdinfo', 'serverinfo', 'avatar', 
                   'coinflip', 'dice', 'rps', 'eightball', 'choose', 'ship',
                   'balance', 'daily', 'work', 'gamble', 'pay']
    
    # If it's a fun/utility command, allow everyone
    if ctx.command.name in fun_commands:
        return True
    
    # If it's a mod command, check if owner
    if is_mod_command(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send("⛔ **Owner Only** - Moderation commands are restricted to the bot owner.")
            return False
        return True
    
    # Allow all other commands (default)
    return True

# === SIMPLE AI RESPONSES ===
async def ai_response(question):
    """Simple AI responses without external API"""
    q = question.lower()
    
    responses = {
        "who": ["I'm a Discord bot!", "I'm here to help!", "Just a friendly bot!"],
        "what": ["That's a great question!", "I'm not sure, but I'm learning!", "Interesting question!"],
        "when": ["Soon!", "Right now!", "In the future!"],
        "where": ["Everywhere!", "Here in Discord!", "In the cloud!"],
        "why": ["Because it's fun!", "Why not?", "Good question!"],
        "how": ["Very carefully!", "With code!", "Step by step!"],
        "advice": ["Take breaks!", "Stay hydrated!", "Be kind to others!"],
        "suggestion": ["Try !help", "Play !trivia", "Use !8ball"],
    }
    
    for key in responses:
        if key in q:
            return random.choice(responses[key])
    
    return random.choice(["🤖 Interesting!", "💭 Hmm...", "🌟 Good question!", "🎯 Not sure!"])

# === BASIC COMMANDS ===
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.change_presence(activity=discord.Game(name="!help"))
    print(f"🔒 Moderation commands restricted to owner ID: {OWNER_ID}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI response for mentions
    if bot.user.mentioned_in(message) and not message.content.startswith("!"):
        response = await ai_response(message.content)
        await message.reply(response)
    
    await bot.process_commands(message)

# === OWNER-ONLY MODERATION COMMANDS ===
@bot.command()
@is_owner()
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    """[OWNER] Kick a member"""
    await member.kick(reason=f"By {ctx.author}: {reason}")
    await ctx.send(f"👢 **Owner Action:** Kicked {member} | Reason: {reason}")

@bot.command()
@is_owner()
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    """[OWNER] Ban a member"""
    await member.ban(reason=f"By {ctx.author}: {reason}")
    await ctx.send(f"🔨 **Owner Action:** Banned {member} | Reason: {reason}")

@bot.command()
@is_owner()
async def purge(ctx, amount: int = 10):
    """[OWNER] Delete messages"""
    if amount > 100:
        await ctx.send("❌ Max 100 messages at once")
        return
    
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 **Owner Action:** Deleted {amount} messages")
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
    if mute_role in member.roles:
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
        "time": str(datetime.datetime.now())
    })
    
    await ctx.send(f"⚠️ **Owner Action:** Warned {member} | Reason: {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["warnings"] or not data["warnings"][user_id]:
        await ctx.send(f"✅ {member} has no warnings")
        return
    
    embed = discord.Embed(title=f"Warnings for {member}", color=0xff9900)
    for i, warn in enumerate(data["warnings"][user_id][-10:], 1):
        embed.add_field(
            name=f"Warning #{i}",
            value=f"Reason: {warn['reason']}\nBy: <@{warn['by']}>",
            inline=False
        )
    
    await ctx.send(embed=embed)

# === TROLLKICK COMMAND (OWNER ONLY) ===
@bot.command()
@is_owner()
async def trollkick(ctx, member: discord.Member, *, reason="Trolling around"):
    """[OWNER] Kick and invite back as a prank"""
    # Check if user can kick the member
    if member == ctx.author:
        await ctx.send("❌ You can't troll kick yourself!")
        return
    
    if member.top_role >= ctx.author.top_role:
        await ctx.send("❌ You cannot troll someone with equal/higher role.")
        return
    
    # Save original roles (excluding @everyone)
    original_roles = [role for role in member.roles if role != ctx.guild.default_role]
    
    try:
        # Create a one-time invite
        invite = await ctx.channel.create_invite(max_age=300, max_uses=1, reason="Troll kick invite")
        
        # Send DM with the prank
        embed = discord.Embed(
            title=f"😜 You've been kicked from {ctx.guild.name}!",
            description=f"**JUST KIDDING!**\n\nRejoin with this link:\n{invite.url}\n\nThis invite expires in 5 minutes!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="This is a prank! Rejoin for a surprise!")
        
        await member.send(embed=embed)
    except:
        pass  # Can't DM, but continue with the prank
    
    # Actually kick them
    await member.kick(reason=f"Troll kick by {ctx.author}: {reason}")
    await ctx.send(f"😂 **Owner Action:** {member.display_name} has been troll kicked! They should check their DMs!")
    
    # Wait for them to rejoin (5 minutes max)
    def check(m):
        return m.id == member.id and m.guild == ctx.guild
    
    try:
        await ctx.send(f"⏰ Waiting for {member.display_name} to rejoin... (5 minutes)")
        rejoined_member = await bot.wait_for('member_join', timeout=300.0, check=check)
        
        # Give them back their roles
        if original_roles:
            try:
                await rejoined_member.add_roles(*original_roles)
                await ctx.send(f"✅ {rejoined_member.display_name} rejoined and got their roles back! 🎉")
            except:
                await ctx.send(f"✅ {rejoined_member.display_name} rejoined! (Failed to restore some roles)")
        
        # Give them a special "Trolled" role if it exists
        trolled_role = discord.utils.get(ctx.guild.roles, name="Trolled")
        if not trolled_role:
            try:
                trolled_role = await ctx.guild.create_role(
                    name="Trolled",
                    color=discord.Color.orange(),
                    reason="For troll kick victims"
                )
            except:
                trolled_role = None
        
        if trolled_role:
            try:
                await rejoined_member.add_roles(trolled_role)
                # Remove after 1 hour
                await asyncio.sleep(3600)
                if trolled_role in rejoined_member.roles:
                    await rejoined_member.remove_roles(trolled_role)
            except:
                pass
        
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ {member.display_name} didn't rejoin within 5 minutes. The joke's on them!")

# === PUBLIC FUN COMMANDS (EVERYONE CAN USE) ===
@bot.command()
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def coinflip(ctx):
    """Flip a coin"""
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

@bot.command()
async def dice(ctx, dice: str = "1d6"):
    """Roll dice"""
    try:
        num, sides = map(int, dice.split('d'))
        if num > 20:
            await ctx.send("❌ Max 20 dice")
            return
        
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls)
        
        await ctx.send(f"🎲 Rolled: {', '.join(map(str, rolls))} | Total: {total}")
    except:
        await ctx.send("❌ Format: NdN (e.g., 2d6)")

@bot.command()
async def rps(ctx, choice: str):
    """Rock Paper Scissors"""
    choices = ["rock", "paper", "scissors"]
    choice = choice.lower()
    
    if choice not in choices:
        await ctx.send("❌ Choose: rock, paper, or scissors")
        return
    
    bot_choice = random.choice(choices)
    
    if choice == bot_choice:
        result = "Tie! 🤝"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(f"**You:** {choice}\n**Bot:** {bot_choice}\n\n**{result}**")

@bot.command()
async def eightball(ctx, *, question):
    """Magic 8-ball"""
    responses = [
        "Yes", "No", "Maybe", "Ask again",
        "Definitely", "I doubt it", "For sure!",
        "Not likely", "Absolutely!", "Never"
    ]
    
    await ctx.send(f"🎱 **{question}**\nAnswer: {random.choice(responses)}")

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
    
    emoji = "💔"
    if score > 80:
        emoji = "💖"
    elif score > 60:
        emoji = "❤️"
    elif score > 40:
        emoji = "💕"
    elif score > 20:
        emoji = "💘"
    
    await ctx.send(f"{emoji} **{user1.display_name}** + **{user2.display_name}**\nCompatibility: {score}%")

# === PUBLIC UTILITY COMMANDS ===
@bot.command(name="cmds", aliases=["cmd", "commands"])
async def cmds(ctx, category: str = None):
    """Show all commands"""
    
    # Define command categories
    command_categories = {
        "🔨 MODERATION": {
            "commands": ["kick", "ban", "purge", "mute", "unmute", "warn", "warnings", "trollkick"],
            "description": "**Owner Only** - Server management commands",
            "emoji": "🔒"
        },
        "🎮 FUN": {
            "commands": ["ping", "coinflip", "dice", "rps", "eightball", "choose", "ship"],
            "description": "**Public** - Games and entertainment",
            "emoji": "🎉"
        },
        "💰 ECONOMY": {
            "commands": ["balance", "daily", "work", "gamble", "pay"],
            "description": "**Public** - Virtual currency system",
            "emoji": "💰"
        },
        "🛠️ UTILITY": {
            "commands": ["help", "cmds", "cmdinfo", "serverinfo", "avatar"],
            "description": "**Public** - Useful tools and info",
            "emoji": "🔧"
        }
    }
    
    if category:
        # Show specific category
        category = category.upper()
        if category in ["MODERATION", "MOD"]:
            cat_key = "🔨 MODERATION"
        elif category in ["FUN", "GAMES"]:
            cat_key = "🎮 FUN"
        elif category in ["ECONOMY", "MONEY"]:
            cat_key = "💰 ECONOMY"
        elif category in ["UTILITY", "UTIL", "TOOLS"]:
            cat_key = "🛠️ UTILITY"
        else:
            cat_key = None
        
        if cat_key and cat_key in command_categories:
            embed = discord.Embed(
                title=f"{cat_key} Commands",
                description=command_categories[cat_key]["description"],
                color=discord.Color.blue()
            )
            
            # Get command details
            command_list = []
            for cmd_name in command_categories[cat_key]["commands"]:
                cmd = bot.get_command(cmd_name)
                if cmd:
                    prefix = "🔒 " if cat_key == "🔨 MODERATION" else ""
                    command_list.append(f"• `!{cmd_name}` - {cmd.help or 'No description'}")
            
            embed.add_field(
                name=f"Commands ({len(command_categories[cat_key]['commands'])})",
                value="\n".join(command_list),
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Category not found. Available: `moderation`, `fun`, `economy`, `utility`")
        return
    
    # Show all categories
    embed = discord.Embed(
        title="📚 All Commands",
        description=f"**Owner ID:** `{OWNER_ID}`\nModeration commands are **owner-only**\nFun commands are **public**\n",
        color=discord.Color.green()
    )
    
    for category_name, category_info in command_categories.items():
        cmd_names = [f"`!{cmd}`" for cmd in category_info["commands"]]
        embed.add_field(
            name=f"{category_name} ({len(category_info['commands'])})",
            value=f"{category_info['emoji']} {category_info['description']}\n{', '.join(cmd_names)}",
            inline=False
        )
    
    embed.set_footer(text="🔒 = Owner Only | 🎉 = Public | Use !help <command> for details")
    await ctx.send(embed=embed)

@bot.command(name="cmdinfo")
async def cmdinfo(ctx, command_name: str = None):
    """Get detailed info about a specific command"""
    if not command_name:
        await ctx.send("❌ Usage: `!cmdinfo <command>`\nExample: `!cmdinfo kick`")
        return
    
    cmd = bot.get_command(command_name.lower())
    if not cmd:
        # Try to find similar commands
        all_commands = [c.name for c in bot.commands]
        similar = [c for c in all_commands if command_name in c or c.startswith(command_name[:3])]
        
        if similar:
            await ctx.send(f"❌ Command `{command_name}` not found. Did you mean: {', '.join(f'`!{c}`' for c in similar[:3])}?")
        else:
            await ctx.send(f"❌ Command `{command_name}` not found. Use `!cmds` to see all commands.")
        return
    
    embed = discord.Embed(
        title=f"Command: !{cmd.name}",
        color=discord.Color.blue()
    )
    
    # Check if it's an owner-only command
    is_owner_cmd = cmd.name in ['kick', 'ban', 'purge', 'mute', 'unmute', 'warn', 'trollkick']
    
    if is_owner_cmd:
        embed.add_field(name="🔒 Access", value="**Owner Only** - Restricted to bot owner", inline=False)
    else:
        embed.add_field(name="🎉 Access", value="**Public** - Everyone can use", inline=False)
    
    embed.add_field(name="Description", value=cmd.help or "No description", inline=False)
    
    if cmd.aliases:
        embed.add_field(name="Aliases", value=", ".join(f"`!{alias}`" for alias in cmd.aliases), inline=True)
    
    # Get signature if available
    if hasattr(cmd, 'signature') and cmd.signature:
        embed.add_field(name="Usage", value=f"`!{cmd.name} {cmd.signature}`", inline=False)
    else:
        embed.add_field(name="Usage", value=f"`!{cmd.name}`", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx, command=None):
    """Show help - use !cmds for all commands"""
    if command:
        # Redirect to cmdinfo for detailed command help
        await cmdinfo(ctx, command)
    else:
        # Show quick help message
        embed = discord.Embed(
            title="🤖 Bot Help",
            description=f"**Owner:** <@{OWNER_ID}>\nModeration commands are restricted to the owner only.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📚 All Commands",
            value="`!cmds` - View all commands by category\n`!cmdinfo <command>` - Get detailed info",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Popular Fun Commands",
            value="`!ping` `!coinflip` `!dice` `!rps` `!8ball` `!ship`",
            inline=False
        )
        
        embed.add_field(
            name="💰 Economy System",
            value="`!balance` `!daily` `!work` `!gamble` `!pay`",
            inline=False
        )
        
        embed.add_field(
            name="🔒 Owner Commands",
            value="`!kick` `!ban` `!purge` `!mute` `!trollkick`",
            inline=False
        )
        
        embed.set_footer(text="Bot by owner • Moderation is owner-only")
        await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Server information"""
    guild = ctx.guild
    
    embed = discord.Embed(title=guild.name, color=0x5865F2)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    await ctx.send(member.avatar.url if member.avatar else member.default_avatar.url)

# === PUBLIC ECONOMY COMMANDS ===
@bot.command()
async def balance(ctx, member: discord.Member = None):
    """Check balance"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100}
    
    await ctx.send(f"💰 **{member.display_name}'s balance:** ${data['economy'][user_id]['balance']:,}")

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Daily reward"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100}
    
    reward = random.randint(50, 200)
    data["economy"][user_id]["balance"] += reward
    
    await ctx.send(f"🎁 Daily reward: **${reward}**!")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work for money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100}
    
    jobs = ["Developer", "Designer", "Streamer", "Chef"]
    job = random.choice(jobs)
    earned = random.randint(30, 150)
    data["economy"][user_id]["balance"] += earned
    
    await ctx.send(f"💼 Worked as **{job}** and earned **${earned}**!")

@bot.command()
async def gamble(ctx, amount: int):
    """Gamble money"""
    user_id = str(ctx.author.id)
    if user_id not in data["economy"]:
        data["economy"][user_id] = {"balance": 100}
    
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    if amount > data["economy"][user_id]["balance"]:
        await ctx.send("❌ Not enough money!")
        return
    
    if random.random() < 0.45:
        data["economy"][user_id]["balance"] += amount
        await ctx.send(f"🎉 Won **${amount}**!")
    else:
        data["economy"][user_id]["balance"] -= amount
        await ctx.send(f"😢 Lost **${amount}**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    """Pay another user"""
    if amount < 1:
        await ctx.send("❌ Minimum $1")
        return
    
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    if sender_id not in data["economy"]:
        data["economy"][sender_id] = {"balance": 100}
    if receiver_id not in data["economy"]:
        data["economy"][receiver_id] = {"balance": 100}
    
    if amount > data["economy"][sender_id]["balance"]:
        await ctx.send("❌ Not enough money!")
        return
    
    data["economy"][sender_id]["balance"] -= amount
    data["economy"][receiver_id]["balance"] += amount
    
    await ctx.send(f"💰 Paid **${amount}** to {member.mention}!")

# === OWNER INFO COMMAND ===
@bot.command()
@is_owner()
async def ownerinfo(ctx):
    """[OWNER] Show owner information"""
    embed = discord.Embed(
        title="🔑 Owner Information",
        description=f"You are the bot owner!",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Your ID", value=f"`{ctx.author.id}`", inline=True)
    embed.add_field(name="Bot ID", value=f"`{bot.user.id}`", inline=True)
    embed.add_field(name="Server Count", value=len(bot.guilds), inline=True)
    
    mod_commands = [f"`!{cmd.name}`" for cmd in bot.commands if cmd.name in ['kick', 'ban', 'purge', 'mute', 'unmute', 'warn', 'trollkick']]
    embed.add_field(name="Your Commands", value=" ".join(mod_commands), inline=False)
    
    embed.set_footer(text="Only you can use moderation commands")
    await ctx.send(embed=embed)

# === ERROR HANDLING ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Cooldown: {error.retry_after:.1f}s")
    elif isinstance(error, commands.CheckFailure):
        # Already handled by global check
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
