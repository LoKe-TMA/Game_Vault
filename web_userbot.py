import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from google import genai
from fastapi import FastAPI
import uvicorn

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ===============================================
# ၁။ CONFIGURATION & ENVIRONMENT VARIABLES
# ===============================================

API_ID = int(os.environ.get("API_ID", 0)) 
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 

MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
COMMAND_PREFIX = [".ai", "/ai"]

# ===============================================
# ၂။ CLIENT INITIALIZATION (Global Objects)
# ===============================================

app_pyrogram = None  # Pyrogram Client ကို Global အဖြစ် သတ်မှတ်
gemini_client = None # Gemini Client ကို Global အဖြစ် သတ်မှတ်
app_fastapi = FastAPI(title="Gemini UserBot Web Worker") # FastAPI App

# ===============================================
# ၃။ PYROGRAM HANDLERS
# ===============================================

async def initialize_clients():
    """Pyrogram နှင့် Gemini Client များကို စတင်ခြင်း"""
    global app_pyrogram, gemini_client

    if not API_ID or not API_HASH or not SESSION_STRING:
        logging.error("❌ Telegram API/Session variables are missing.")
        return False
    if not GEMINI_API_KEY:
        logging.error("❌ GEMINI_API_KEY is missing.")
        return False

    # Gemini Client
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logging.info("✅ Gemini Client successfully initialized.")
    except Exception as e:
        logging.error(f"❌ Gemini Client initialization failed: {e}")
        return False

    # Pyrogram Client
    try:
        app_pyrogram = Client(
            session_string=SESSION_STRING, 
            api_id=API_ID,
            api_hash=API_HASH,
            # Handler များကို မှတ်ပုံတင်ရန်
            plugins={"root": "web_userbot"} 
        )
        logging.info("✅ Pyrogram Client initialized with Session String.")
    except Exception as e:
        logging.error(f"❌ Pyrogram Client initialization failed: {e}")
        return False
    
    return True

@app_pyrogram.on_message(filters.me & filters.text & filters.command(COMMAND_PREFIX, prefixes=""))
async def gemini_response_handler(client: Client, message: Message):
    """Gemini API ကို အသုံးပြုပြီး မက်ဆေ့ခ်ျများကို တုံ့ပြန်သည်"""
    
    if not gemini_client:
        await message.edit("❌ Gemini Client is unavailable.")
        return

    # Extract prompt
    # ... (ယခင်ကအတိုင်း)
    
    full_command = message.text.split(maxsplit=1)
    if len(full_command) < 2:
        await message.edit(f"❓ **အသုံးပြုပုံ:** `{COMMAND_PREFIX[0]} မေးခွန်း`")
        return
    
    prompt = full_command[1].strip()

    try:
        await message.edit("🧠 **Thinking...**")
    except FloodWait:
        await asyncio.sleep(5)
        await message.edit("🧠 **Thinking...**") 

    
    # Call Gemini API
    try:
        response = gemini_client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )

        ai_response = response.text
        final_response = f"**Query:** `{prompt}`\n\n---\n\n{ai_response}"
        await message.edit(final_response, parse_mode="markdown")

    except Exception as e:
        error_message = f"🚫 Gemini API Error: `{e}`"
        logging.error(error_message)
        await message.edit(error_message)


# ===============================================
# ၄။ FASTAPI WEB SERVICE LOGIC
# ===============================================

@app_fastapi.on_event("startup")
async def startup_event():
    """Web Server စတင်သောအခါ Pyrogram Client ကို စတင်မည်"""
    global app_pyrogram
    
    success = await initialize_clients()
    if success:
        # Pyrogram Client ကို Background မှာ Run စေရန်
        asyncio.create_task(app_pyrogram.start())
        logging.info("⭐ Pyrogram client started in background.")
    else:
        logging.critical("🚨 Bot cannot start due to initialization failure.")
        # Failed ဆိုရင်တော့ Bot က အလုပ်မလုပ်တော့ပါဘူး

@app_fastapi.on_event("shutdown")
async def shutdown_event():
    """Web Server ရပ်သောအခါ Pyrogram Client ကို ရပ်တန့်မည်"""
    if app_pyrogram:
        await app_pyrogram.stop()
        logging.info("🛑 Pyrogram client stopped.")

@app_fastapi.get("/")
@app_fastapi.get("/health")
async def health_check():
    """Render Health Check အတွက် တုံ့ပြန်ရန်"""
    status = "running" if app_pyrogram and app_pyrogram.is_running else "not started"
    return {"status": "ok", "bot_status": status, "model": MODEL_NAME}

# ===============================================
# ၅။ ENTRY POINT FOR RENDER
# ===============================================

# Local မှာ Run ရင် uvicorn ကို သုံးပြီး ခေါ်ဖို့အတွက်
if __name__ == "__main__":
    # Render မှာ Environment Variable 'PORT' ကို Auto ပေးတဲ့အတွက် 
    # local run မှာ 8000 ကို သုံးထားသည်
    PORT = int(os.environ.get("PORT", 8000)) 
    uvicorn.run("web_userbot:app_fastapi", host="0.0.0.0", port=PORT, log_level="info")
