from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key = os.getenv("HACKCLUB_API_KEY"),
    base_url = "https://ai.hackclub.com/proxy/v1"
)

def send_prompt(prompt):
    response = client.chat.completions.create(
        model = "anthropic/claude-sonnet-5",
        messages = [
            {
                "role": "system",
                "content": (
                    "Write a concise hardware comparison summary using only "
                    "the benchmark facts provided. Never invent scores."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens = 300
    )

    return response.choices[0].message.content