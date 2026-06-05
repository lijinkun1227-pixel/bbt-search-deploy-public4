#!/usr/bin/env python3
"""英中字幕对齐：优先序号+时间偏移，其次时间重叠。用法: python pipeline/03_align_bilingual.py --season 1"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common.srt import parse_srt_file  # noqa: E402

RAW = ROOT / "data" / "raw" / "subtitles"
STAGING = ROOT / "data" / "staging"
EP_RE = re.compile(r"S(\d+)E(\d+)", re.I)


def overlap_ratio(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    duration = max(a_end - a_start, 1)
    return overlap / duration


def center_ms(start: int, end: int) -> int:
    return (start + end) // 2


def find_best_index_offset(en_rows: list[dict], zh_lines: list, sample: int = 30) -> int:
    """在 zh 相对 en 的索引偏移 k 中，找时间中心最接近的 k（-15..15）。"""
    if not en_rows or not zh_lines:
        return 0
    best_k = 0
    best_score = float("inf")
    n = min(sample, len(en_rows))
    for k in range(-15, 16):
        err = 0.0
        matched = 0
        for i in range(n):
            j = i + k
            if j < 0 or j >= len(zh_lines):
                err += 60_000
                continue
            err += abs(
                center_ms(en_rows[i]["start_ms"], en_rows[i]["end_ms"])
                - center_ms(zh_lines[j].start_ms, zh_lines[j].end_ms)
            )
            matched += 1
        if matched and err / matched < best_score:
            best_score = err / matched
            best_k = k
    return best_k


def align_episode(en_rows: list[dict], zh_lines: list) -> list[dict]:
    """对单集所有 en 行写入 text_zh / align_confidence。"""
    if not zh_lines:
        for row in en_rows:
            row["text_zh"] = None
            row["align_confidence"] = None
        return en_rows

    # 按 index 排序的 en 逻辑行（jsonl 已是时间序）
    offset = find_best_index_offset(en_rows, zh_lines)

    for i, row in enumerate(en_rows):
        j = i + offset
        text_zh = None
        conf = 0.0

        if 0 <= j < len(zh_lines):
            z = zh_lines[j]
            ov = overlap_ratio(row["start_ms"], row["end_ms"], z.start_ms, z.end_ms)
            center_diff = abs(
                center_ms(row["start_ms"], row["end_ms"]) - center_ms(z.start_ms, z.end_ms)
            )
            # 序号对齐 + 时间不离谱（中心点差 < 8s 或重叠 > 0.35）
            if ov >= 0.35 or center_diff < 8000:
                text_zh = z.text_clean
                conf = max(ov, 1.0 - min(center_diff / 8000.0, 1.0))

        if not text_zh:
            # 回退：纯时间重叠
            best_text, best_score = None, 0.0
            for z in zh_lines:
                score = overlap_ratio(row["start_ms"], row["end_ms"], z.start_ms, z.end_ms)
                if score > best_score:
                    best_score = score
                    best_text = z.text_clean
            if best_score >= 0.55 and best_text:
                text_zh = best_text
                conf = best_score

        row["text_zh"] = text_zh
        row["align_confidence"] = round(conf, 3) if text_zh else None
    return en_rows


def load_zh_by_episode(season: int) -> dict[tuple[int, int], list]:
    result: dict[tuple[int, int], list] = {}
    for path in sorted((RAW / "zh").glob("*.srt")):
        m = EP_RE.search(path.stem)
        if not m or int(m.group(1)) != season:
            continue
        s, e = int(m.group(1)), int(m.group(2))
        result[(s, e)] = parse_srt_file(path, s, e)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()

    en_path = STAGING / f"S{args.season:02d}_lines_en.jsonl"
    if not en_path.exists():
        print("Run 02_parse_srt.py first")
        sys.exit(1)

    zh_map = load_zh_by_episode(args.season)
    by_ep: dict[tuple[int, int], list[dict]] = {}
    for raw in en_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        key = (row["season"], row["episode"])
        by_ep.setdefault(key, []).append(row)

    out_path = STAGING / f"S{args.season:02d}_lines_aligned.jsonl"
    count = 0
    with out_path.open("w", encoding="utf-8") as fout:
        for key in sorted(by_ep.keys()):
            aligned = align_episode(by_ep[key], zh_map.get(key, []))
            for row in aligned:
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
            print(f"  S{key[0]:02d}E{key[1]:02d}: {len(aligned)} lines, zh={sum(1 for r in aligned if r.get('text_zh'))} matched")
    print(f"Aligned {count} lines -> {out_path}")
    print("请重新运行: python pipeline/04_import_supabase.py --season 1 --clear-season")


if __name__ == "__main__":
    main()
