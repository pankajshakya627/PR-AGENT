## model =  "xiaomi/mimo-v2-flash:free"

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def verify_model():
    try:
        completion = client.chat.completions.create(
            model="xiaomi/mimo-v2-flash:free",
            messages=[
                {"role": "user", "content": "Say 'Model is working'"}
            ],
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    verify_model()
