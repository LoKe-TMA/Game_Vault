import os
import asyncio
import logging
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
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

# Render (သို့မဟုတ် .env) မှ တန်ဖိုးများ ရယူသည်
API_ID = int(os.environ.get("API_ID", 0)) 
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 

MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# ===============================================
# ၂။ GLOBAL OBJECTS & INITIALIZATION
# ===============================================

app_pyrogram: Client = None 
gemini_client = None 
app_fastapi = FastAPI(title="Gemini Freedom UserBot") 

# -----------------------------------------------
# Pyrogram Handler Function
# -----------------------------------------------

async def gemini_response_handler(client: Client, message: Message):
    """
    Freedom Mode: DM တွင် သူငယ်ချင်းများထံမှ စာသားမက်ဆေ့ခ်ျတိုင်းကို အဖြေပြန်သည်
    """
    
    if not gemini_client:
        logging.error("Gemini Client is unavailable. Aborting response.")
        return

    # 1. မက်ဆေ့ခ်ျတစ်ခုလုံးကို prompt အဖြစ် တိုက်ရိုက်ယူပါ
    prompt = message.text.strip()

    if not prompt:
        # စာသားမဟုတ်သော မက်ဆေ့ခ်ျများ (e.g. photo, sticker) ကို ကျော်လိုက်ပါ
        return 

    # 2. Thinking message ကို အရင် Reply ပို့ပါ
    chat_id = message.chat.id
    
    try:
        thinking_msg = await client.send_message(
            chat_id, 
            "🧠 **Thinking...**",
            reply_to_message_id=message.id 
        )
    except FloodWait as e:
        logging.warning(f"FloodWait on sending message: waiting {e.value}s")
        await asyncio.sleep(e.value)
        thinking_msg = await client.send_message(chat_id, "🧠 **Thinking...**", reply_to_message_id=message.id)


    # 3. Call Gemini API
    try:
        response = gemini_client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )

        ai_response = response.text
        
        # 4. အဖြေရလာသောအခါ 'Thinking' message ကို Edit လုပ်ပါ
        final_response = f"**Query:** `{prompt}`\n\n---\n\n{ai_response}"
        
        await thinking_msg.edit_text(final_response, parse_mode="markdown")

    except Exception as e:
        error_message = f"🚫 Gemini API Error: `{type(e).__name__}: {e}`"
        logging.error(error_message)
        
        # Error ကို Thinking message နေရာမှာ ပြင်ပါ
        await thinking_msg.edit_text(error_message)


# -----------------------------------------------
# Client Initialization Function
# -----------------------------------------------

async def initialize_clients():
    """Pyrogram နှင့် Gemini Client များကို စတင်ပြီး Handler မှတ်ပုံတင်ခြင်း"""
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

    # Pyrogram Client (Name Missing Error ကို ဖြေရှင်းပြီး)
    try:
        app_pyrogram = Client(
            name=SESSION_STRING, # SESSION_STRING ကို 'name' argument အဖြစ် ပေးခြင်း
            api_id=API_ID,
            api_hash=API_HASH,
        )
        logging.info("✅ Pyrogram Client initialized with Session String (Fix applied).")
    except Exception as e:
        logging.error(f"❌ Pyrogram Client initialization failed: {e}")
        return False
    
    # 💡 Freedom Filter: စာသား & Private Chat & ကိုယ့်ကိုယ်ကို ပို့တာ မဟုတ်ရ
    if app_pyrogram:
        # Filters: Text Message & Private Chat & Not Me (သူငယ်ချင်းရဲ့ စာသာ)
        message_filters = filters.text & filters.private & ~filters.me 
        
        app_pyrogram.add_handler(
            MessageHandler(gemini_response_handler, message_filters)
        )
        logging.info("✅ Auto-reply handler registered for all INCOMING DM messages.")
        
    return True

# ===============================================
# ၃။ FASTAPI WEB SERVICE LOGIC (Startup/Shutdown/Health)
# ===============================================

@app_fastapi.on_event("startup")
async def startup_event():
    """Web Server စတင်သောအခါ Pyrogram Client ကို Background တွင် စတင်မည်"""
    if await initialize_clients():
        # Client ကို Background Task အဖြစ် Run ခြင်း
        asyncio.create_task(app_pyrogram.start()) 
        logging.info("⭐ Pyrogram client started in background task.")
    else:
        logging.critical("🚨 Bot initialization failed. Check environment variables.")

@app_fastapi.on_event("shutdown")
async def shutdown_event():
    """Web Server ရပ်သောအခါ Pyrogram Client ကို ရပ်တန့်မည်"""
    # 💡 ပြင်ဆင်ချက်: is_running ကို ဖယ်ရှားပြီး app_pyrogram ရှိမရှိသာ စစ်ဆေးခြင်း
    if app_pyrogram: 
        await app_pyrogram.stop()
        logging.info("🛑 Pyrogram client stopped.")

@app_fastapi.get("/")
@app_fastapi.get("/health")
async def health_check():
    """Render Health Check အတွက် တုံ့ပြန်ရန်"""
    # 💡 ပြင်ဆင်ချက်: app_pyrogram object ရှိနေခြင်းကိုသာ စစ်ဆေးခြင်း
    status = "running" if app_pyrogram else "not started"
    return {"status": "ok", "bot_status": status, "model": MODEL_NAME}

# ===============================================
# ၄။ ENTRY POINT
# ===============================================

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000)) 
    uvicorn.run("web_userbot:app_fastapi", host="0.0.0.0", port=PORT, log_level="info")
