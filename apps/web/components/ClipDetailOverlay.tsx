"use client";

import { useCallback, useEffect, useState } from "react";
import { createClips, formatTime, type MaterialItem } from "@/lib/api";
import { normalizeClipPlayUrl } from "@/lib/clip-url";
import { ClipPlayer } from "@/components/ClipPlayer";
import { useBasket } from "@/store/basket";

type Props = {
  items: MaterialItem[];
  index: number;
  open: boolean;
  onClose: () => void;
  onIndexChange: (index: number) => void;
};

export function ClipDetailOverlay({
  items,
  index,
  open,
  onClose,
  onIndexChange,
}: Props) {
  const { add } = useBasket();
  const [materials, setMaterials] = useState<MaterialItem[]>(items);
  const [loadingClip, setLoadingClip] = useState(false);
  const [clipError, setClipError] = useState("");

  useEffect(() => {
    setMaterials(items);
  }, [items]);

  const current = materials[index];
  const hasPrev = index > 0;
  const hasNext = index < materials.length - 1;

  const ensureClip = useCallback(async (item: MaterialItem) => {
    if (item.play_url && item.clip_id) return item;
    setLoadingClip(true);
    setClipError("");
    try {
      const { jobs } = await createClips([item.line_id]);
      const job = jobs[0];
      const play_url = normalizeClipPlayUrl(job?.play_url ?? undefined, job?.clip_id);
      const updated: MaterialItem = {
        ...item,
        clip_id: job?.clip_id ?? item.clip_id,
        play_url,
        has_clip: job?.status === "ready",
      };
      setMaterials((prev) =>
        prev.map((m) => (m.line_id === item.line_id ? updated : m))
      );
      return updated;
    } catch {
      setClipError("片段加载失败，请确认 API 与 FFmpeg 已就绪");
      return item;
    } finally {
      setLoadingClip(false);
    }
  }, []);

  useEffect(() => {
    if (!open || !current || current.play_url) return;
    ensureClip(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅在打开或切换条目时拉取片段
  }, [open, index]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasPrev) onIndexChange(index - 1);
      if (e.key === "ArrowRight" && hasNext) onIndexChange(index + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, index, hasPrev, hasNext, onClose, onIndexChange]);

  if (!open || !current) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/70 backdrop-blur-sm"
        aria-label="关闭"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
          <span className="text-sm font-medium text-slate-500">
            S{current.season.toString().padStart(2, "0")}E
            {current.episode.toString().padStart(2, "0")} · {formatTime(current.start_ms)}
            <span className="ml-2 text-slate-400">
              {index + 1} / {materials.length}
            </span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4 px-5 py-5">
          <blockquote className="border-l-4 border-amber-400 pl-4">
            <p className="font-serif text-lg leading-relaxed text-slate-900">
              {current.text_en}
            </p>
            {current.text_zh && (
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{current.text_zh}</p>
            )}
            {"align_confidence" in current &&
              current.align_confidence != null &&
              current.align_confidence < 0.5 && (
                <p className="mt-2 text-xs text-amber-600">
                  双语对齐置信度较低，若与画面不符请检查字幕文件是否为同一集。
                </p>
              )}
          </blockquote>

          <div className="relative min-h-[200px] rounded-xl bg-slate-950">
            {loadingClip && (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-white/80">
                正在准备片段…
              </div>
            )}
            {current.play_url || current.clip_id ? (
              <ClipPlayer
                clipId={current.clip_id ?? undefined}
                playUrl={current.play_url ?? undefined}
                lineId={current.line_id}
                onUrlFixed={(url) => {
                  setMaterials((prev) =>
                    prev.map((m) =>
                      m.line_id === current.line_id ? { ...m, play_url: url } : m
                    )
                  );
                }}
              />
            ) : (
              !loadingClip && (
                <div className="flex h-[200px] items-center justify-center text-sm text-white/60">
                  暂无视频片段
                </div>
              )
            )}
          </div>
          {clipError && <p className="text-sm text-red-600">{clipError}</p>}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-4">
          <button
            type="button"
            disabled={!hasPrev}
            onClick={() => onIndexChange(index - 1)}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm disabled:opacity-30"
          >
            ← 上一条
          </button>
          <button
            type="button"
            onClick={() => add(current)}
            className="rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-700 hover:bg-slate-200"
          >
            加入素材篮
          </button>
          <button
            type="button"
            disabled={!hasNext}
            onClick={() => onIndexChange(index + 1)}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm disabled:opacity-30"
          >
            下一条 →
          </button>
        </div>
      </div>
    </div>
  );
}
