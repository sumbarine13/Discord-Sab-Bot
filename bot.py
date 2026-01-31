import os
import discord
from discord.ext import commands
import random
import asyncio
import aiohttp
import threading
import time
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ========== CONFIGURATION ==========
TOKEN = os.environ.get("DISCORD_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
PREFIX = "!"
OWNER_IDS = [1307042499898118246]  # Replace with your Discord ID
BOT_START_TIME = time.time()

# ========== HTTP SERVER FOR RENDER ==========
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("index.html", "r", encoding="utf-8") as f:
                html = f.read()
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status_data = {
                "status": "online",
                "uptime": int(time.time() - BOT_START_TIME),
                "guilds": len(bot.guilds) if bot.is_ready() else 0,
                "commands": len(bot.commands)
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        pass

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), BotHTTPServer)
    server.serve_forever()

# ========== DISCORD BOT ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ========== DATA STORAGE ==========
bot_data = {
    "warnings": {},
    "reminders": [],
    "user_stats": {},
    "game_scores": {},
    "server_configs": {}
}

# ========== HELPER FUNCTIONS ==========
def create_embed(title, description, color=0x5865F2):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Requested by")
    return embed

def is_owner():
    async def predicate(ctx):
        return ctx.author.id in OWNER_IDS
    return commands.check(predicate)

# ========== EVENT HANDLERS ==========
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    print(f"Connected to {len(bot.guilds)} guilds")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=create_embed("❌ Missing Permissions", "You don't have permission to use this command!", 0xFF0000))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=create_embed("⏰ Cooldown", f"Please wait {error.retry_after:.1f} seconds!", 0xFFA500))
    else:
        await ctx.send(embed=create_embed("❌ Error", f"An error occurred: {str(error)}", 0xFF0000))

# ========== UTILITY COMMANDS (10) ==========
@bot.command()
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(embed=create_embed("🏓 Pong!", f"Latency: {latency}ms"))

