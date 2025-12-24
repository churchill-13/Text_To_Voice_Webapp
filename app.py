from flask import Flask, render_template, request, send_file, jsonify, session
import edge_tts
import asyncio
import os
import time
import uuid
from collections import deque

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

BASE_OUTPUT = "output/sessions"
os.makedirs(BASE_OUTPUT, exist_ok=True)

MAX_FILES_PER_SESSION = 10

DEMO_TEXT = {
    "English": "This is a demo voice preview.",
    "Tamil": "இது ஒரு மாதிரி குரல் முன்னோட்டம்.",
    "Telugu": "ఇది ఒక నమూనా వాయిస్ ప్రివ్యూ.",
    "Hindi": "यह एक नमूना आवाज़ पूर्वावलोकन है।",
    "Chinese": "这是一个示例语音预览。"
}

# ---------- SESSION ----------
def get_session_folder():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
        session["files"] = deque()
    folder = os.path.join(BASE_OUTPUT, session["sid"])
    os.makedirs(folder, exist_ok=True)
    return folder

def cleanup_files():
    while len(session["files"]) > MAX_FILES_PER_SESSION:
        old = session["files"].popleft()
        try:
            os.remove(old)
        except:
            pass

# ---------- ROUTES ----------
@app.route("/")
def index():
    get_session_folder()
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text")
    voice = request.form.get("voice")

    if not text or not voice:
        return "Missing data", 400

    folder = get_session_folder()
    filename = f"gen_{int(time.time())}.mp3"
    path = os.path.join(folder, filename)

    async def tts():
        await edge_tts.Communicate(text=text.strip(), voice=voice).save(path)

    asyncio.run(tts())

    session["files"].append(path)
    cleanup_files()

    return send_file(path, as_attachment=True)

@app.route("/preview", methods=["POST"])
def preview():
    data = request.json
    text = data.get("text")
    voice = data.get("voice")

    folder = get_session_folder()
    filename = f"preview_{int(time.time())}.mp3"
    path = os.path.join(folder, filename)

    async def tts():
        await edge_tts.Communicate(text=text.strip(), voice=voice).save(path)

    asyncio.run(tts())

    session["files"].append(path)
    cleanup_files()

    return jsonify({"audio": f"/audio/{session['sid']}/{filename}"})

@app.route("/demo", methods=["POST"])
def demo():
    data = request.json
    language = data.get("language")
    voice = data.get("voice")

    text = DEMO_TEXT.get(language)
    if not text:
        return jsonify({"error": "Invalid language"}), 400

    folder = get_session_folder()
    filename = f"demo_{int(time.time())}.mp3"
    path = os.path.join(folder, filename)

    async def tts():
        await edge_tts.Communicate(text=text, voice=voice).save(path)

    asyncio.run(tts())

    session["files"].append(path)
    cleanup_files()

    return jsonify({"audio": f"/audio/{session['sid']}/{filename}"})

@app.route("/audio/<sid>/<filename>")
def serve_audio(sid, filename):
    return send_file(os.path.join(BASE_OUTPUT, sid, filename))

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
