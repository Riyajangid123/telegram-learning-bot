# app.py

from flask import Flask

app = Flask(__name__)

@app.route("/")
def health():
    return "Telegram Learning Bot Running!"