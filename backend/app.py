import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

COMMON_RULES = """Rules:
- Always reply in English only.
- Keep replies short and conversational (1-3 sentences).
- Stay in character for the entire conversation.
- Ask follow-up questions to keep the conversation going."""

SCENE_PROMPTS = {
    "interview": f"""You are an HR interviewer conducting a job interview in English.
Your role: ask about the candidate's background, skills, experience, and motivation.
{COMMON_RULES}
- Ask one clear interview question at a time.
- Be professional but friendly.""",
    "restaurant": f"""You are a restaurant waiter taking orders in English.
Your role: greet the guest, recommend dishes, confirm orders, and handle special requests.
{COMMON_RULES}
- Use natural restaurant phrases (e.g. "What would you like to order?").
- Politely clarify choices when needed.""",
    "meeting": f"""You are a business colleague in an English workplace meeting.
Your role: discuss project updates, share opinions, and collaborate on decisions.
{COMMON_RULES}
- Use professional but natural business English.
- Respond as a peer, not a teacher.""",
    "daily-life": f"""You are a friendly English-speaking friend in a casual daily life conversation.
Your role: chat with the user about everyday topics like hobbies, plans, feelings, and daily experiences.
{COMMON_RULES}
- Be warm, friendly, and informal.
- Talk like a supportive friend, not like a teacher.
- Ask follow-up questions to keep the conversation going.""",
}

DEFAULT_SCENE = "interview"


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []
    scene = (data.get("scene") or DEFAULT_SCENE).strip()
    if scene not in SCENE_PROMPTS:
        return jsonify({"error": f"invalid scene: {scene}"}), 400

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    system_prompt = SCENE_PROMPTS[scene]
    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        reply = payload.get("message", {}).get("content", "").strip()
        if not reply:
            return jsonify({"error": "empty response from ollama"}), 502
        return jsonify({"reply": reply})
    except requests.exceptions.ConnectionError:
        return (
            jsonify(
                {
                    "error": "Cannot connect to Ollama. Please run: ollama serve"
                }
            ),
            503,
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = ""
        if exc.response is not None:
            try:
                detail = exc.response.json().get("error", exc.response.text)
            except ValueError:
                detail = exc.response.text
        return jsonify({"error": f"Ollama error: {detail}"}), status
    except requests.exceptions.Timeout:
        return jsonify({"error": "Ollama request timed out"}), 504
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model": OLLAMA_MODEL, "scenes": list(SCENE_PROMPTS.keys())})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
