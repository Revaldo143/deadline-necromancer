"""Start Deadline Necromancer:  python run.py"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    print(f"⚰️  Deadline Necromancer → http://{settings.HOST}:{settings.PORT}")
    print(f"   Model: {settings.MODEL} via Ollama at {settings.OLLAMA_HOST}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
