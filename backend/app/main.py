from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db import Base, SessionLocal, engine
from app.seed import seed_demo_data
from app.services.ingestion import MetadataIngestionService

app = FastAPI(title="Living Data DNA Platform API", version="0.1.0")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://helix-dna-frontend-ojug5k4mta-uc.a.run.app",
    "https://helix-dna-frontend-330015043682.us-central1.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    with SessionLocal() as db:
        if settings.demo_seed_enabled:
            seed_demo_data(db)
        if settings.openmetadata_url:
            try:
                await MetadataIngestionService().sync(db)
            except Exception as exc:
                # Keep API alive even if OpenMetadata is still booting.
                print(f"[startup] OpenMetadata sync skipped: {exc}")


app.include_router(router)
