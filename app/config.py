"""LESSON 1 - Configuration.

Secrets (API keys) must never be hard-coded or committed to git.
We keep them in a `.env` file and load them into environment variables
with python-dotenv. `os.getenv` then reads them anywhere in the app.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the current working directory

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
# OpenRouter speaks the OpenAI API format, so we reuse OpenAI's client
# and simply point it at OpenRouter's URL.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DB_PATH = os.getenv("DB_PATH", "chat.db")
