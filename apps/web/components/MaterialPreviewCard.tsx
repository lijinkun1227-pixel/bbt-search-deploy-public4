"use client";

import { useState } from "react";
import { formatTime, type MaterialItem } from "@/lib/api";

type Props = {
  item: MaterialItem;
  onClick: () => void;
};

export function MaterialPreviewCard({ item, onClick }: Props) {
  const [thumbOk, setThumbOk] = useState(true);
  const thumb = item.thumbnail_url;

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col overflow-hidden rounded-xl border border-slate-200/80 bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:border-amber-300/60 hover:shadow-md"
    >
      <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-slate-800 via-slate-900 to-indigo-950">
        {thumb && thumbOk ? (
          <img
            src={thumb}
            alt=""
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
            onError={() => setThumbOk(false)}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-lg text-white">
              ▶
            </span>
            <span className="text-center font-serif text-xs italic leading-snug text-white/75 line-clamp-3">
              {item.text_en}
            </span>
          </div>
        )}
        <span className="absolute bottom-2 left-2 rounded bg-black/55 px-2 py-0.5 text-xs text-white">
          S{item.season.toString().padStart(2, "0")}E{item.episode.toString().padStart(2, "0")}{" "}
          {formatTime(item.start_ms)}
        </span>
        <span className="absolute right-2 top-2 rounded-full bg-amber-500/90 px-2 py-0.5 text-[10px] font-medium text-white shadow">
          查看片段
        </span>
      </div>
      <div className="p-3">
        <p className="line-clamp-2 text-xs leading-relaxed text-slate-600">{item.text_en}</p>
      </div>
    </button>
  );
}
