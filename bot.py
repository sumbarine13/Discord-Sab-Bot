import discord
from discord.ext import commands
from discord import app_commands
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
import uvicorn
import httpx

# ---------------- Discord Bot ----------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- Bot Settings ----------------
bot_settings = {
    "prefix": "!",
    "welcome_msg": "Welcome to the server!",
    "question_words": ["who","what","when","where","why","how","can"],
    "recent_messages": [],
    "groq_model": "llama-3.1-8b-instant",
    "groq_api_key": "GROQ_API_KEY_PLACEHOLDER"
}

# Only this user can run restricted slash commands
ALLOWED_USER_ID = 1307042499898118246

# ---------------- Question Detection ----------------
def is_question(message: str):
    msg = message.lower().strip()
    return any(msg.startswith(w) for w in bot_settings["question_words"]) or msg.endswith("?")

# ---------------- Discord Events ----------------
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

# ---------------- Groq API ----------------
async def query_groq(prompt: str):
    url = "https://api.groq.com/v1/query"  # Placeholder URL
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

# ---------------- Slash Command Example ----------------
@bot.tree.command(name="secret", description="Restricted command")
async def secret(interaction: discord.Interaction):
    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        return
    await interaction.response.send_message("Hello, authorized user!")

# ---------------- FastAPI Dashboard ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"status": "online"}

@app.get("/settings")
def get_settings():
    return bot_settings

@app.post("/update_prefix")
def update_prefix(prefix: str):
    bot_settings["prefix"] = prefix
    bot.command_prefix = lambda _: prefix
    return {"status": "ok"}

@app.post("/update_welcome")
def update_welcome(welcome: str):
    bot_settings["welcome_msg"] = welcome
    return {"status": "ok"}

@app.post("/update_question_words")
def update_question_words(words: str):
    bot_settings["question_words"] = [w.strip() for w in words.split(",")]
    return {"status": "ok"}

@app.post("/update_groq_model")
def update_groq_model(model: str):
    bot_settings["groq_model"] = model
    return {"status": "ok"}

@app.get("/recent_messages")
def recent_messages():
    return {"messages": bot_settings["recent_messages"][-20:]}

# ---------------- Run API Server ----------------
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

threading.Thread(target=run_api).start()

# ---------------- Run Bot ----------------
bot.run("DISCORD_BOT_TOKEN_PLACEHOLDER")
