from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    # Runs the Flask server on port 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Starts the Flask server in a separate thread so it doesn't block the bot
    t = Thread(target=run)
    t.start()
