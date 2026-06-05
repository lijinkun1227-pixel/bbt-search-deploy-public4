"use client";

import type { SearchItem } from "@/lib/api";
import { formatTime } from "@/lib/api";
import { useBasket } from "@/store/basket";

type Props = {
  item: SearchItem;
  onOpen: () => void;
};

export function ResultCard({ item, onOpen }: Props) {
  const { items, add, remove } = useBasket();
  const selected = items.some((i) => i.line_id === item.line_id);

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className="cursor-pointer rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-amber-300/50 hover:shadow-md"
    >
      <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
        <span>
          S{item.season.toString().padStart(2, "0")}E{item.episode.toString().padStart(2, "0")} ·{" "}
          {formatTime(item.start_ms)}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            selected ? remove(item.line_id) : add(item);
          }}
          className={`rounded-md px-3 py-1 text-sm ${
            selected ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
          }`}
        >
          {selected ? "已加入" : "加入素材篮"}
        </button>
      </div>
      <p
        className="text-base leading-relaxed text-slate-900"
        dangerouslySetInnerHTML={{ __html: item.snippet_en || item.text_en }}
      />
      {item.text_zh && (
        <p
          className="mt-2 text-sm leading-relaxed text-slate-600"
          dangerouslySetInnerHTML={{ __html: item.snippet_zh || item.text_zh }}
        />
      )}
      <p className="mt-3 text-xs text-amber-600/80">点击查看片段 →</p>
    </article>
  );
}
