import os
import logging
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set. Please set it in your environment variables.")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

def call_llm(prompt: str) -> str:
    """
    Sends a prompt to the Groq LLM (llama3-8b-8192) and returns the response.
    The LLM is prompted to act as a strict AI tutor.
    """
    try:
        logging.info("Calling LLM...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict AI tutor."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
        )
        logging.info("LLM response received")
        return chat_completion.choices[0].message.content
    except Exception:
        return "Temporary issue. Please try again."
