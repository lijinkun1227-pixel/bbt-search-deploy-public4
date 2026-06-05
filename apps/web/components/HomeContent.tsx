"use client";

import { useEffect, useState } from "react";
import { SearchBar } from "@/components/SearchBar";
import { MaterialPreviewCard } from "@/components/MaterialPreviewCard";
import { ClipDetailOverlay } from "@/components/ClipDetailOverlay";
import { fetchFeatured, type MaterialItem } from "@/lib/api";
import { pickRandomQuote, type HeroQuote } from "@/lib/quotes";
import { normalizeClipPlayUrl } from "@/lib/clip-url";

export function HomeContent() {
  const [quote, setQuote] = useState<HeroQuote | null>(null);
  const [featured, setFeatured] = useState<MaterialItem[]>([]);
  const [loadingFeatured, setLoadingFeatured] = useState(true);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayIndex, setOverlayIndex] = useState(0);

  // 随机台词仅在客户端生成，避免 SSR/CSR 不一致（hydration 报错）
  useEffect(() => {
    setQuote(pickRandomQuote());
  }, []);

  useEffect(() => {
    setLoadingFeatured(true);
    fetchFeatured(9)
      .then((data) => {
        setFeatured(
          data.items.map((item) => ({
            ...item,
            play_url: normalizeClipPlayUrl(item.play_url ?? undefined, item.clip_id ?? undefined),
          }))
        );
      })
      .catch(() => setFeatured([]))
      .finally(() => setLoadingFeatured(false));
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-10 text-center">
        <p className="mb-3 text-xs font-medium uppercase tracking-[0.35em] text-amber-600/90">
          Quote Finder
        </p>
        <h1 className="font-serif text-4xl font-light tracking-tight text-slate-900 md:text-5xl">
          The Big Bang Theory
        </h1>
        <div className="mx-auto mt-6 max-w-lg min-h-[7rem]">
          <div className="mx-auto h-px w-12 bg-gradient-to-r from-transparent via-amber-400 to-transparent" />
          {quote ? (
            <>
              <p className="mt-6 font-serif text-lg italic leading-relaxed text-slate-700">
                &ldquo;{quote.en}&rdquo;
              </p>
              {quote.zh && <p className="mt-2 text-sm text-slate-500">{quote.zh}</p>}
              <p className="mt-3 text-xs text-slate-400">— {quote.attribution}</p>
            </>
          ) : (
            <div className="mt-6 space-y-2 animate-pulse">
              <div className="mx-auto h-5 w-3/4 rounded bg-slate-200" />
              <div className="mx-auto h-4 w-1/2 rounded bg-slate-100" />
            </div>
          )}
        </div>
      </header>

      <div className="mx-auto max-w-2xl">
        <SearchBar />
      </div>

      <section className="mt-12">
        <div className="mb-4">
          <h2 className="text-sm font-medium text-slate-500">随机片段 · 刷新页面可换一批</h2>
        </div>
        {loadingFeatured ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="aspect-video animate-pulse rounded-xl bg-slate-200" />
            ))}
          </div>
        ) : featured.length === 0 ? (
          <p className="text-center text-sm text-slate-500">
            暂无推荐片段，请先搜索台词并生成视频。
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((item, i) => (
              <MaterialPreviewCard
                key={`${item.line_id}-${i}`}
                item={item}
                onClick={() => {
                  setOverlayIndex(i);
                  setOverlayOpen(true);
                }}
              />
            ))}
          </div>
        )}
      </section>

      <ClipDetailOverlay
        items={featured}
        index={overlayIndex}
        open={overlayOpen}
        onClose={() => setOverlayOpen(false)}
        onIndexChange={setOverlayIndex}
      />
    </div>
  );
}
