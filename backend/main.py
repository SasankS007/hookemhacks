from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stroke, rally

app = FastAPI(title="PicklePro API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stroke.router, prefix="/api/stroke", tags=["stroke"])
app.include_router(rally.router, prefix="/api/rally", tags=["rally"])
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "picklepro-api"}
