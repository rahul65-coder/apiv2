import os
import json
import requests
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify
import threading

# 🔐 Firebase credentials from environment variables (NO FILE)
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
last_status = {"status": "Initializing...", "last_update": None}

def get_size_label(number):
    return "SMALL" if number <= 4 else "BIG"

def fetch_and_save():
    global last_status
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        items = data["data"]["list"][:10]

        for item in items:
            issue = str(item["issueNumber"])
            number = int(item["number"])
            size = get_size_label(number)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if ref.child(issue).get() is None:
                ref.child(issue).set({
                    "result_number": number,
                    "type": size,
                    "timestamp": timestamp
                })
                last_status = {"status": f"✅ Saved: {issue} → {number} ({size})", "last_update": timestamp}
            else:
                last_status = {"status": f"⚠️ Skipped (exists): {issue}", "last_update": timestamp}

    except Exception as e:
        last_status = {"status": f"❌ Fetch error: {str(e)}", "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

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

@app.route("/status")
def status():
    return jsonify(last_status)

@app.route("/fetch-now")
def fetch_now():
    fetch_and_save()
    return jsonify({"message": "Manual fetch triggered", "status": last_status})

# ✅ Start background thread for loop
threading.Thread(target=exact_one_minute_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))