@bot.command()
async def help(ctx):
    """Show help menu"""
    embed = create_embed("🤖 Bot Help", "Prefix: `!`")
    
    categories = {
        "🔧 Utility": ["ping", "help", "uptime", "invite", "userinfo", "serverinfo", "avatar", "embed", "say", "remind"],
        "🎮 Fun": ["meme", "joke", "coinflip", "dice", "8ball", "rate", "choose", "reverse", "mock", "ascii", "compliment", "roast", "ship", "hack", "cat"],
        "🎲 Games": ["rps", "guess", "math", "trivia", "slots", "battle", "tictactoe", "count", "wordchain", "leaderboard"],
        "🛡️ Moderation": ["kick", "ban", "unban", "timeout", "untimeout", "purge", "slowmode", "lock", "unlock", "warn", "warnings", "clearwarns", "nick", "role", "mute"],
        "⚙️ Admin": ["setprefix", "setstatus", "setactivity", "reload", "shutdown", "restart", "announce", "poll", "giveaway", "config"],
        "🎭 Prank": ["trollkick", "fakeban", "fakecrash", "ghostping", "rickroll"]
    }
    
    for category, commands_list in categories.items():
        embed.add_field(name=category, value="`" + "`, `".join(commands_list) + "`", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def uptime(ctx):
    """Check bot uptime"""
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(embed=create_embed("⏰ Uptime", f"{hours}h {minutes}m {seconds}s"))

@bot.command()
async def invite(ctx):
    """Get bot invite link"""
    await ctx.send(embed=create_embed("🔗 Invite", f"[Click here to invite me!](https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8)"))

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    """Get user information"""
    member = member or ctx.author
    embed = create_embed(f"👤 {member.display_name}", "")
    embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Roles", value=len(member.roles) - 1, inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    """Get server information"""
    guild = ctx.guild
    embed = create_embed(f"🏰 {guild.name}", "")
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Get user's avatar"""
    member = member or ctx.author
    await ctx.send(embed=create_embed(f"🖼️ {member.display_name}'s Avatar", f"[Download]({member.avatar.url if member.avatar else member.default_avatar.url})").set_image(url=member.avatar.url if member.avatar else member.default_avatar.url))

@bot.command()
async def embed(ctx, *, text):
    """Create an embed with your text"""
    await ctx.send(embed=create_embed("📝 Embed", text))

@bot.command()
async def say(ctx, *, message):
    """Make the bot say something"""
    await ctx.send(message)

@bot.command()
async def remind(ctx, time_in_minutes: int, *, reminder):
    """Set a reminder"""
    if time_in_minutes > 1440:
        await ctx.send(embed=create_embed("❌ Error", "Maximum reminder time is 24 hours (1440 minutes)", 0xFF0000))
        return
    
    bot_data["reminders"].append({
        "user": ctx.author.id,
        "channel": ctx.channel.id,
        "reminder": reminder,
        "time": time.time() + (time_in_minutes * 60)
    })
    
    await ctx.send(embed=create_embed("⏰ Reminder Set", f"I'll remind you in {time_in_minutes} minute(s) about: {reminder}"))

# ========== FUN COMMANDS (15) ==========
@bot.command()
async def meme(ctx):
    """Get a random meme"""
    memes = [
        "When you finally fix the bug at 3 AM",
        "Me: I'll start my project tomorrow. Also me: *proceeds to procrastinate*",
        "Debugging be like: It works on my machine!",
        "When the bot works perfectly in testing but breaks in production",
        "Git commit -m 'Fixed stuff'"
    ]
    await ctx.send(embed=create_embed("😂 Meme", random.choice(memes)))

@bot.command()
async def joke(ctx):
    """Get a random joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What do you call a fake noodle? An impasta!",
        "Why don't eggs tell jokes? They'd crack each other up!"
    ]
    await ctx.send(embed=create_embed("😂 Joke", random.choice(jokes)))

@bot.command()
async def coinflip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(embed=create_embed("🪙 Coin Flip", f"The coin landed on **{result}**!"))

@bot.command()
async def dice(ctx, sides: int = 6):
    """Roll a dice (default 6 sides)"""
    if sides < 2 or sides > 100:
        await ctx.send(embed=create_embed("❌ Error", "Dice must have between 2 and 100 sides", 0xFF0000))
        return
    
    result = random.randint(1, sides)
    await ctx.send(embed=create_embed("🎲 Dice Roll", f"You rolled a **{result}** on a {sides}-sided dice!"))

@bot.command()
async def eightball(ctx, *, question):
    """Ask the magic 8-ball"""
    responses = [
        "It is certain", "It is decidedly so", "Without a doubt", "Yes definitely",
        "You may rely on it", "As I see it, yes", "Most likely", "Outlook good",
        "Yes", "Signs point to yes", "Reply hazy try again", "Ask again later",
        "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
        "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good",
        "Very doubtful"
    ]
    await ctx.send(embed=create_embed("🎱 Magic 8-Ball", f"**Q:** {question}\n**A:** {random.choice(responses)}"))

@bot.command()
async def rate(ctx, *, thing):
    """Rate something out of 10"""
    rating = random.randint(1, 10)
    stars = "⭐" * rating + "☆" * (10 - rating)
    await ctx.send(embed=create_embed("⭐ Rating", f"I rate **{thing}** a **{rating}/10**!\n{stars}"))

@bot.command()
async def choose(ctx, *, options):
    """Choose between options separated by 'or'"""
    if " or " not in options:
        await ctx.send(embed=create_embed("❌ Error", "Please separate options with 'or' (e.g., `!choose pizza or burgers`)", 0xFF0000))
        return
    
    choices = [opt.strip() for opt in options.split(" or ") if opt.strip()]
    if len(choices) < 2:
        await ctx.send(embed=create_embed("❌ Error", "Please provide at least 2 options", 0xFF0000))
        return
    
    choice = random.choice(choices)
    await ctx.send(embed=create_embed("🤔 Choose", f"I choose: **{choice}**!"))

@bot.command()
async def reverse(ctx, *, text):
    """Reverse your text"""
    reversed_text = text[::-1]
    await ctx.send(embed=create_embed("🔁 Reverse", f"Original: {text}\nReversed: {reversed_text}"))

@bot.command()
async def mock(ctx, *, text):
    """MoCk YoUr TeXt LiKe ThIs"""
    mocked = "".join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
    await ctx.send(embed=create_embed("🤪 Mock", mocked))

@bot.command()
async def ascii(ctx, *, text):
    """Convert text to ASCII art (simple)"""
    if len(text) > 10:
        await ctx.send(embed=create_embed("❌ Error", "Text must be 10 characters or less", 0xFF0000))
        return
    
    ascii_art = ""
    for char in text.upper():
        if char.isalpha():
            ascii_art += f":regional_indicator_{char.lower()}: "
        elif char.isdigit():
            ascii_art += f":{['zero','one','two','three','four','five','six','seven','eight','nine'][int(char)]}: "
        elif char == " ":
            ascii_art += "   "
        else:
            ascii_art += char + " "
    
    await ctx.send(ascii_art)

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    """Give someone a compliment"""
    member = member or ctx.author
    compliments = [
        f"{member.display_name}, you're amazing! ✨",
        f"{member.display_name} has the best smile! 😊",
        f"Everyone loves {member.display_name}! ❤️",
        f"{member.display_name} is a ray of sunshine! ☀️",
        f"{member.display_name} makes this server better! 🏆"
    ]
    await ctx.send(embed=create_embed("💖 Compliment", random.choice(compliments)))

@bot.command()
async def roast(ctx, member: discord.Member = None):
    """Light-hearted roast (friendly)"""
    member = member or ctx.author
    roasts = [
        f"{member.display_name}, you're like a cloud. When you disappear, it's a beautiful day! ☁️",
        f"{member.display_name} is so funny... not! 😅",
        f"If {member.display_name} was a vegetable, they'd be a cute-cumber! 🥒",
        f"{member.display_name}'s jokes are so bad they're good! 😂",
        f"{member.display_name} is 100% reminder that someone actually knows how to use their 0% correctly! 💯"
    ]
    await ctx.send(embed=create_embed("🔥 Roast", random.choice(roasts)))

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """Ship two users together"""
    user2 = user2 or ctx.author
    if user1 == user2:
        await ctx.send(embed=create_embed("❌ Error", "You can't ship someone with themselves!", 0xFF0000))
        return
    
    score = random.randint(0, 100)
    if score > 90:
        status = "Perfect Match! 💖"
    elif score > 70:
        status = "Great Match! ❤️"
    elif score > 50:
        status = "Good Match! 💕"
    elif score > 30:
        status = "Maybe... 💘"
    else:
        status = "Not a great match... 💔"
    
    await ctx.send(embed=create_embed("💞 Ship", f"**{user1.display_name}** + **{user2.display_name}**\nCompatibility: **{score}%**\n{status}"))

@bot.command()
async def hack(ctx, member: discord.Member = None):
    """Fake hack (just for fun)"""
    member = member or ctx.author
    msg = await ctx.send(embed=create_embed("👨‍💻 Hacking...", "Initializing hack sequence..."))
    
    steps = [
        "Bypassing firewall...",
        "Accessing mainframe...",
        "Decrypting passwords...",
        "Downloading data...",
        "Covering tracks...",
        "Hack complete!"
    ]
    
    for step in steps:
        await asyncio.sleep(1)
        await msg.edit(embed=create_embed("👨‍💻 Hacking...", step))
    
    await asyncio.sleep(1)
    await msg.edit(embed=create_embed("✅ Hack Complete", f"Successfully 'hacked' {member.display_name}!\n(This was just a joke! 😄)"))

@bot.command()
async def cat(ctx):
    """Get a random cat fact"""
    facts = [
        "Cats sleep for about 70% of their lives! 😴",
        "A group of cats is called a clowder! 🐈",
        "Cats can't taste sweetness! 🍬",
        "Cats have 32 muscles in each ear! 👂",
        "The oldest cat lived to be 38 years old! 🎂"
    ]
    await ctx.send(embed=create_embed("🐱 Cat Fact", random.choice(facts)))

# ========== GAMES COMMANDS (10) ==========
@bot.command()
async def rps(ctx, choice: str):
    """Play Rock Paper Scissors"""
    choice = choice.lower()
    if choice not in ["rock", "paper", "scissors"]:
        await ctx.send(embed=create_embed("❌ Error", "Please choose: rock, paper, or scissors", 0xFF0000))
        return
    
    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    if choice == bot_choice:
        result = "It's a tie! 🤝"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(embed=create_embed("🪨📄✂️ RPS", f"You chose: **{choice}**\nI chose: **{bot_choice}**\n**{result}**"))

@bot.command()
async def guess(ctx, number: int = None):
    """Guess a number between 1-10"""
    if number is None:
        await ctx.send(embed=create_embed("🎯 Guess", "Think of a number between 1-10 and I'll try to guess it!\nUse `!guess <number>` to make your guess."))
        return
    
    if number < 1 or number > 10:
        await ctx.send(embed=create_embed("❌ Error", "Please guess a number between 1-10", 0xFF0000))
        return
    
    bot_guess = random.randint(1, 10)
    if number == bot_guess:
        await ctx.send(embed=create_embed("🎯 Guess", f"I guessed **{bot_guess}**! You win! 🎉"))
    else:
        await ctx.send(embed=create_embed("🎯 Guess", f"I guessed **{bot_guess}**. Better luck next time!"))

@bot.command()
async def math(ctx, *, problem: str = None):
    """Solve a simple math problem"""
    if problem is None:
        await ctx.send(embed=create_embed("🧮 Math", "Give me a simple math problem like `!math 5 + 3` or `!math 10 * 2`"))
        return
    
    try:
        # Basic safety check
        problem = problem.replace(" ", "")
        if any(c not in "0123456789+-*/.() " for c in problem):
            await ctx.send(embed=create_embed("❌ Error", "Only basic math operations allowed (+, -, *, /)", 0xFF0000))
            return
        
        result = eval(problem)  # Safe because of check above
        await ctx.send(embed=create_embed("🧮 Math", f"{problem} = **{result}**"))
    except:
        await ctx.send(embed=create_embed("❌ Error", "Invalid math problem", 0xFF0000))

@bot.command()
async def trivia(ctx):
    """Answer a trivia question"""
    questions = [
        {"q": "What is the largest planet in our solar system?", "a": "Jupiter"},
        {"q": "How many continents are there?", "a": "7"},
        {"q": "What is the chemical symbol for gold?", "a": "Au"},
        {"q": "Who wrote Hamlet?", "a": "Shakespeare"},
        {"q": "What is the capital of France?", "a": "Paris"}
    ]
    
    question = random.choice(questions)
    await ctx.send(embed=create_embed("❓ Trivia", question["q"]))

@bot.command()
async def slots(ctx):
    """Play slot machine"""
    symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    
    if result[0] == result[1] == result[2]:
        win = "JACKPOT! 🎉🎉🎉"
    elif result[0] == result[1] or result[1] == result[2]:
        win = "Two in a row! 🎉"
    else:
        win = "Try again!"
    
    await ctx.send(embed=create_embed("🎰 Slots", f"[ {result[0]} | {result[1]} | {result[2]} ]\n{win}"))

@bot.command()
async def battle(ctx, member: discord.Member = None):
    """Battle another user"""
    if member is None:
        await ctx.send(embed=create_embed("⚔️ Battle", "Mention someone to battle! `!battle @user`"))
        return
    
    if member == ctx.author:
        await ctx.send(embed=create_embed("❌ Error", "You can't battle yourself!", 0xFF0000))
        return
    
    players = [ctx.author, member]
    winner = random.choice(players)
    
    moves = [
        "used a powerful spell! 🔥",
        "swung their mighty sword! ⚔️",
        "cast a healing spell! 💚",
        "threw a fireball! 🎯",
        "used stealth attack! 🥷"
    ]
    
    await ctx.send(embed=create_embed("⚔️ Battle", f"{ctx.author.display_name} {random.choice(moves)}\n{member.display_name} {random.choice(moves)}\n\n**Winner:** {winner.display_name}! 🏆"))

@bot.command()
async def tictactoe(ctx, member: discord.Member = None):
    """Start a tic-tac-toe game"""
    if member is None:
        await ctx.send(embed=create_embed("❌ Error", "Mention someone to play with! `!tictactoe @user`", 0xFF0000))
        return
    
    await ctx.send(embed=create_embed("⭕ Tic-Tac-Toe", f"{ctx.author.mention} vs {member.mention}\nUse reactions to play! (Game in development)"))

@bot.command()
async def count(ctx):
    """Start a counting game"""
    if ctx.channel.id not in bot_data["game_scores"]:
        bot_data["game_scores"][ctx.channel.id] = {"count": 0, "last_user": None}
    
    current = bot_data["game_scores"][ctx.channel.id]["count"]
    await ctx.send(embed=create_embed("🔢 Count", f"Current count: **{current}**\nNext number: **{current + 1}**\nSay the next number to continue!"))

@bot.command()
async def wordchain(ctx, *, word: str = None):
    """Play word chain game"""
    if word is None:
        await ctx.send(embed=create_embed("🔤 Word Chain", "Start with any word! `!wordchain apple`"))
        return
    
    last_letter = word[-1].lower()
    suggestions = []
    words = ["apple", "elephant", "tiger", "rabbit", "turtle", "eagle", "egg", "giraffe", "elephant", "tomato"]
    
    for w in words:
        if w[0].lower() == last_letter:
            suggestions.append(w)
    
    if suggestions:
        await ctx.send(embed=create_embed("🔤 Word Chain", f"Word: **{word}**\nNext word must start with: **{last_letter.upper()}**\nSuggestions: {', '.join(suggestions[:3])}"))
    else:
        await ctx.send(embed=create_embed("🔤 Word Chain", f"Word: **{word}**\nNext word must start with: **{last_letter.upper()}**\nNo suggestions found!"))

@bot.command()
async def leaderboard(ctx):
    """Show game leaderboard"""
    if not bot_data["game_scores"]:
        await ctx.send(embed=create_embed("🏆 Leaderboard", "No scores yet! Play some games first!"))
        return
    
    # Simple leaderboard
    scores = []
    for user_id, data in bot_data.get("user_stats", {}).items():
        if "wins" in data:
            scores.append((user_id, data["wins"]))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    
    embed = create_embed("🏆 Leaderboard", "Top players:")
    for i, (user_id, wins) in enumerate(scores[:10], 1):
        try:
            user = await bot.fetch_user(user_id)
            embed.add_field(name=f"{i}. {user.display_name}", value=f"{wins} wins", inline=False)
        except:
            pass
    
    await ctx.send(embed=embed)

# ========== MODERATION COMMANDS (15) ==========
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kick a member"""
    if member == ctx.author:
        await ctx.send(embed=create_embed("❌ Error", "You can't kick yourself!", 0xFF0000))
        return
    if member.top_role >= ctx.author.top_role:
        await ctx.send(embed=create_embed("❌ Error", "You can't kick someone with equal or higher role!", 0xFF0000))
        return
    
    await member.kick(reason=reason)
    await ctx.send(embed=create_embed("👢 Kicked", f"{member.mention} has been kicked.\nReason: {reason}", 0xFFA500))

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban a member"""
    if member == ctx.author:
        await ctx.send(embed=create_embed("❌ Error", "You can't ban yourself!", 0xFF0000))
        return
    if member.top_role >= ctx.author.top_role:
        await ctx.send(embed=create_embed("❌ Error", "You can't ban someone with equal or higher role!", 0xFF0000))
        return
    
    await member.ban(reason=reason)
    await ctx.send(embed=create_embed("🔨 Banned", f"{member.mention} has been banned.\nReason: {reason}", 0xFF0000))

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    """Unban a user by ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(embed=create_embed("✅ Unbanned", f"{user} has been unbanned.", 0x00FF00))
    except:
        await ctx.send(embed=create_embed("❌ Error", "User not found or not banned", 0xFF0000))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    """Timeout a member"""
    if minutes < 1 or minutes > 10080:
        await ctx.send(embed=create_embed("❌ Error", "Timeout must be between 1 and 10080 minutes (1 week)", 0xFF0000))
        return
    
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(embed=create_embed("⏰ Timeout", f"{member.mention} has been timed out for {minutes} minute(s).\nReason: {reason}", 0xFFA500))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    """Remove timeout from a member"""
    await member.timeout(None)
    await ctx.send(embed=create_embed("✅ Timeout Removed", f"{member.mention}'s timeout has been removed.", 0x00FF00))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    """Delete messages"""
    if amount < 1 or amount > 100:
        await ctx.send(embed=create_embed("❌ Error", "Amount must be between 1 and 100", 0xFF0000))
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=create_embed("🧹 Purged", f"Deleted {len(deleted) - 1} messages.", 0x00FF00))
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    """Set slowmode"""
    if seconds < 0 or seconds > 21600:
        await ctx.send(embed=create_embed("❌ Error", "Slowmode must be between 0 and 21600 seconds (6 hours)", 0xFF0000))
        return
    
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send(embed=create_embed("✅ Slowmode", "Slowmode disabled.", 0x00FF00))
    else:
        await ctx.send(embed=create_embed("🐌 Slowmode", f"Slowmode set to {seconds} second(s).", 0xFFA500))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Lock the channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=create_embed("🔒 Locked", "Channel locked.", 0xFF0000))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Unlock the channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=create_embed("🔓 Unlocked", "Channel unlocked.", 0x00FF00))

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    """Warn a member"""
    user_id = str(member.id)
    if user_id not in bot_data["warnings"]:
        bot_data["warnings"][user_id] = []
    
    bot_data["warnings"][user_id].append({
        "reason": reason,
        "moderator": ctx.author.id,
        "timestamp": time.time()
    })
    
    await ctx.send(embed=create_embed("⚠️ Warned", f"{member.mention} has been warned.\nReason: {reason}\nTotal warnings: {len(bot_data['warnings'][user_id])}", 0xFFA500))

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """View warnings"""
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in bot_data["warnings"] or not bot_data["warnings"][user_id]:
        await ctx.send(embed=create_embed("✅ Clean Record", f"{member.display_name} has no warnings.", 0x00FF00))
        return
    
    warnings = bot_data["warnings"][user_id]
    embed = create_embed(f"⚠️ Warnings for {member.display_name}", f"Total: {len(warnings)}")
    
    for i, warn in enumerate(warnings[-5:], 1):
        try:
            mod = await bot.fetch_user(warn["moderator"])
            mod_name = mod.display_name
        except:
            mod_name = "Unknown"
        
        time_str = datetime.fromtimestamp(warn["timestamp"]).strftime("%Y-%m-%d")
        embed.add_field(name=f"Warning #{i}", value=f"Reason: {warn['reason']}\nBy: {mod_name}\nDate: {time_str}", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    """Clear all warnings for a member"""
    user_id = str(member.id)
    if user_id in bot_data["warnings"]:
        count = len(bot_data["warnings"][user_id])
        bot_data["warnings"][user_id] = []
        await ctx.send(embed=create_embed("✅ Cleared", f"Cleared {count} warning(s) for {member.mention}.", 0x00FF00))
    else:
        await ctx.send(embed=create_embed("ℹ️ Info", f"{member.display_name} has no warnings to clear.", 0x5865F2))

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    """Change a member's nickname"""
    if nickname and len(nickname) > 32:
        await ctx.send(embed=create_embed("❌ Error", "Nickname must be 32 characters or less", 0xFF0000))
        return
    
    await member.edit(nick=nickname)
    if nickname:
        await ctx.send(embed=create_embed("✅ Nickname Changed", f"{member.mention}'s nickname changed to: {nickname}", 0x00FF00))
    else:
        await ctx.send(embed=create_embed("✅ Nickname Reset", f"{member.mention}'s nickname has been reset.", 0x00FF00))

@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, action: str, member: discord.Member, *, role_name: str):
    """Add or remove a role"""
    action = action.lower()
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        await ctx.send(embed=create_embed("❌ Error", f"Role '{role_name}' not found", 0xFF0000))
        return
    
    if action in ["add", "give"]:
        await member.add_roles(role)
        await ctx.send(embed=create_embed("✅ Role Added", f"Added {role.name} to {member.mention}", 0x00FF00))
    elif action in ["remove", "take"]:
        await member.remove_roles(role)
        await ctx.send(embed=create_embed("✅ Role Removed", f"Removed {role.name} from {member.mention}", 0x00FF00))
    else:
        await ctx.send(embed=create_embed("❌ Error", "Use: add/give or remove/take", 0xFF0000))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member):
    """Mute a member (server mute)"""
    if member.voice:
        await member.edit(mute=True)
        await ctx.send(embed=create_embed("🔇 Muted", f"{member.mention} has been voice muted.", 0xFFA500))
    else:
        await ctx.send(embed=create_embed("❌ Error", "User must be in a voice channel", 0xFF0000))

