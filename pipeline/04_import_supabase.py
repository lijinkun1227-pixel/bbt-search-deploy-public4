#!/usr/bin/env python3
"""导入 jsonl 到 Supabase PostgreSQL。用法: python pipeline/04_import_supabase.py --season 1"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.env import get_database_url  # noqa: E402

STAGING = ROOT / "data" / "staging"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--clear-season", action="store_true", help="删除该季旧台词后重导")
    args = parser.parse_args()

    path = STAGING / f"S{args.season:02d}_lines_aligned.jsonl"
    if not path.exists():
        print("Run 03_align_bilingual.py first")
        sys.exit(1)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    conn = psycopg2.connect(get_database_url())
    conn.autocommit = False
    cur = conn.cursor()
    try:
        if args.clear_season:
            cur.execute(
                """
                DELETE FROM subtitle_lines
                WHERE episode_id IN (SELECT id FROM episodes WHERE season = %s)
                """,
                (args.season,),
            )
            cur.execute("DELETE FROM episodes WHERE season = %s", (args.season,))

        episode_ids: dict[tuple[int, int], int] = {}
        for (season, episode) in {(r["season"], r["episode"]) for r in rows}:
            cur.execute(
                """
                INSERT INTO episodes (season, episode, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (season, episode) DO UPDATE SET season = EXCLUDED.season
                RETURNING id
                """,
                (season, episode, f"S{season:02d}E{episode:02d}"),
            )
            episode_ids[(season, episode)] = cur.fetchone()[0]

        batch = []
        for r in rows:
            eid = episode_ids[(r["season"], r["episode"])]
            batch.append(
                (
                    eid,
                    r["start_ms"],
                    r["end_ms"],
                    r["text_en"],
                    r.get("text_zh"),
                    r.get("align_confidence"),
                    r["line_hash"],
                )
            )
        execute_batch(
            cur,
            """
            INSERT INTO subtitle_lines
              (episode_id, start_ms, end_ms, text_en, text_zh, align_confidence, line_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (line_hash) DO NOTHING
            """,
            batch,
            page_size=500,
        )
        conn.commit()
        cur.execute(
            "SELECT COUNT(*) FROM subtitle_lines sl JOIN episodes e ON e.id = sl.episode_id WHERE e.season = %s",
            (args.season,),
        )
        total = cur.fetchone()[0]
        print(f"Import done. Season {args.season} subtitle_lines count: {total}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
