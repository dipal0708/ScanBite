from dotenv import load_dotenv
from fastapi import FastAPI

# Load .env before importing the routers because the agent reads its Ollama
# configuration when the module is imported.
load_dotenv()

from app.routers import analyze, agent  # noqa: E402

app = FastAPI(title="LabelWise AI Service")

app.include_router(analyze.router)
app.include_router(agent.router)


@app.get("/health")
def health():
    return {"status": "ok"}
