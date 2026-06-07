import json
import os
import re
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

CORRECTION_PROMPT = """After each user message, first reply as the conversation partner in English (1-3 short sentences). Then on a new line, provide only a JSON object with these fields:
{
    "reply": "<assistant reply>",
    "corrections": [
        {
            "issue": "<a concise English sentence describing the grammatical or expression issue>",
            "suggestion": "<a complete English sentence preserving the user's meaning with corrected grammar and natural phrasing>",
            "explanation": "<one short English sentence explaining why the original is incorrect>",
            "severity": "<minor|major>"
        }
    ]
}

Instructions for producing the JSON (must follow exactly):
- Be strict and aggressive about finding and reporting any grammatical, lexical, punctuation, or usage issues — including minor ones such as missing/extra articles, wrong prepositions, verb tense, subject-verb agreement, plurality, word order, omitted words, collocations, register, punctuation, and capitalization.
- For each distinct issue, include one object in the "corrections" array with the fields: `issue`, `suggestion`, `explanation`, and `severity`.
- `suggestion` must be a fully corrected sentence that preserves the user's intended meaning and uses natural, idiomatic English.
- `explanation` must be a one-sentence rationale (concise) describing the error.
- `severity` should be "minor" for small stylistic/punctuation or wording choices and "major" for errors that affect correctness or clarity.
- If multiple issues exist, list them all (do not collapse them into a single entry).
- If the sentence is already grammatically correct, still return one suggestion with `issue` set to "Natural phrasing", provide a more idiomatic alternative in `suggestion`, a short `explanation`, and set `severity` to "minor".
- Never praise the user or say "well done" in the JSON — only factual issue objects and suggestions.
- Do not include any extra text outside the single JSON object. Use plain JSON with double quotes.
"""


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

    system_prompt = SCENE_PROMPTS[scene] + "\n\n" + CORRECTION_PROMPT
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
        raw_content = payload.get("message", {}).get("content", "").strip()
        if not raw_content:
            return jsonify({"error": "empty response from ollama"}), 502

        try:
            parsed = json.loads(raw_content)
        except ValueError:
            json_text = re.search(r"\{[\s\S]*\}", raw_content)
            parsed = json.loads(json_text.group(0)) if json_text else {}

        reply = (parsed.get("reply") or raw_content).strip()
        corrections = parsed.get("corrections") if isinstance(parsed.get("corrections"), list) else []
        return jsonify({"reply": reply, "corrections": corrections})
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
