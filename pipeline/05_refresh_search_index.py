#!/usr/bin/env python3
"""刷新 search_vector（触发器更新已有行）。用法: python pipeline/05_refresh_search_index.py"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.env import get_database_url  # noqa: E402


def main() -> None:
    conn = psycopg2.connect(get_database_url())
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE subtitle_lines
        SET text_en = text_en
        """
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM subtitle_lines")
    print(f"Refreshed search_vector for {cur.fetchone()[0]} rows")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
