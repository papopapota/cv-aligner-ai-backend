from fastapi import FastAPI

app = FastAPI(
    title="CV Aligner AI Backend",
    description="Hexagonal Architecture Multi-Agent CV Optimizer",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}