# ========== ADMIN COMMANDS (10) ==========
@bot.command()
@is_owner()
async def setprefix(ctx, new_prefix: str):
    """Change bot prefix (Owner only)"""
    if len(new_prefix) > 3:
        await ctx.send(embed=create_embed("❌ Error", "Prefix must be 3 characters or less", 0xFF0000))
        return
    
    bot.command_prefix = new_prefix
    await ctx.send(embed=create_embed("✅ Prefix Changed", f"Prefix changed to: `{new_prefix}`", 0x00FF00))

@bot.command()
@is_owner()
async def setstatus(ctx, *, status: str):
    """Change bot status (Owner only)"""
    await bot.change_presence(activity=discord.Game(name=status))
    await ctx.send(embed=create_embed("✅ Status Changed", f"Status set to: {status}", 0x00FF00))

@bot.command()
@is_owner()
async def setactivity(ctx, activity_type: str, *, name: str):
    """Change bot activity type (Owner only)"""
    activity_type = activity_type.lower()
    
    if activity_type == "playing":
        activity = discord.Game(name=name)
    elif activity_type == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=name)
    elif activity_type == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=name)
    elif activity_type == "streaming":
        activity = discord.Activity(type=discord.ActivityType.streaming, name=name, url="https://twitch.tv/")
    else:
        await ctx.send(embed=create_embed("❌ Error", "Activity type must be: playing, listening, watching, or streaming", 0xFF0000))
        return
    
    await bot.change_presence(activity=activity)
    await ctx.send(embed=create_embed("✅ Activity Changed", f"Activity set to: {activity_type} {name}", 0x00FF00))

