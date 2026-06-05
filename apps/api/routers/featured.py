from fastapi import APIRouter, Query

from apps.api.services import featured_service

router = APIRouter(prefix="/api", tags=["featured"])


@router.get("/featured")
def api_featured(limit: int = Query(9, ge=1, le=20)):
    return {"items": featured_service.get_featured(limit)}
