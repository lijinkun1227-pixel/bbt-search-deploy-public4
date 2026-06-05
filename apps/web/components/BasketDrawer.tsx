"use client";

import { useEffect, useState } from "react";
import { createClips, createShare, formatTime, getClip } from "@/lib/api";
import { normalizeClipPlayUrl } from "@/lib/clip-url";
import { ClipPlayer } from "@/components/ClipPlayer";
import { useBasket } from "@/store/basket";

export function BasketDrawer() {
  const { items, remove, clear, updateClip } = useBasket();
  const [busy, setBusy] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [error, setError] = useState("");

  // 打开页面时刷新已 ready 条目的播放链接（避免 localStorage 里缓存了旧 URL）
  useEffect(() => {
    items.forEach(async (item) => {
      if (item.clipId && item.clipStatus === "ready") {
        try {
          const c = await getClip(item.clipId);
          const fixed = normalizeClipPlayUrl(c.play_url ?? undefined, item.clipId);
          if (fixed && fixed !== item.playUrl) {
            updateClip(item.line_id, { playUrl: fixed, clipStatus: c.status });
          }
        } catch {
          /* ignore */
        }
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- 仅首屏校正一次

  async function generateClips() {
    setBusy(true);
    setError("");
    try {
      const need = items.filter((i) => i.clipStatus !== "ready");
      if (need.length) {
        const { jobs } = await createClips(need.map((i) => i.line_id));
        for (const job of jobs) {
          const lineId =
            (job?.line_id as number | undefined) ??
            need.find((n) => n.clipId === job?.clip_id)?.line_id;
          if (job?.clip_id && lineId != null) {
            const fixed = normalizeClipPlayUrl(job.play_url ?? undefined, job.clip_id);
            updateClip(lineId, {
              clipId: job.clip_id,
              clipStatus: job.status,
              playUrl: fixed,
            });
            if (job.status === "failed" && job.error_message) {
              setError(String(job.error_message));
            }
          }
        }
      }
      // 已有 ready 的也重新拉 play_url（修复缓存里的错误链接）
      for (const item of items) {
        if (item.clipId) {
          const c = await getClip(item.clipId);
          const fixed = normalizeClipPlayUrl(c.play_url ?? undefined, item.clipId);
          updateClip(item.line_id, {
            clipStatus: c.status,
            playUrl: fixed,
          });
          if (c.status === "failed" && c.error_message) {
            setError(String(c.error_message));
          }
        }
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "生成失败，请确认 API 已启动且 FFmpeg/Storage 已配置"
      );
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const clipIds = items.map((i) => i.clipId).filter(Boolean) as string[];
    const data = await createShare(
      items.map((i) => i.line_id),
      clipIds
    );
    const url = `${window.location.origin}${data.url}`;
    setShareUrl(url);
    await navigator.clipboard.writeText(url);
  }

  if (!items.length) return null;

  return (
    <aside className="fixed bottom-0 left-0 right-0 z-50 max-h-[45vh] overflow-auto border-t border-slate-200 bg-white p-4 shadow-lg md:left-auto md:right-4 md:bottom-4 md:w-96 md:rounded-xl md:border">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">素材篮 ({items.length})</h2>
        <button type="button" className="text-sm text-slate-500" onClick={clear}>
          清空
        </button>
      </div>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.line_id} className="rounded-lg bg-slate-50 p-3 text-sm">
            <div className="mb-1 text-slate-500">
              S{item.season}E{item.episode} {formatTime(item.start_ms)}
              {item.clipStatus && item.clipStatus !== "idle" && (
                <span className="ml-2 text-xs">· {item.clipStatus}</span>
              )}
            </div>
            <p className="line-clamp-2">{item.text_en}</p>
            {(item.playUrl || item.clipId) && (
              <ClipPlayer
                clipId={item.clipId}
                playUrl={item.playUrl}
                lineId={item.line_id}
                onUrlFixed={(url) => updateClip(item.line_id, { playUrl: url })}
              />
            )}
            <button type="button" className="mt-1 text-red-500" onClick={() => remove(item.line_id)}>
              移除
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-col gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={generateClips}
          className="rounded-lg bg-brand py-2 text-white disabled:opacity-50"
        >
          {busy ? "生成中（可能需要几十秒）…" : "生成/刷新视频片段"}
        </button>
        {error && <p className="text-xs text-red-600 break-words">{error}</p>}
        <button type="button" onClick={share} className="rounded-lg border border-slate-300 py-2">
          创建分享链接
        </button>
        {shareUrl && <p className="break-all text-xs text-slate-600">已复制: {shareUrl}</p>}
      </div>
    </aside>
  );
}
