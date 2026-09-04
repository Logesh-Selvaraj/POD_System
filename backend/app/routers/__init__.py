from app.routers.auth import router as auth_router
from app.routers.deliveries import router as deliveries_router
from app.routers.evidence import router as evidence_router

__all__ = ["auth_router", "deliveries_router", "evidence_router"]
