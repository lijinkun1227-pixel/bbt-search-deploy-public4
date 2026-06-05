from __future__ import annotations

from apps.api.db import get_conn
from apps.api.services.clip_service import get_clip


def get_featured(limit: int = 9) -> list[dict]:
    limit = min(max(limit, 1), 20)
    items: list[dict] = []

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sl.id, e.season, e.episode, sl.start_ms, sl.end_ms,
                   sl.text_en, sl.text_zh, ca.id::text AS clip_id
            FROM clip_assets ca
            JOIN subtitle_lines sl ON sl.id = ca.subtitle_line_id
            JOIN episodes e ON e.id = sl.episode_id
            WHERE ca.status = 'ready'
            ORDER BY random()
            LIMIT %s
            """,
            (limit,),
        )
        clip_rows = cur.fetchall()

        seen_line_ids = set()
        for row in clip_rows:
            line_id, season, episode, start_ms, end_ms, text_en, text_zh, clip_id = row
            seen_line_ids.add(line_id)
            clip = get_clip(clip_id) if clip_id else {}
            items.append(
                {
                    "line_id": line_id,
                    "season": season,
                    "episode": episode,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text_en": text_en,
                    "text_zh": text_zh,
                    "has_clip": True,
                    "clip_id": clip_id,
                    "play_url": clip.get("play_url"),
                    "thumbnail_url": clip.get("thumbnail_url"),
                }
            )

        remaining = limit - len(items)
        if remaining > 0:
            exclude = tuple(seen_line_ids) if seen_line_ids else (-1,)
            cur.execute(
                """
                SELECT sl.id, e.season, e.episode, sl.start_ms, sl.end_ms,
                       sl.text_en, sl.text_zh,
                       EXISTS (
                         SELECT 1 FROM clip_assets ca
                         WHERE ca.subtitle_line_id = sl.id AND ca.status = 'ready'
                       ) AS has_clip
                FROM subtitle_lines sl
                JOIN episodes e ON e.id = sl.episode_id
                WHERE sl.id NOT IN %s
                ORDER BY random()
                LIMIT %s
                """,
                (exclude, remaining),
            )
            for row in cur.fetchall():
                line_id, season, episode, start_ms, end_ms, text_en, text_zh, has_clip = row
                item = {
                    "line_id": line_id,
                    "season": season,
                    "episode": episode,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text_en": text_en,
                    "text_zh": text_zh,
                    "has_clip": has_clip,
                    "clip_id": None,
                    "play_url": None,
                }
                if has_clip:
                    cur.execute(
                        """
                        SELECT id::text FROM clip_assets
                        WHERE subtitle_line_id = %s AND status = 'ready'
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (line_id,),
                    )
                    cid_row = cur.fetchone()
                    if cid_row:
                        clip = get_clip(cid_row[0])
                        item["clip_id"] = cid_row[0]
                        item["play_url"] = clip.get("play_url")
                        item["thumbnail_url"] = clip.get("thumbnail_url")
                items.append(item)

    return items
