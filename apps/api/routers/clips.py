from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.api.services import clip_service

router = APIRouter(prefix="/api", tags=["clips"])


class ClipRequest(BaseModel):
    line_ids: list[int] = Field(..., min_length=1)
    padding_ms: int = 500


@router.post("/clips")
def create_clips(body: ClipRequest):
    jobs = clip_service.create_clips(body.line_ids, body.padding_ms)
    return {"jobs": jobs}


@router.get("/clips/{clip_id}")
def get_clip(clip_id: str):
    clip = clip_service.get_clip(clip_id)
    if not clip:
        return {"error": "not_found"}
    return clip
