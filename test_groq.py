from dotenv import load_dotenv
from groq import Groq
import os
import json

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("ERROR: GROQ_API_KEY was not found in .env")
    raise SystemExit(1)

try:
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize emails. Return valid JSON with "
                    "the keys summary and priority."
                )
            },
            {
                "role": "user",
                "content": (
                    "Email subject: Assignment deadline. "
                    "Email body: Please submit the assignment by "
                    "Friday at 5 PM."
                )
            }
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=200
    )

    result = json.loads(response.choices[0].message.content)
    print("\nSUCCESS: Groq API responded!")
    print(json.dumps(result, indent=2))

except Exception as error:
    print("\nGroq API test failed.")
    print("Error type:", type(error).__name__)
    print("Details:", str(error)[:1000])
