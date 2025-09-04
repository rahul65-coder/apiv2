import os
import json
import requests
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify
import threading

# 🔐 Firebase credentials from environment variable
firebase_key = os.getenv("FIREBASE_KEY")
if not firebase_key:
    raise ValueError("FIREBASE_KEY environment variable is missing!")

firebase_key_json = json.loads(firebase_key)

cred = credentials.Certificate(firebase_key_json)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://web-admin-e297c-default-rtdb.asia-southeast1.firebasedatabase.app'
})

ref = db.reference("satta")

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
last_status = {"status": "Initializing...", "last_update": None, "api_status": None}

# ✅ Browser-like headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://draw.ar-lottery01.com/",
    "Origin": "https://draw.ar-lottery01.com",
    "Connection": "keep-alive"
}

def get_size_label(number):
    return "SMALL" if number <= 4 else "BIG"

def fetch_and_save():
    global last_status
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        api_status_code = response.status_code
        raw_text = response.text.strip()

        if not raw_text:
            last_status = {
                "status": "❌ Fetch error: Empty response from API",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "api_status": api_status_code
            }
            return

        data = response.json()
        items = data["data"]["list"][:10]

        for item in items:
            issue = f"period{item['issueNumber']}"
            number = int(item["number"])
            size = get_size_label(number)
            color = item["color"]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if ref.child(issue).get() is None:
                ref.child(issue).set({
                    "number": number,
                    "type": size,
                    "color": color,
                    "timestamp": timestamp
                })
                last_status = {
                    "status": f"✅ Saved: {issue} → {number} ({size}) {color}",
                    "last_update": timestamp,
                    "api_status": api_status_code
                }
            else:
                last_status = {
                    "status": f"⚠️ Skipped (exists): {issue}",
                    "last_update": timestamp,
                    "api_status": api_status_code
                }

    except Exception as e:
        last_status = {
            "status": f"❌ Fetch error: {str(e)}",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_status": None
        }

def exact_one_minute_loop():
    while True:
        start_time = datetime.now()
        fetch_and_save()
        next_minute = (start_time + timedelta(minutes=1)).replace(second=0, microsecond=0)
        sleep_duration = (next_minute - datetime.now()).total_seconds()
        if sleep_duration > 0:
            time.sleep(sleep_duration)

# ✅ Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
      <head><title>Bot Status</title></head>
      <body style='font-family: Arial; text-align: center; margin-top: 50px;'>
        <h1 style='color: green;'>✅ Bot Chal Raha Hai</h1>
        <p>
          Status check: <a href='/status'>/status</a> |
          Manual fetch: <a href='/fetch-now'>/fetch-now</a> |
          Debug: <a href='/debug'>/debug</a>
        </p>
      </body>
    </html>
    """

@app.route("/status")
def status():
    return jsonify(last_status)

@app.route("/fetch-now")
def fetch_now():
    fetch_and_save()
    return jsonify({"message": "Manual fetch triggered", "status": last_status})

@app.route("/debug")
def debug():
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        return jsonify({
            "status_code": response.status_code,
            "response_length": len(response.text),
            "preview": response.text[:300]
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Start background thread
threading.Thread(target=exact_one_minute_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
