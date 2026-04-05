from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging.config import configure_logging, get_logger
from app.logging.middleware import RequestLoggingMiddleware
from app.routers import auth, jobs, public_jobs
from app.utils.exceptions import AppException

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
    log = get_logger(__name__)
    log.info("app.startup", env_db=settings.DATABASE_URL.split("///")[-1])
    yield
    log.info("app.shutdown")


app = FastAPI(
    title="Job Listing API",
    version="1.0.0",
    description="REST API for the Job Listing web application. Swagger UI is at /docs.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — origins are configured via CORS_ORIGINS env var (comma-separated)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/response logging
app.add_middleware(RequestLoggingMiddleware)


# Single exception handler for all domain errors
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(public_jobs.router)
