from __future__ import annotations

import re
from html import escape

from apps.api.db import get_conn

# 纯英文短词默认整词匹配，避免 hi → this/history
_ASCII_WORD = re.compile(r"^[a-zA-Z][a-zA-Z'\-]*$")


def _is_english_word_query(q: str) -> bool:
    q = q.strip()
    return len(q) >= 1 and bool(_ASCII_WORD.match(q))


def _word_regex(q: str) -> str:
    """PostgreSQL 正则整词边界 \\y"""
    return rf"\y{re.escape(q.strip())}\y"


def _build_text_condition(lang: str, q: str, whole_word: bool) -> tuple[str, list]:
    """返回 SQL 片段与参数。whole_word 仅对英文生效。"""
    params: list = []
    parts: list[str] = []
    use_word = whole_word and _is_english_word_query(q)

    if use_word:
        pattern = _word_regex(q)
        if lang == "en":
            parts.append("sl.text_en ~* %s")
            params.append(pattern)
        elif lang == "zh":
            parts.append("sl.text_zh ILIKE %s")
            params.append(f"%{q}%")
        else:
            parts.append("(sl.text_en ~* %s OR (sl.text_zh IS NOT NULL AND sl.text_zh ILIKE %s))")
            params.extend([pattern, f"%{q}%"])
    else:
        like = f"%{q}%"
        if lang == "en":
            parts.append("sl.text_en ILIKE %s")
            params.append(like)
        elif lang == "zh":
            parts.append("sl.text_zh ILIKE %s")
            params.append(like)
        else:
            parts.append("(sl.text_en ILIKE %s OR sl.text_zh ILIKE %s)")
            params.extend([like, like])

    return " AND ".join(parts), params


def _highlight(text: str | None, q: str, whole_word: bool) -> str | None:
    if not text or not q:
        return None
    escaped = escape(text)
    if whole_word and _is_english_word_query(q):
        pattern = re.compile(rf"\b({re.escape(q)})\b", re.IGNORECASE)
    else:
        pattern = re.compile(re.escape(q), re.IGNORECASE)
    return pattern.sub(lambda m: f"<em>{m.group(1) if m.lastindex else m.group(0)}</em>", escaped)


def search(
    q: str,
    lang: str = "both",
    season: int | None = None,
    episode: int | None = None,
    page: int = 1,
    page_size: int = 20,
    whole_word: bool = True,
) -> dict:
    q = q.strip()
    page_size = min(max(page_size, 1), 50)
    page = max(page, 1)
    offset = (page - 1) * page_size

    text_cond, params = _build_text_condition(lang, q, whole_word)
    conditions = [text_cond]
    if season is not None:
        conditions.append("e.season = %s")
        params.append(season)
    if episode is not None:
        conditions.append("e.episode = %s")
        params.append(episode)

    where = " AND ".join(conditions)
    count_sql = f"""
        SELECT COUNT(*) FROM subtitle_lines sl
        JOIN episodes e ON e.id = sl.episode_id
        WHERE {where}
    """
    data_sql = f"""
        SELECT sl.id, e.season, e.episode, sl.start_ms, sl.end_ms,
               sl.text_en, sl.text_zh, sl.align_confidence,
               EXISTS (
                 SELECT 1 FROM clip_assets ca
                 WHERE ca.subtitle_line_id = sl.id AND ca.status = 'ready'
               ) AS has_clip
        FROM subtitle_lines sl
        JOIN episodes e ON e.id = sl.episode_id
        WHERE {where}
        ORDER BY e.season, e.episode, sl.start_ms
        LIMIT %s OFFSET %s
    """

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]
        cur.execute(data_sql, params + [page_size, offset])
        rows = cur.fetchall()

    total_pages = max(1, (total + page_size - 1) // page_size)
    items = []
    for row in rows:
        line_id, s, ep, start_ms, end_ms, text_en, text_zh, align_conf, has_clip = row
        items.append(
            {
                "line_id": line_id,
                "season": s,
                "episode": ep,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text_en": text_en,
                "text_zh": text_zh,
                "align_confidence": align_conf,
                "snippet_en": _highlight(text_en, q, whole_word),
                "snippet_zh": _highlight(text_zh, q, whole_word) if text_zh else None,
                "has_clip": has_clip,
            }
        )
    return {
        "total": total,
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "whole_word": whole_word and _is_english_word_query(q),
    }
