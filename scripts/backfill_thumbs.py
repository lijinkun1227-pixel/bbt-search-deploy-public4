#!/usr/bin/env python3
"""为已有 ready 的 clip 补生成缩略图。用法: python scripts/backfill_thumbs.py"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "deploy" / ".env")

from supabase import create_client

from apps.api.config import settings
from apps.api.db import get_conn
from apps.api.services.clip_service import _public_play_url, _resolve_video_path

def main() -> None:
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    bucket = settings.supabase_storage_bucket

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ca.id::text, sl.start_ms, sl.end_ms, e.season, e.episode, e.source_video_path
            FROM clip_assets ca
            JOIN subtitle_lines sl ON sl.id = ca.subtitle_line_id
            JOIN episodes e ON e.id = sl.episode_id
            WHERE ca.status = 'ready'
            """
        )
        rows = cur.fetchall()

    ok = 0
    for clip_id, start_ms, end_ms, season, episode, source_path in rows:
        thumb_key = f"thumbs/{clip_id}.jpg"
        video = _resolve_video_path(source_path, season, episode)
        if not video:
            print(f"skip {clip_id}: no video")
            continue
        mid = ((start_ms + end_ms) / 2) / 1000.0
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp) / "t.jpg"
            cmd = [
                "ffmpeg", "-y", "-ss", str(mid), "-i", str(video),
                "-vframes", "1", "-q:v", "2", str(thumb),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except Exception as e:
                print(f"fail {clip_id}: {e}")
                continue
            if not thumb.exists():
                continue
            sb.storage.from_(bucket).upload(
                thumb_key,
                thumb.read_bytes(),
                file_options={"content-type": "image/jpeg", "upsert": "true"},
            )
            print(f"ok {clip_id} -> {_public_play_url(thumb_key)}")
            ok += 1
    print(f"Done. {ok}/{len(rows)} thumbnails.")


if __name__ == "__main__":
    main()
