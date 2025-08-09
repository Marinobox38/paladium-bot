# keep_alive.py
from flask import Flask
import os

app = Flask("keepalive")

@app.route("/")
def home():
    return "Paladium Bot is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
