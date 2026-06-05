from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.services import share_service

router = APIRouter(prefix="/api", tags=["share"])


class ShareRequest(BaseModel):
    line_ids: list[int]
    clip_ids: list[str] | None = None


@router.post("/share")
def create_share(body: ShareRequest):
    return share_service.create_share(body.line_ids, body.clip_ids)


@router.get("/share/{share_id}")
def get_share(share_id: str):
    data = share_service.get_share(share_id)
    if not data:
        return {"error": "not_found"}
    return data
