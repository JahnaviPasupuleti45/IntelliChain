import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Read settings such as API keys from a .env file (backend/.env or the repo root),
# so secrets never need to be written in the code.
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"))


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "intellichain.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Used to sign login tokens. Always set a real value outside local development.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    TOKEN_MAX_AGE_SECONDS = 60 * 60 * 8

    # IoT devices send this key in the X-API-Key header
    DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "dev-device-key")

    # LLM keys are optional: without one the app still works, using template reports
    # and returning retrieved SOP sections instead of generated answers.
    # If both are set, Groq is used.
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
    # "embeddings" (local bge-small model via fastembed) or "tfidf" (keyword search)
    RETRIEVER_BACKEND = os.getenv("RETRIEVER_BACKEND", "embeddings")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Tests never call a real LLM, even if a key is in .env
    GROQ_API_KEY = ""
    GEMINI_API_KEY = ""
