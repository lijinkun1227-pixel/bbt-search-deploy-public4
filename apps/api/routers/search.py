from fastapi import APIRouter, Query

from apps.api.services import search_service

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def api_search(
    q: str = Query(..., min_length=1),
    lang: str = Query("both"),
    season: int | None = None,
    episode: int | None = None,
    page: int = 1,
    page_size: int = 20,
    whole_word: bool = True,
):
    return search_service.search(q, lang, season, episode, page, page_size, whole_word)
