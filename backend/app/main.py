"""DataCheck Web - FastAPI Application Entry Point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import create_tables
from app.services.scheduler_service import start_scheduler, shutdown_scheduler
from app.api import (
    auth_router,
    admin_router,
    dba_router,
    chat_router,
    feedback_router,
)

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    create_tables()
    start_scheduler()
    logging.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado con éxito.")
    yield
    # Shutdown
    shutdown_scheduler()
    logging.info("🛑 DataCheck API detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(dba_router, prefix="/dba", tags=["dba"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])


@app.get("/", summary="Root status")
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/healthz", summary="Health check endpoint")
async def healthz():
    return {"status": "ok"}
