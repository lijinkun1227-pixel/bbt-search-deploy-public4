#!/usr/bin/env python3
"""CLI 搜索。用法: python pipeline/search_cli.py bazinga"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.env import get_database_url  # noqa: E402


def main() -> None:
    q = " ".join(sys.argv[1:]) or "bazinga"
    conn = psycopg2.connect(get_database_url())
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.season, e.episode, sl.start_ms, sl.text_en, sl.text_zh
        FROM subtitle_lines sl
        JOIN episodes e ON e.id = sl.episode_id
        WHERE sl.text_en ILIKE %s OR sl.text_zh ILIKE %s
        ORDER BY e.season, e.episode, sl.start_ms
        LIMIT 10
        """,
        (f"%{q}%", f"%{q}%"),
    )
    rows = cur.fetchall()
    print(f"Query '{q}' -> {len(rows)} hits (showing up to 10)")
    for s, ep, start_ms, en, zh in rows:
        sec = start_ms // 1000
        print(f"S{s:02d}E{ep:02d} {sec//60:02d}:{sec%60:02d} | {en[:80]}")
        if zh:
            print(f"  ZH: {zh[:80]}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