@bot.command()
@is_owner()
async def reload(ctx):
    """Reload the bot (Owner only)"""
    await ctx.send(embed=create_embed("🔄 Reloading", "Bot is reloading...", 0xFFA500))
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
@is_owner()
async def shutdown(ctx):
    """Shutdown the bot (Owner only)"""
    await ctx.send(embed=create_embed("🛑 Shutdown", "Bot is shutting down...", 0xFF0000))
    await bot.close()

@bot.command()
@is_owner()
async def restart(ctx):
    """Restart the bot (Owner only)"""
    await ctx.send(embed=create_embed("🔄 Restarting", "Bot is restarting...", 0xFFA500))
    await bot.close()
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message):
    """Make an announcement"""
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=0xFFD700,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Announced by {ctx.author.display_name}")
    await ctx.send("@everyone", embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def poll(ctx, *, question):
    """Create a poll"""
    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=0x5865F2,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("🤷")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, duration: int, *, prize):
    """Start a giveaway"""
    if duration < 1 or duration > 10080:
        await ctx.send(embed=create_embed("❌ Error", "Duration must be between 1 and 10080 minutes (1 week)", 0xFF0000))
        return
    
    end_time = time.time() + (duration * 60)
    embed = discord.Embed(
        title="🎉 Giveaway",
        description=f"**Prize:** {prize}\n**Duration:** {duration} minute(s)\nReact with 🎉 to enter!",
        color=0x00FF00,
        timestamp=datetime.fromtimestamp(end_time)
    )
    embed.set_footer(text="Giveaway ends")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    
    # Store giveaway data
    if "giveaways" not in bot_data:
        bot_data["giveaways"] = []
    bot_data["giveaways"].append({
        "message_id": msg.id,
        "channel_id": ctx.channel.id,
        "prize": prize,
        "end_time": end_time,
        "creator": ctx.author.id
    })

