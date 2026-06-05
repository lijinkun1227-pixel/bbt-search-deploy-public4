#!/usr/bin/env python3
"""解析 raw 字幕为 jsonl。用法: python pipeline/02_parse_srt.py --season 1"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.srt import line_hash, parse_srt_file  # noqa: E402

RAW = ROOT / "data" / "raw" / "subtitles"
STAGING = ROOT / "data" / "staging"
EP_RE = re.compile(r"S(\d+)E(\d+)", re.I)


def discover_episodes(season: int, lang: str) -> list[tuple[int, int, Path]]:
    folder = RAW / lang
    found: dict[tuple[int, int], Path] = {}
    for path in sorted(folder.glob("*.srt")):
        m = EP_RE.search(path.stem)
        if not m:
            continue
        s, e = int(m.group(1)), int(m.group(2))
        if s != season:
            continue
        found[(s, e)] = path
    return [(s, e, p) for (s, e), p in sorted(found.items())]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    STAGING.mkdir(parents=True, exist_ok=True)

    episodes = discover_episodes(args.season, "en")
    if not episodes:
        print(f"No EN srt for season {args.season} under {RAW / 'en'}")
        sys.exit(1)

    out_path = STAGING / f"S{args.season:02d}_lines_en.jsonl"
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for season, episode, path in episodes:
            for line in parse_srt_file(path, season, episode):
                row = {
                    "season": season,
                    "episode": episode,
                    "start_ms": line.start_ms,
                    "end_ms": line.end_ms,
                    "text_en": line.text_clean,
                    "line_hash": line_hash(season, episode, line.start_ms, line.text_clean),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    print(f"Wrote {count} lines -> {out_path}")


if __name__ == "__main__":
    main()
