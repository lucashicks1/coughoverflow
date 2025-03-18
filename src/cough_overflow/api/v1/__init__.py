"""Routes module."""

from fastapi import APIRouter

from .analysis import router as analysis_router
from .health import router as health_router
from .labs import router as labs_router
from .patients import router as patients_router

r = router = APIRouter()

router.include_router(analysis_router, prefix="/analysis")
router.include_router(health_router, prefix="/health")
router.include_router(labs_router, prefix="/labs")
router.include_router(patients_router, prefix="/patients")
