#!/usr/bin/env python3
"""扫描本地视频目录（支持 mp4/mkv），登记到 episodes 表。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.env import get_database_url, get_source_video_root  # noqa: E402

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}
EP_RE = re.compile(r"S(\d+)E(\d+)", re.I)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, default="")
    args = parser.parse_args()
    root = Path(args.root) if args.root else get_source_video_root()
    if not root.exists():
        print(f"Video root not found: {root}")
        print("Create it and add files like S01E01.mkv, S01E02.mkv")
        sys.exit(1)

    found = []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() not in VIDEO_EXTS:
            continue
        m = EP_RE.search(path.stem)
        if not m:
            continue
        found.append((int(m.group(1)), int(m.group(2)), str(path.resolve())))

    if not found:
        print(f"No SxxExx video files in {root} (supported: {', '.join(VIDEO_EXTS)})")
        sys.exit(1)

    conn = psycopg2.connect(get_database_url())
    cur = conn.cursor()
    for season, episode, abspath in found:
        cur.execute(
            """
            INSERT INTO episodes (season, episode, title, source_video_path, has_source_video)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (season, episode) DO UPDATE SET
              source_video_path = EXCLUDED.source_video_path,
              has_source_video = TRUE
            """,
            (season, episode, f"S{season:02d}E{episode:02d}", abspath),
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Registered {len(found)} video file(s):")
    for s, e, p in found:
        print(f"  S{s:02d}E{e:02d} -> {p}")


if __name__ == "__main__":
    main()
