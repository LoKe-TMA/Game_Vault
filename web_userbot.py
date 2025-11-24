import os
import asyncio
import logging
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
# MessageHandler ကို import လုပ်ရန်
from pyrogram.handlers import MessageHandler 
from google import genai
from fastapi import FastAPI
from dotenv import load_dotenv

# .env ဖိုင်မှ တန်ဖိုးများကို load လုပ်သည် (Local စမ်းသပ်ရန်အတွက်)
load_dotenv() 

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ===============================================
# ၁။ CONFIGURATION & ENVIRONMENT VARIABLES
# ===============================================

# Environment Variables မှ တန်ဖိုးများ ရယူပါ (Render တွင် ၎င်းတို့၏ Environment Variables ကို သုံးမည်)
API_ID = int(os.environ.get("API_ID", 0)) 
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 

MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
# .env မှရသော string ကို list အဖြစ် ပြန်ပြောင်းသည်
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX_LIST", ".ai").split() 

# ===============================================
# ၂။ GLOBAL OBJECTS & INITIALIZATION
# ===============================================

app_pyrogram = None 
gemini_client = None 
app_fastapi = FastAPI(title="Gemini UserBot Web Worker") 

# -----------------------------------------------
# Pyrogram Handler Function
# -----------------------------------------------

# Decorator မပါဝင်ပါ၊ ဤ function ကို initialize_clients() ထဲတွင် မှတ်ပုံတင်ပါမည်။
async def gemini_response_handler(client: Client, message: Message):
    """
    UserBot ၏ မက်ဆေ့ခ်ျများကို စောင့်ကြည့်ပြီး Gemini API မှတဆင့် တုံ့ပြန်သည်
    """
    
    if not gemini_client:
        await message.edit("❌ Gemini Client is unavailable. Check API Key.")
        return

    # Extract prompt
    full_command = message.text.split(maxsplit=1)
    if len(full_command) < 2:
        await message.edit(f"❓ **အသုံးပြုပုံ:** `{COMMAND_PREFIX[0]} မေးခွန်း`")
        return
    
    prompt = full_command[1].strip()

    try:
        await message.edit("🧠 **Thinking...**")
    except FloodWait as e:
        await asyncio.sleep(e.value)
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
        error_message = f"🚫 Gemini API Error: `{type(e).__name__}: {e}`"
        logging.error(error_message)
        await message.edit(error_message)


# -----------------------------------------------
# Client Initialization Function
# -----------------------------------------------

async def initialize_clients():
    """Pyrogram နှင့် Gemini Client များကို စတင်ခြင်း"""
    global app_pyrogram, gemini_client

    if not API_ID or not API_HASH or not SESSION_STRING:
        logging.critical("❌ Telegram API/Session variables are missing.")
        return False
    if not GEMINI_API_KEY:
        logging.critical("❌ GEMINI_API_KEY is missing.")
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
        )
        logging.info("✅ Pyrogram Client initialized with Session String.")
    except Exception as e:
        logging.error(f"❌ Pyrogram Client initialization failed: {e}")
        return False
    
    # 💡 Handler ကို Client Object တွင် မှတ်ပုံတင်ခြင်း (Error ဖြေရှင်းချက်)
    if app_pyrogram:
        message_filters = filters.me & filters.text & filters.command(COMMAND_PREFIX, prefixes="")
        
        app_pyrogram.add_handler(
            MessageHandler(gemini_response_handler, message_filters)
        )
        logging.info("✅ Gemini response handler registered.")
        
    return True

# ===============================================
# ၃။ FASTAPI WEB SERVICE LOGIC (Startup/Shutdown)
# ===============================================

@app_fastapi.on_event("startup")
async def startup_event():
    """Web Server စတင်သောအခါ Pyrogram Client ကို Background တွင် စတင်မည်"""
    if await initialize_clients():
        # Pyrogram Client ကို Background Task အနေနဲ့ Run ခြင်း
        asyncio.create_task(app_pyrogram.start())
        logging.info("⭐ Pyrogram client started in background task.")
    else:
        logging.critical("🚨 Bot initialization failed. Check environment variables.")

@app_fastapi.on_event("shutdown")
async def shutdown_event():
    """Web Server ရပ်သောအခါ Pyrogram Client ကို ရပ်တန့်မည်"""
    if app_pyrogram and app_pyrogram.is_running:
        await app_pyrogram.stop()
        logging.info("🛑 Pyrogram client stopped.")

@app_fastapi.get("/")
@app_fastapi.get("/health")
async def health_check():
    """Render Health Check အတွက် တုံ့ပြန်ရန်"""
    status = "running" if app_pyrogram and app_pyrogram.is_running else "not started"
    return {"status": "ok", "bot_status": status, "model": MODEL_NAME}

# ===============================================
# ၄။ ENTRY POINT
# ===============================================

if __name__ == "__main__":
    # Local run အတွက် uvicorn ကို သုံးပြီး ခေါ်ဖို့
    PORT = int(os.environ.get("PORT", 8000)) 
    # module:app_fastapi ပုံစံ မှန်ကန်ကြောင်း သေချာပါစေ (web_userbot:app_fastapi)
    uvicorn.run("web_userbot:app_fastapi", host="0.0.0.0", port=PORT, log_level="info")
