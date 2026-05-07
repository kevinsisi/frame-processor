from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import exports, photos, processing_jobs, projects

app = FastAPI(title="frame-processor API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(photos.router)
app.include_router(exports.router)
app.include_router(processing_jobs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "frame-processor", "version": "0.2.0"}
