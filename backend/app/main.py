from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers import applications, extract


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Phase 1 convenience: create tables on startup.
    # Swap for Alembic migrations once the schema starts changing.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="JobTrail API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(extract.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
