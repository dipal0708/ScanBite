from fastapi import FastAPI
from app.routers import analyze, agent

app = FastAPI(title="LabelWise AI Service")

app.include_router(analyze.router)
app.include_router(agent.router)


@app.get("/health")
def health():
    return {"status": "ok"}
