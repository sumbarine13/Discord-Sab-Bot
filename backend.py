from flask import Flask, request, jsonify, send_from_directory
import threading
import subprocess
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
PASSWORD = "Sumbarine13"
BOT_SCRIPT = "bot.py"  # Your Discord bot script
bot_process = None
lock = threading.Lock()

# =========================
# SERVE HTML
# =========================
@app.route("/")
def index():
    return send_from_directory(".", "control_panel.html")


# =========================
# CONTROL ENDPOINTS
# =========================
@app.route("/start", methods=["POST"])
def start_bot():
    global bot_process
    pw = request.form.get("password") or request.args.get("password")
    if pw != PASSWORD:
        return jsonify({"status": "error", "message": "Wrong password"}), 403

    with lock:
        if bot_process and bot_process.poll() is None:
            return jsonify({"status": "error", "message": "Bot is already running"}), 400

        bot_process = subprocess.Popen(["python", BOT_SCRIPT])
        return jsonify({"status": "success", "message": "Bot started"})


@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_process
    pw = request.form.get("password") or request.args.get("password")
    if pw != PASSWORD:
        return jsonify({"status": "error", "message": "Wrong password"}), 403

    with lock:
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
            bot_process = None
            return jsonify({"status": "success", "message": "Bot stopped"})
        else:
            return jsonify({"status": "error", "message": "Bot is not running"}), 400


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
