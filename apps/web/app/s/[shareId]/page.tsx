"use client";

import { useEffect, useState } from "react";
import { formatTime, getShare } from "@/lib/api";

export default function SharePage({ params }: { params: { shareId: string } }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof getShare>> | null>(null);

  useEffect(() => {
    getShare(params.shareId).then(setData).catch(() => setData(null));
  }, [params.shareId]);

  if (!data) return <p className="text-slate-500">加载分享页…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">分享素材</h1>
      {data.items?.map((item: { line_id: number; season: number; episode: number; start_ms: number; text_en: string; text_zh?: string }) => (
        <article key={item.line_id} className="rounded-xl border bg-white p-4">
          <p className="text-sm text-slate-500">
            S{item.season}E{item.episode} {formatTime(item.start_ms)}
          </p>
          <p className="mt-2">{item.text_en}</p>
          {item.text_zh && <p className="mt-1 text-slate-600">{item.text_zh}</p>}
        </article>
      ))}
      {data.clips?.map((c: { clip_id: string; play_url?: string }) =>
        c.play_url ? <video key={c.clip_id} src={c.play_url} controls className="w-full rounded-lg" /> : null
      )}
    </div>
  );
}
