from fastapi import APIRouter

from .catalog import router as catalog_router
from .clusters import router as clusters_router
from .questions import router as questions_router

router = APIRouter(prefix="/api/v1")
router.include_router(catalog_router)
router.include_router(questions_router)
# router.include_router(clusters_router)
