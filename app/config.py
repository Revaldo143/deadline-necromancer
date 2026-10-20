"""Runtime configuration for Deadline Necromancer.

Everything is driven by environment variables so the same code runs on a
laptop demo, a Render deploy, or CI without edits. See `.env.example`.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


class Settings:
    # Ollama (local, open-weight models). The app NEVER calls a cloud LLM.
    OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    MODEL: str = os.environ.get("NECRO_MODEL", "gemma3:12b")
    OLLAMA_TIMEOUT: float = float(os.environ.get("OLLAMA_TIMEOUT", "300"))
    OLLAMA_HEALTH_TIMEOUT: float = float(os.environ.get("OLLAMA_HEALTH_TIMEOUT", "3"))

    # Scanning
    DEFAULT_SCAN_PATH: str = os.environ.get(
        "DEFAULT_SCAN_PATH", str(Path.home() / "projects")
    )
    MAX_SCAN_DEPTH: int = int(os.environ.get("MAX_SCAN_DEPTH", "3"))

    # Server
    HOST: str = os.environ.get("HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("PORT", "8000"))


settings = Settings()
