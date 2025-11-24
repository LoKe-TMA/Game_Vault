from pyrogram import Client
import os

# Render မှာ သုံးမယ့် API ID နှင့် API HASH ကို ဒီနေရာမှာ ဖြည့်ပါ
API_ID = 1234567 # <--- Replace with your API ID
API_HASH = "your_api_hash" # <--- Replace with your API Hash

if not API_ID or not API_HASH:
    print("API_ID and API_HASH must be set.")
    exit()

print("Pyrogram Client ကို စတင်ပြီး Session String ထုတ်ပေးပါမည်။")
print("ဖုန်းနံပါတ်၊ ကုဒ်နှင့် (2FA ရှိပါက) စကားဝှက်များကို ထည့်သွင်းပါ။")

# Session ကို RAM ထဲမှာသာ သိမ်းပြီး String ထုတ်ပေးရန်
try:
    with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as client:
        session_string = client.export_session_string()
        print("\n" + "="*50)
        print("✅ SUCCESS: Your Pyrogram Session String is Ready:")
        print(session_string)
        print("="*50 + "\n")
        print("💡 ဤ String ကို Render ၏ **SESSION_STRING** Environment Variable တွင် ထည့်သွင်းပါ။")
except SessionPasswordNeeded:
    print("❌ 2FA Password လိုအပ်ပါသည်။")
except Exception as e:
    print(f"❌ Error during session generation: {e}")

