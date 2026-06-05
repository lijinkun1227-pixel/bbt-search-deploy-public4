"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ResultCard } from "@/components/ResultCard";
import { SearchBar } from "@/components/SearchBar";
import { SearchPagination } from "@/components/SearchPagination";
import { ClipDetailOverlay } from "@/components/ClipDetailOverlay";
import { searchQuotes, type MaterialItem, type SearchItem } from "@/lib/api";

function toMaterials(items: SearchItem[]): MaterialItem[] {
  return items.map((i) => ({ ...i, clip_id: null, play_url: null }));
}

export default function SearchPage() {
  const sp = useSearchParams();
  const q = sp.get("q") || "";
  const lang = sp.get("lang") || "both";
  const page = Math.max(1, parseInt(sp.get("page") || "1", 10) || 1);
  const [items, setItems] = useState<SearchItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [wholeWord, setWholeWord] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayIndex, setOverlayIndex] = useState(0);

  const materials = useMemo(() => toMaterials(items), [items]);

  useEffect(() => {
    if (!q) return;
    setLoading(true);
    setError("");
    searchQuotes({ q, lang, page })
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages ?? 1);
        setWholeWord(data.whole_word ?? true);
        setOverlayOpen(false);
      })
      .catch(() => setError("搜索失败，请确认后端 API 已部署且 NEXT_PUBLIC_API_URL 配置正确"))
      .finally(() => setLoading(false));
  }, [q, lang, page]);

  return (
    <div className="space-y-6">
      <SearchBar defaultQ={q} defaultLang={lang} />
      {loading && <p className="text-slate-500">搜索中…</p>}
      {error && <p className="text-red-600">{error}</p>}
      {!loading && q && (
        <p className="text-sm text-slate-500">
          「{q}」共 {total} 条
          {wholeWord && /^[a-zA-Z]/.test(q.trim()) ? "（英文整词匹配）" : ""}
          ，当前第 {page} 页 · 点击卡片查看片段
        </p>
      )}
      <div className="space-y-4">
        {items.map((item, i) => (
          <ResultCard
            key={item.line_id}
            item={item}
            onOpen={() => {
              setOverlayIndex(i);
              setOverlayOpen(true);
            }}
          />
        ))}
      </div>

      <SearchPagination page={page} totalPages={totalPages} total={total} />

      <ClipDetailOverlay
        items={materials}
        index={overlayIndex}
        open={overlayOpen}
        onClose={() => setOverlayOpen(false)}
        onIndexChange={setOverlayIndex}
      />
    </div>
  );
}
