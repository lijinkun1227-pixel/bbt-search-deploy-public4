from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SrtLine:
    season: int
    episode: int
    index: int
    start_ms: int
    end_ms: int
    text: str

    @property
    def text_clean(self) -> str:
        t = HTML_TAG_RE.sub("", self.text)
        t = t.replace("\n", " ").strip()
        return re.sub(r"\s+", " ", t)


def time_to_ms(h: str, m: str, s: str, ms: str) -> int:
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


def parse_srt_file(path: str | Path, season: int, episode: int) -> list[SrtLine]:
    content = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", content.strip())
    lines: list[SrtLine] = []
    idx = 0
    for block in blocks:
        rows = [r.strip() for r in block.splitlines() if r.strip()]
        if len(rows) < 2:
            continue
        time_row = rows[1] if rows[0].isdigit() else rows[0]
        text_rows = rows[2:] if rows[0].isdigit() else rows[1:]
        m = TIME_RE.search(time_row)
        if not m or not text_rows:
            continue
        idx += 1
        start_ms = time_to_ms(*m.groups()[:4])
        end_ms = time_to_ms(*m.groups()[4:8])
        if end_ms <= start_ms:
            continue
        text = "\n".join(text_rows)
        if not text.strip():
            continue
        lines.append(
            SrtLine(
                season=season,
                episode=episode,
                index=idx,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
            )
        )
    return lines


def line_hash(season: int, episode: int, start_ms: int, text_en: str) -> str:
    norm = re.sub(r"\s+", " ", text_en.lower().strip())
    raw = f"{season}|{episode}|{start_ms}|{norm}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
