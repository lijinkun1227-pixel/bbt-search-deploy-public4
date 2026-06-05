from __future__ import annotations

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path

from supabase import create_client

from apps.api.config import settings
from apps.api.db import get_conn

logger = logging.getLogger(__name__)

VIDEO_EXTS = [".mkv", ".mp4", ".avi", ".mov"]


def _supabase():
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _storage_object_path(storage_path: str) -> str:
    """DB 里存 clips/uuid.mp4；上传/签名都用这个路径。"""
    path = storage_path.strip()
    bucket = settings.supabase_storage_bucket
    if path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1 :]
    return path.lstrip("/")


def _public_play_url(object_path: str) -> str:
    """手动拼接 Public URL，避免 SDK 返回缺少路径前缀。"""
    bucket = settings.supabase_storage_bucket
    base = settings.supabase_url.rstrip("/")
    path = object_path.lstrip("/")
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def _resolve_video_path(source_path: str | None, season: int, episode: int) -> Path | None:
    if source_path and Path(source_path).exists():
        return Path(source_path)
    root = Path(settings.source_video_root)
    for ext in VIDEO_EXTS:
        candidate = root / f"S{season:02d}E{episode:02d}{ext}"
        if candidate.exists():
            return candidate
    return None


def get_clip(clip_id: str) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, status, storage_path, error_message, subtitle_line_id
            FROM clip_assets WHERE id = %s
            """,
            (clip_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    cid, status, storage_path, error_message, line_id = row
    play_url = None
    if status == "ready" and storage_path:
        object_path = _storage_object_path(storage_path)
        # Public 桶：固定用可验证的 public URL（signed 有时会返回错误路径）
        play_url = _public_play_url(object_path)
    thumbnail_url = None
    if status == "ready":
        thumbnail_url = _public_play_url(f"thumbs/{cid}.jpg")

    return {
        "clip_id": str(cid),
        "status": status,
        "play_url": play_url,
        "thumbnail_url": thumbnail_url,
        "error_message": error_message,
        "line_id": line_id,
    }


def _get_or_create_clip_id(line_id: int, padding_ms: int) -> str:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM clip_assets
            WHERE subtitle_line_id = %s AND padding_ms = %s
            """,
            (line_id, padding_ms),
        )
        row = cur.fetchone()
        if row:
            clip_id = str(row[0])
            # 重试时清空旧的失败信息，避免一直卡在 pending/failed
            cur.execute(
                """
                UPDATE clip_assets
                SET status = 'pending', error_message = NULL, updated_at = now()
                WHERE id = %s AND status IN ('pending', 'failed', 'processing')
                """,
                (clip_id,),
            )
            conn.commit()
            return clip_id

        clip_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO clip_assets (id, subtitle_line_id, padding_ms, status, storage_path)
            VALUES (%s, %s, %s, 'pending', NULL)
            """,
            (clip_id, line_id, padding_ms),
        )
        conn.commit()
        return clip_id


def create_clips(line_ids: list[int], padding_ms: int = 500) -> list[dict]:
    jobs = []
    for line_id in line_ids:
        clip_id = _get_or_create_clip_id(line_id, padding_ms)
        existing = get_clip(clip_id)
        if existing and existing.get("status") == "ready":
            existing["line_id"] = line_id
            jobs.append(existing)
            continue

        result = process_clip(clip_id)
        if result:
            result["line_id"] = line_id
        jobs.append(result or get_clip(clip_id))
    return jobs


def get_clip_for_line(line_id: int, padding_ms: int) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM clip_assets
            WHERE subtitle_line_id = %s AND padding_ms = %s
            """,
            (line_id, padding_ms),
        )
        row = cur.fetchone()
    if not row:
        return None
    return get_clip(str(row[0]))


def process_clip(clip_id: str) -> dict:
    logger.info("Processing clip %s", clip_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE clip_assets SET status = 'processing', error_message = NULL, updated_at = now()
            WHERE id = %s
            """,
            (clip_id,),
        )
        cur.execute(
            """
            SELECT sl.start_ms, sl.end_ms, e.season, e.episode, e.source_video_path
            FROM clip_assets ca
            JOIN subtitle_lines sl ON sl.id = ca.subtitle_line_id
            JOIN episodes e ON e.id = sl.episode_id
            WHERE ca.id = %s
            """,
            (clip_id,),
        )
        row = cur.fetchone()
        cur.execute("SELECT padding_ms FROM clip_assets WHERE id = %s", (clip_id,))
        padding_row = cur.fetchone()
        conn.commit()

    if not row or not padding_row:
        return _fail(clip_id, "LINE_NOT_FOUND")

    start_ms, end_ms, season, episode, source_path = row
    padding_ms = padding_row[0]
    video = _resolve_video_path(source_path, season, episode)
    if not video:
        return _fail(clip_id, f"NO_SOURCE_VIDEO (S{season:02d}E{episode:02d})")

    start_sec = max(0, (start_ms - padding_ms) / 1000.0)
    end_sec = (end_ms + padding_ms) / 1000.0
    storage_key = f"clips/{clip_id}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{clip_id}.mp4"
        # -ss 放在 -i 之后，MKV 切段更准确，避免黑屏/空帧
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-ss",
            str(start_sec),
            "-to",
            str(end_sec),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(out),
        ]
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            logger.info("ffmpeg ok clip=%s stderr_len=%s", clip_id, len(proc.stderr or ""))
        except FileNotFoundError:
            return _fail(clip_id, "FFMPEG_NOT_INSTALLED")
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e))[:500]
            return _fail(clip_id, f"FFMPEG_ERROR: {err}")

        if not out.exists() or out.stat().st_size == 0:
            return _fail(clip_id, "FFMPEG_OUTPUT_EMPTY")

        data = out.read_bytes()
        thumb_key = f"thumbs/{clip_id}.jpg"
        thumb_path = Path(tmp) / f"{clip_id}.jpg"
        mid_sec = (start_sec + end_sec) / 2.0
        thumb_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(mid_sec),
            "-i",
            str(video),
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(thumb_path),
        ]
        try:
            subprocess.run(
                thumb_cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            logger.warning("thumbnail ffmpeg failed clip=%s: %s", clip_id, exc)

        bucket = settings.supabase_storage_bucket
        try:
            sb = _supabase()
            sb.storage.from_(bucket).upload(
                storage_key,
                data,
                file_options={"content-type": "video/mp4", "upsert": "true"},
            )
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                sb.storage.from_(bucket).upload(
                    thumb_key,
                    thumb_path.read_bytes(),
                    file_options={"content-type": "image/jpeg", "upsert": "true"},
                )
        except Exception as exc:
            logger.exception("Storage upload failed clip=%s", clip_id)
            return _fail(clip_id, f"STORAGE_UPLOAD: {str(exc)[:400]}")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE clip_assets
            SET status = 'ready', storage_path = %s, file_size = %s, updated_at = now()
            WHERE id = %s
            """,
            (storage_key, len(data), clip_id),
        )
        conn.commit()
    logger.info("Clip ready %s size=%s", clip_id, len(data))
    return get_clip(clip_id)


def _fail(clip_id: str, message: str) -> dict:
    logger.error("Clip failed %s: %s", clip_id, message)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE clip_assets SET status = 'failed', error_message = %s, updated_at = now()
            WHERE id = %s
            """,
            (message, clip_id),
        )
        conn.commit()
    return get_clip(clip_id)
