from pathlib import Path
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, engine
from app.routes.application_routes import router as application_router
from app.routes.auth_routes import router as auth_router
from app.routes.interview_routes import router as interview_router
from app.routes.job_routes import router as job_router
from app.routes.system_routes import router as system_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables ensured.")
        except Exception:
            logger.exception("Failed to auto-create database tables at startup.")
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(job_router)
app.include_router(application_router)
app.include_router(interview_router)
app.include_router(system_router)

frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")


@app.get("/", include_in_schema=False)
def home():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "ATS API is running"}


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check():
    return {"status": "ok"}
