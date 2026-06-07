import json
from unittest.mock import patch

import backend.app as backend_module


mock_payload = {
    "message": {
        "content": json.dumps(
            {
                "reply": "Sure — tell me more.",
                "corrections": [
                    {
                        "issue": "Missing article before noun",
                        "suggestion": "I have a cat.",
                        "explanation": "Use the indefinite article 'a' before a singular countable noun.",
                        "severity": "minor",
                    }
                ],
            }
        )
    }
}


class MockResp:
    def raise_for_status(self):
        return None

    def json(self):
        return mock_payload


def run_test():
    with patch("backend.app.requests.post", return_value=MockResp()):
        app = backend_module.app
        client = app.test_client()
        res = client.post(
            "/api/chat",
            json={"message": "I have pen", "history": [], "scene": "interview"},
        )
        print("Status:", res.status_code)
        print("Body:", res.get_data(as_text=True))


if __name__ == "__main__":
    run_test()
