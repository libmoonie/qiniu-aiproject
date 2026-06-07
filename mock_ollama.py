import json
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/api/chat", methods=["POST"])
def chat():
    # Return a payload where message.content is a JSON string (as Ollama might)
    sample = {
        "reply": "Sure — tell me more.",
        "corrections": [
            {
                "issue": "Missing article before noun",
                "suggestion": "I have a cat.",
                "explanation": "Use the indefinite article 'a' before a singular countable noun.",
                "severity": "minor",
            },
            {
                "issue": "Incorrect verb form",
                "suggestion": "He goes to school every day.",
                "explanation": "Use 'goes' for third-person singular subjects.",
                "severity": "major",
            },
        ],
    }

    return jsonify({"message": {"content": json.dumps(sample)}})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=11434)
