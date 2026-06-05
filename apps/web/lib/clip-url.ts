/**
 * 修正 Supabase Storage 播放地址。
 * 旧版 API 可能返回 .../public/clips/{id}.mp4，实际文件在 .../public/clips/clips/{id}.mp4
 */
export function normalizeClipPlayUrl(
  playUrl: string | undefined,
  clipId?: string
): string | undefined {
  if (!playUrl || !clipId) return playUrl;

  const bucket = "clips";
  const wrongSuffix = `/public/${bucket}/${clipId}.mp4`;
  const rightSuffix = `/public/${bucket}/${bucket}/${clipId}.mp4`;

  if (playUrl.includes(wrongSuffix) && !playUrl.includes(`/public/${bucket}/${bucket}/`)) {
    return playUrl.replace(wrongSuffix, rightSuffix);
  }

  return playUrl;
}
