import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, SessionPasswordNeeded
from google import genai

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ===============================================
# ၁။ CONFIGURATION & ENVIRONMENT VARIABLES
# ===============================================

# Environment Variables မှ တန်ဖိုးများ ရယူပါ
API_ID = int(os.environ.get("API_ID", 0)) 
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") # Render မှာ အဓိကသုံးမယ့် Session String
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 

# Configuration Options
MODEL_NAME = "gemini-2.5-flash"
COMMAND_PREFIX = [".ai", "/ai"]

# Validate crucial variables
if not API_ID or not API_HASH:
    logging.error("❌ API_ID and API_HASH must be set in Environment Variables.")
    exit(1)

if not GEMINI_API_KEY:
    logging.error("❌ GEMINI_API_KEY must be set in Environment Variables.")
    exit(1)

# ===============================================
# ၂။ CLIENT INITIALIZATION
# ===============================================

# Pyrogram Client
try:
    if SESSION_STRING:
        # Session String ကို သုံးပြီး Client ကို စတင်ခြင်း (Render အတွက် အကောင်းဆုံး)
        app = Client(
            session_name=SESSION_STRING, 
            api_id=API_ID,
            api_hash=API_HASH,
        )
        logging.info("✅ Pyrogram Client initialized using SESSION_STRING.")
    else:
        # Local run သို့မဟုတ် ပထမဆုံးအကြိမ် login အတွက် session name ကိုသုံးခြင်း
        app = Client(
            "gemini_userbot_session", # Session file နာမည်
            api_id=API_ID,
            api_hash=API_HASH
        )
        logging.warning("⚠️ SESSION_STRING is missing. Client will try to log in interactively (might fail on Render).")

except Exception as e:
    logging.error(f"❌ Pyrogram Client initialization failed: {e}")
    exit(1)

# Gemini Client
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logging.info(f"✅ Gemini Client successfully initialized with model: {MODEL_NAME}.")
except Exception as e:
    logging.error(f"❌ Gemini Client initialization failed: {e}")
    gemini_client = None


# ===============================================
# ၃။ MESSAGE HANDLER
# ===============================================

@app.on_message(filters.me & filters.text & filters.command(COMMAND_PREFIX, prefixes=""))
async def gemini_response_handler(client: Client, message: Message):
    """
    UserBot ၏ ကိုယ်ပိုင်မက်ဆေ့ခ်ျများကို စောင့်ကြည့်ပြီး Gemini API မှတဆင့် တုံ့ပြန်သည်။
    """
    
    if not gemini_client:
        await message.edit("❌ Gemini Client စတင်၍ မရပါ။ API Key ကို စစ်ဆေးပါ။")
        return

    # Extract prompt
    full_command = message.text.split(maxsplit=1)
    if len(full_command) < 2:
        await message.edit(f"❓ **အသုံးပြုပုံ:** `{COMMAND_PREFIX[0]} မေးခွန်း`")
        return
    
    prompt = full_command[1].strip()

    # Inform user (edit the original message)
    try:
        await message.edit("🧠 **Thinking...**")
    except FloodWait as e:
        logging.warning(f"FloodWait on edit: Retrying after {e.value} seconds.")
        await asyncio.sleep(e.value)
        await message.edit("🧠 **Thinking...**") 

    
    # Call Gemini API
    try:
        response = gemini_client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )

        ai_response = response.text
        
        # Final response formatting
        final_response = f"**Query:** `{prompt}`\n\n---\n\n{ai_response}"

        # Send final response
        await message.edit(final_response, parse_mode="markdown")

    except Exception as e:
        error_message = f"🚫 Gemini API ခေါ်ဆိုမှုတွင် အမှားဖြစ်ပွား: `{type(e).__name__}: {e}`"
        logging.error(error_message)
        
        # Edit the message back to show the error
        try:
            await message.edit(error_message)
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            await message.edit(error_message)


# ===============================================
# ၄။ STARTUP
# ===============================================

if __name__ == "__main__":
    logging.info(f"🚀 Gemini UserBot ({MODEL_NAME}) is starting...")
    app.run()
    logging.info("👋 UserBot stopped.")
  
