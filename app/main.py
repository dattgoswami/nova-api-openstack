import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.flavor import Flavor
from app.models.image import Image

# Fixed UUIDs for deterministic seed data — never regenerated on restart
SEED_FLAVORS = [
    {
        "id": "11111111-0000-0000-0000-000000000001",
        "name": "m1.tiny",
        "vcpus": 1,
        "ram_mb": 512,
        "disk_gb": 1,
    },
    {
        "id": "11111111-0000-0000-0000-000000000002",
        "name": "m1.small",
        "vcpus": 1,
        "ram_mb": 2048,
        "disk_gb": 20,
    },
    {
        "id": "11111111-0000-0000-0000-000000000003",
        "name": "m1.medium",
        "vcpus": 2,
        "ram_mb": 4096,
        "disk_gb": 40,
    },
    {
        "id": "11111111-0000-0000-0000-000000000004",
        "name": "m1.large",
        "vcpus": 4,
        "ram_mb": 8192,
        "disk_gb": 80,
    },
    {
        "id": "11111111-0000-0000-0000-000000000005",
        "name": "m1.xlarge",
        "vcpus": 8,
        "ram_mb": 16384,
        "disk_gb": 160,
    },
]

SEED_IMAGES = [
    {
        "id": "22222222-0000-0000-0000-000000000001",
        "name": "Ubuntu 22.04 LTS",
        "os_distro": "ubuntu",
        "min_disk_gb": 8,
        "size_bytes": 2361393152,
        "status": "active",
    },
    {
        "id": "22222222-0000-0000-0000-000000000002",
        "name": "Debian 12",
        "os_distro": "debian",
        "min_disk_gb": 8,
        "size_bytes": 1073741824,
        "status": "active",
    },
    {
        "id": "22222222-0000-0000-0000-000000000003",
        "name": "CentOS Stream 9",
        "os_distro": "centos",
        "min_disk_gb": 10,
        "size_bytes": 1610612736,
        "status": "active",
    },
    {
        "id": "22222222-0000-0000-0000-000000000004",
        "name": "Fedora 39",
        "os_distro": "fedora",
        "min_disk_gb": 8,
        "size_bytes": 1879048192,
        "status": "active",
    },
]

_start_time: float = 0.0


async def seed_data() -> None:
    logger = logging.getLogger(__name__)
    async with AsyncSessionLocal() as session:
        # Seed flavors if empty
        result = await session.execute(select(Flavor).limit(1))
        if result.scalar_one_or_none() is None:
            for flavor_data in SEED_FLAVORS:
                session.add(Flavor(**flavor_data))
            logger.info("Seed flavors inserted", extra={"count": len(SEED_FLAVORS)})

        # Seed images if empty
        result = await session.execute(select(Image).limit(1))
        if result.scalar_one_or_none() is None:
            for image_data in SEED_IMAGES:
                session.add(Image(**image_data))
            logger.info("Seed images inserted", extra={"count": len(SEED_IMAGES)})

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _start_time
    logger = logging.getLogger(__name__)

    logger.info(
        "Application starting",
        extra={"version": settings.app_version, "env": settings.env, "debug": settings.debug},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    await seed_data()

    _start_time = time.monotonic()
    logger.info("Application ready", extra={"version": settings.app_version})

    yield

    logger.info("Application shutting down")
    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API for managing OpenStack VM lifecycle operations. "
            "Implements Nova server terminology with full CRUD and state machine actions."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    from app.api.v1.router import router as v1_router

    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health_check() -> JSONResponse:
        db_status = "healthy"
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            db_status = "unhealthy"

        overall = "healthy" if db_status == "healthy" else "unhealthy"
        uptime = int(time.monotonic() - _start_time) if _start_time else 0

        return JSONResponse(
            status_code=200 if overall == "healthy" else 503,
            content={
                "status": overall,
                "version": settings.app_version,
                "env": settings.env,
                "uptime_s": uptime,
                "checks": {
                    "database": {"status": db_status},
                },
            },
        )

    return app


app = create_app()
