import requests
import time
import sys

# User provided token
TOKEN = "8552870041:AAE66aBCQjeQYRDMf61CHKyPe0DWm8-hXdw"
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

print(f"Bot token: {TOKEN[:5]}...{TOKEN[-5:]}")
print("Mesaj bekleniyor... Lütfen bota gidip /start yazın.")

# 60 saniye boyunca deneyecek
for i in range(12): 
    try:
        response = requests.get(URL)
        data = response.json()
        
        if data["ok"] and data["result"]:
            # Son mesajı al
            last_update = data["result"][-1]
            chat_id = last_update["message"]["chat"]["id"]
            user_name = last_update["message"]["from"].get("first_name", "User")
            
            print(f"\nBAŞARILI! Chat ID bulundu: {chat_id}")
            print(f"Kullanıcı: {user_name}")
            
            # Save token and chat_id to a config file
            with open("config.py", "w", encoding="utf-8") as f:
                f.write(f'TELEGRAM_TOKEN = "{TOKEN}"\n')
                f.write(f'TELEGRAM_CHAT_ID = "{chat_id}"\n')
            
            print("\nconfig.py dosyası oluşturuldu.")
            break
        else:
            print(".", end="", flush=True)
            time.sleep(5)
    except Exception as e:
        print(f"Hata: {e}")
        time.sleep(5)
else:
    print("\nZaman aşımı. Bot'a mesaj attığınızdan emin olun.")
