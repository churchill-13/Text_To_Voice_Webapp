from flask import Flask, render_template, request, send_file, jsonify, session
import edge_tts
import asyncio
import os
import time
import uuid

app = Flask(__name__)
app.secret_key = "edge-tts-secret-key"

BASE_OUTPUT = "output/sessions"
os.makedirs(BASE_OUTPUT, exist_ok=True)

MAX_FILES_PER_SESSION = 10

DEMO_TEXT = {
    "English": "This is a demo voice preview.",
    "Tamil": "இது ஒரு மாதிரி குரல் முன்னோட்டம்.",
    "Hindi": "यह एक नमूना आवाज़ पूर्वावलोकन है।",
    "Telugu": "ఇది ఒక నమూనా వాయిస్ ప్రివ్యూ.",
    "Chinese": "这是一个示例语音预览。"
}

# ---------------- SESSION ----------------
def get_session_folder():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
        session["files"] = []
    folder = os.path.join(BASE_OUTPUT, session["sid"])
    os.makedirs(folder, exist_ok=True)
    return folder

def cleanup_files():
    files = session.get("files", [])
    while len(files) > MAX_FILES_PER_SESSION:
        old = files.pop(0)
        try:
            os.remove(old)
        except:
            pass
    session["files"] = files

# ---------------- HOME ----------------
@app.route("/")
def index():
    get_session_folder()
    return render_template("index.html")

# ---------------- ASYNC TTS HELPER ----------------
async def generate_tts(text, voice, filepath):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(filepath)

def run_tts(text, voice, filepath):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(generate_tts(text, voice, filepath))
    loop.close()

# ---------------- GENERATE ----------------
@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text")
    voice = request.form.get("voice")

    if not text or not voice:
        return "Missing data", 400

    folder = get_session_folder()
    filename = f"gen_{int(time.time())}.mp3"
    filepath = os.path.join(folder, filename)

    run_tts(text.strip(), voice, filepath)

    session["files"].append(filepath)
    cleanup_files()

    return send_file(filepath, as_attachment=True)

# ---------------- PREVIEW ----------------
@app.route("/preview", methods=["POST"])
def preview():
    data = request.json
    text = data.get("text")
    voice = data.get("voice")

    if not text or not voice:
        return jsonify({"error": "Missing data"}), 400

    folder = get_session_folder()
    filename = f"preview_{int(time.time())}.mp3"
    filepath = os.path.join(folder, filename)

    run_tts(text.strip(), voice, filepath)

    session["files"].append(filepath)
    cleanup_files()

    return jsonify({"audio": f"/audio/{session['sid']}/{filename}"})

# ---------------- DEMO ----------------
@app.route("/demo", methods=["POST"])
def demo():
    data = request.json
    language = data.get("language")
    voice = data.get("voice")

    text = DEMO_TEXT.get(language)
    if not text or not voice:
        return jsonify({"error": "Missing data"}), 400

    folder = get_session_folder()
    filename = f"demo_{int(time.time())}.mp3"
    filepath = os.path.join(folder, filename)

    run_tts(text, voice, filepath)

    session["files"].append(filepath)
    cleanup_files()

    return jsonify({"audio": f"/audio/{session['sid']}/{filename}"})

# ---------------- SERVE AUDIO ----------------
@app.route("/audio/<sid>/<filename>")
def serve_audio(sid, filename):
    return send_file(os.path.join(BASE_OUTPUT, sid, filename))