@bot.command()
@commands.has_permissions(administrator=True)
async def config(ctx, setting: str = None, value: str = None):
    """Configure bot settings"""
    if setting is None:
        embed = create_embed("⚙️ Config", "Available settings: prefix, status")
        embed.add_field(name="Current Config", value=f"Prefix: {PREFIX}\nStatus: {bot.activity}", inline=False)
        await ctx.send(embed=embed)
        return
    
    await ctx.send(embed=create_embed("⚙️ Config", f"Setting {setting} to {value} (config saved in memory)"))

# ========== PRANK COMMANDS (5) ==========
@bot.command()
async def trollkick(ctx, member: discord.Member):
    """Fake kick (harmless prank)"""
    embed = discord.Embed(
        title="👢 Kicked",
        description=f"{member.mention} has been kicked from the server.",
        color=0xFFA500,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Kicked by {ctx.author.display_name}")
    await ctx.send(embed=embed)
    await asyncio.sleep(2)
    await ctx.send(f"Just kidding! {member.mention} wasn't actually kicked! 😄")

@bot.command()
async def fakeban(ctx, member: discord.Member):
    """Fake ban (harmless prank)"""
    embed = discord.Embed(
        title="🔨 Banned",
        description=f"{member.mention} has been banned from the server.",
        color=0xFF0000,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Banned by {ctx.author.display_name}")
    await ctx.send(embed=embed)
    await asyncio.sleep(2)
    await ctx.send(f"Gotcha! {member.mention} is still here! 😜")

@bot.command()
async def fakecrash(ctx):
    """Fake bot crash"""
    await ctx.send("⚠️ **SYSTEM ERROR**")
    await asyncio.sleep(1)
    await ctx.send("Bot is crashing...")
    await asyncio.sleep(1)
    await ctx.send("Just kidding! I'm still here! 🤖")

@bot.command()
async def ghostping(ctx, member: discord.Member):
    """Ghost ping someone"""
    msg = await ctx.send(member.mention)
    await asyncio.sleep(0.5)
    await msg.delete()
    await ctx.send("👻 Boo! Ghost ping!", delete_after=2)

@bot.command()
async def rickroll(ctx):
    """Rickroll someone"""
    await ctx.send("Never gonna give you up\nNever gonna let you down\nNever gonna run around and desert you\n🎵 https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# ========== REMINDER CHECKER ==========
async def check_reminders():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = time.time()
        reminders_to_remove = []
        
        for i, reminder in enumerate(bot_data["reminders"]):
            if now >= reminder["time"]:
                try:
                    channel = bot.get_channel(reminder["channel"])
                    user = await bot.fetch_user(reminder["user"])
                    if channel:
                        await channel.send(f"⏰ Reminder for {user.mention}: {reminder['reminder']}")
                    reminders_to_remove.append(i)
                except:
                    reminders_to_remove.append(i)
        
        # Remove sent reminders
        for i in sorted(reminders_to_remove, reverse=True):
            bot_data["reminders"].pop(i)
        
        await asyncio.sleep(60)

# ========== MAIN ==========
if __name__ == "__main__":
    # Start HTTP server in background thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Start reminder checker
    bot.loop.create_task(check_reminders())
    
    # Run bot
    if TOKEN:
        print(f"Starting bot on port {PORT}...")
        print(f"HTTP server: http://localhost:{PORT}")
        print(f"Total commands: {len(bot.commands)}")
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_TOKEN environment variable not set!")
        print("Set it in Render Dashboard -> Environment Variables")
