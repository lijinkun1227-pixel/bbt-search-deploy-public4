"use client";

import { useCallback, useEffect, useState } from "react";
import { getClip } from "@/lib/api";
import { normalizeClipPlayUrl } from "@/lib/clip-url";

type Props = {
  clipId?: string;
  playUrl?: string;
  lineId: number;
  onUrlFixed?: (url: string) => void;
};

export function ClipPlayer({ clipId, playUrl, lineId, onUrlFixed }: Props) {
  const [src, setSrc] = useState(() => normalizeClipPlayUrl(playUrl, clipId));
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    setSrc(normalizeClipPlayUrl(playUrl, clipId));
    setLoadError(false);
  }, [playUrl, clipId]);

  const refreshFromApi = useCallback(async () => {
    if (!clipId) return;
    try {
      const c = await getClip(clipId);
      const fixed = normalizeClipPlayUrl(c.play_url ?? undefined, clipId);
      if (fixed) {
        setSrc(fixed);
        onUrlFixed?.(fixed);
        setLoadError(false);
      }
    } catch {
      setLoadError(true);
    }
  }, [clipId, onUrlFixed]);

  useEffect(() => {
    if (clipId && playUrl) {
      const fixed = normalizeClipPlayUrl(playUrl, clipId);
      if (fixed && fixed !== playUrl) {
        setSrc(fixed);
        onUrlFixed?.(fixed);
      }
    }
  }, [clipId, playUrl, onUrlFixed]);

  if (!src) return null;

  return (
    <div className="mt-2">
      <video
        key={src}
        src={src}
        controls
        preload="metadata"
        playsInline
        className="w-full rounded bg-black"
        onError={() => {
          setLoadError(true);
          refreshFromApi();
        }}
      />
      {loadError && (
        <button
          type="button"
          className="mt-1 text-xs text-brand underline"
          onClick={refreshFromApi}
        >
          加载失败，点击刷新播放链接
        </button>
      )}
    </div>
  );
}
