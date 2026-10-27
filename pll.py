import os
import re
import unittest
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
API_URL = "https://openrouter.ai/api/v1/chat/completions"


# 1. PII DATA SANITIZATION AND MASKING

def sanitize_pii(text):
    """Mask common sensitive identifiers before AI processing."""

    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    # Mask email addresses
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL]",
        text,
    )

    # Mask PAN numbers
    text = re.sub(
        r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "[PAN]",
        text,
        flags=re.IGNORECASE,
    )

    # Mask Aadhaar-like 12-digit numbers
    text = re.sub(
        r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)",
        "[AADHAAR]",
        text,
    )

    # Mask Indian mobile numbers
    text = re.sub(
        r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
        "[PHONE]",
        text,
    )

    return text


# 2. OPENROUTER API INTEGRATION

def ask_openrouter(sanitized_text):
    """Send sanitized text to OpenRouter."""

    if not API_KEY:
        raise RuntimeError(
            "API key missing. Add OPENROUTER_API_KEY to your .env file."
        )

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an HRMS support assistant. "
                        "Answer employee questions clearly. "
                        "Do not guess masked personal information."
                    ),
                },
                {
                    "role": "user",
                    "content": sanitized_text,
                },
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"OpenRouter API failed with HTTP {response.status_code}. "
            "Check your API key, model availability, and account limits."
        )

    data = response.json()
    choices = data.get("choices", [])

    if not choices:
        raise RuntimeError("No answer returned by OpenRouter.")

    answer = choices[0].get("message", {}).get("content")

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("OpenRouter returned an empty answer.")

    return answer.strip()


# 3. AUTOMATED TESTING

class TestPIICleansing(unittest.TestCase):

    def test_email(self):
        self.assertEqual(
            sanitize_pii("Email: ravi@gmail.com"),
            "Email: [EMAIL]",
        )

    def test_phone(self):
        self.assertEqual(
            sanitize_pii("Phone: 9876543210"),
            "Phone: [PHONE]",
        )

    def test_pan(self):
        self.assertEqual(
            sanitize_pii("PAN: ABCDE1234F"),
            "PAN: [PAN]",
        )

    def test_aadhaar(self):
        self.assertEqual(
            sanitize_pii("ID: 1234 5678 9012"),
            "ID: [AADHAAR]",
        )

    def test_multiple_pii(self):
        result = sanitize_pii(
            "ravi@gmail.com 9876543210 ABCDE1234F"
        )
        self.assertNotIn("akhi@gmail.com", result)
        self.assertNotIn("9876543210", result)
        self.assertNotIn("ABCDE1234F", result)

    def test_normal_text(self):
        text = "How can I check my leave balance?"
        self.assertEqual(sanitize_pii(text), text)

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            sanitize_pii(None)


# 4. MAIN APPLICATION

def main():
    print("=" * 45)
    print("DAY 42 - PII DATA CLEANSING")
    print("PII Masking + OpenRouter Integration")
    print("=" * 45)

    while True:
        try:
            user_input = input(
                "\nEnter HRMS question, 'test', or 'exit': "
            ).strip()

            if user_input.lower() == "exit":
                print("Application closed.")
                break

            if user_input.lower() == "test":
                suite = unittest.defaultTestLoader.loadTestsFromTestCase(
                    TestPIICleansing
                )
                result = unittest.TextTestRunner(verbosity=2).run(suite)
                print(
                    "All tests passed."
                    if result.wasSuccessful()
                    else "Some tests failed."
                )
                continue

            if not user_input:
                print("Please enter some text.")
                continue

            # Always sanitize before sending data externally
            sanitized_text = sanitize_pii(user_input)

            print("\nSanitized input:")
            print(sanitized_text)

            answer = ask_openrouter(sanitized_text)

            print("\nOpenRouter AI response:")
            print(answer)

        except (requests.RequestException, ValueError, RuntimeError) as exc:
            print(f"Error: {exc}")
        except KeyboardInterrupt:
            print("\nApplication stopped.")
            break


if __name__ == "__main__":
    main()