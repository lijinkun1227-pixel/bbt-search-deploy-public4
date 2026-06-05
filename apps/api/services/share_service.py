from __future__ import annotations

import json
import uuid

from apps.api.db import get_conn
from apps.api.services.clip_service import get_clip
def create_share(line_ids: list[int], clip_ids: list[str] | None = None) -> dict:
    share_id = str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO share_bundles (id, line_ids, clip_ids)
            VALUES (%s, %s, %s)
            """,
            (share_id, json.dumps(line_ids), json.dumps(clip_ids or [])),
        )
        conn.commit()
    return {
        "share_id": share_id,
        "url": f"/s/{share_id}",
    }


def get_share(share_id: str) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT line_ids, clip_ids, created_at FROM share_bundles WHERE id = %s",
            (share_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        line_ids = json.loads(row[0])
        clip_ids = json.loads(row[1] or "[]")
        cur.execute(
            """
            SELECT sl.id, e.season, e.episode, sl.start_ms, sl.end_ms, sl.text_en, sl.text_zh
            FROM subtitle_lines sl
            JOIN episodes e ON e.id = sl.episode_id
            WHERE sl.id = ANY(%s)
            ORDER BY sl.id
            """,
            (line_ids,),
        )
        lines = cur.fetchall()

    items = []
    for lid, s, ep, start_ms, end_ms, text_en, text_zh in lines:
        items.append(
            {
                "line_id": lid,
                "season": s,
                "episode": ep,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text_en": text_en,
                "text_zh": text_zh,
            }
        )
    clips = [get_clip(cid) for cid in clip_ids if cid]
    return {
        "share_id": share_id,
        "items": items,
        "clips": clips,
        "created_at": row[2].isoformat() if row[2] else None,
    }
