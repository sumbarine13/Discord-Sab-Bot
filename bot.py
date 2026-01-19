import os
import discord
from discord.ext import commands
from discord import app_commands
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import threading

# ----------------- Discord Bot -----------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ALLOWED_USER_ID = 1307042499898118246

# ----------------- Bot Settings -----------------
bot_settings = {
    "prefix": "!",
    "name": "SAB HUB",
    "welcome_msg": "Welcome to the server!",
    "goodbye_msg": "Goodbye!",
    "question_words": ["who", "what", "when", "where", "why", "how", "can"],
    "recent_messages": [],
    "groq_model": "llama-3.1-8b-instant",
    "groq_api_key": os.getenv("GROQ_API_KEY"),
    "strict_question_mode": True,
    "only_who_what_when_where": True,
    "theme": "rainbow",
    "dashboard_password": "AaravBisht123",
    "welcome_channel": None
}

# ----------------- Discord Events -----------------
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Error syncing commands:", e)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if is_question(message.content):
        bot_settings["recent_messages"].append(message.content)
        response = await query_groq(message.content)
        await message.channel.send(response)
    await bot.process_commands(message)

# ----------------- Question Detection -----------------
def is_question(message: str):
    msg = message.lower().strip()
    if bot_settings["only_who_what_when_where"]:
        return any(msg.startswith(w) for w in bot_settings["question_words"]) or msg.endswith("?")
    return False

# ----------------- Groq API -----------------
import httpx
async def query_groq(prompt: str):
    url = "https://api.groq.com/v1/query"  # Placeholder
    headers = {
        "Authorization": f"Bearer {bot_settings['groq_api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": bot_settings["groq_model"],
        "prompt": prompt,
        "max_tokens": 100
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, headers=headers, json=data)
            res.raise_for_status()
            result = res.json()
            return result.get("output", "I couldn't answer that.")
        except Exception as e:
            print("Groq API Error:", e)
            return "Error contacting Groq API."

# ----------------- Discord Slash Commands -----------------
@bot.tree.command(name="set_welcome", description="Set the welcome message")
@app_commands.describe(message="Welcome message", channel="Channel name")
async def set_welcome(interaction: discord.Interaction, message: str, channel: str):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        return
    bot_settings["welcome_msg"] = message
    bot_settings["welcome_channel"] = channel
    await interaction.response.send_message(f"Welcome message updated for channel {channel}!", ephemeral=True)

@bot.tree.command(name="set_prefix", description="Set bot command prefix")
@app_commands.describe(prefix="New prefix")
async def set_prefix(interaction: discord.Interaction, prefix: str):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        return
    bot_settings["prefix"] = prefix
    await interaction.response.send_message(f"Prefix updated to {prefix}", ephemeral=True)

# Add more slash commands for all other features similarly...

# ----------------- FastAPI Dashboard -----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve dashboard HTML
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, password: str = None):
    if password != bot_settings["dashboard_password"]:
        return HTMLResponse(
            """
            <html>
            <body style='font-family:sans-serif; text-align:center; margin-top:50px;'>
            <h1>Enter Dashboard Password</h1>
            <form method="get">
                <input type="password" name="password" placeholder="Password"/>
                <button type="submit">Enter</button>
            </form>
            </body>
            </html>
            """
        )
    # Serve main dashboard
    with open("dashboard.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(html_content)

# ----------------- Run both Discord bot and FastAPI -----------------
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    t = threading.Thread(target=run_api)
    t.start()
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
