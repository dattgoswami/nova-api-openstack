"""
Shared fixtures for all tests.

Uses an in-memory SQLite database so tests are isolated and fast.
Seeds flavors and images via the same lifespan logic as production.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_openstack_client
from app.infra.openstack.mock_client import MockOpenStackClient
from app.models.flavor import Flavor
from app.models.image import Image

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# --- Fixtures ---


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seed_flavors(test_session: AsyncSession) -> list[Flavor]:
    flavors = [
        Flavor(id=str(uuid.uuid4()), name="m1.tiny", vcpus=1, ram_mb=512, disk_gb=1),
        Flavor(id=str(uuid.uuid4()), name="m1.small", vcpus=1, ram_mb=2048, disk_gb=20),
        Flavor(id=str(uuid.uuid4()), name="m1.large", vcpus=4, ram_mb=8192, disk_gb=80),
    ]
    for f in flavors:
        test_session.add(f)
    await test_session.commit()
    return flavors


@pytest_asyncio.fixture(scope="function")
async def seed_images(test_session: AsyncSession) -> list[Image]:
    images = [
        Image(
            id=str(uuid.uuid4()),
            name="Ubuntu 22.04 LTS",
            os_distro="ubuntu",
            min_disk_gb=8,
            size_bytes=2361393152,
            status="active",
        ),
        Image(
            id=str(uuid.uuid4()),
            name="Debian 12",
            os_distro="debian",
            min_disk_gb=8,
            size_bytes=1073741824,
            status="active",
        ),
    ]
    for i in images:
        test_session.add(i)
    await test_session.commit()
    return images


@pytest_asyncio.fixture(scope="function")
async def client(
    test_session: AsyncSession,
    seed_flavors: list[Flavor],
    seed_images: list[Image],
) -> AsyncGenerator[AsyncClient, None]:
    """Return an HTTPX AsyncClient wired to the test app with an in-memory DB."""
    from app.main import create_app

    test_app = create_app()

    # Override DB session dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    # Override OpenStack client dependency — no type annotations to avoid FastAPI inspection
    async def override_get_openstack_client():  # type: ignore[no-untyped-def]
        return MockOpenStackClient(test_session)

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_openstack_client] = override_get_openstack_client

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest.fixture
def flavor_id(seed_flavors: list[Flavor]) -> str:
    return seed_flavors[0].id


@pytest.fixture
def flavor_id_2(seed_flavors: list[Flavor]) -> str:
    return seed_flavors[1].id


@pytest.fixture
def image_id(seed_images: list[Image]) -> str:
    return seed_images[0].id
