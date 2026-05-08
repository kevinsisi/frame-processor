from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import adjustments, exports, photos, processing_jobs, projects
from api.routers import settings as settings_router

APP_VERSION = "0.3.11"

app = FastAPI(title="frame-processor API", version=APP_VERSION)

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
app.include_router(settings_router.router)
app.include_router(adjustments.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "frame-processor", "version": APP_VERSION}
