from fastapi import APIRouter

from app.api.v1.endpoints import flavors, images, servers

router = APIRouter()

router.include_router(servers.router)
router.include_router(flavors.router)
router.include_router(images.router)
