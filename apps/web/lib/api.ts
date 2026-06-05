const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type SearchItem = {
  line_id: number;
  season: number;
  episode: number;
  start_ms: number;
  end_ms: number;
  text_en: string;
  text_zh?: string | null;
  snippet_en?: string | null;
  snippet_zh?: string | null;
  has_clip: boolean;
  align_confidence?: number | null;
};

export type MaterialItem = SearchItem & {
  clip_id?: string | null;
  play_url?: string | null;
  thumbnail_url?: string | null;
};

export async function searchQuotes(params: {
  q: string;
  lang?: string;
  page?: number;
  page_size?: number;
  whole_word?: boolean;
}) {
  const sp = new URLSearchParams({
    q: params.q,
    lang: params.lang || "both",
    page: String(params.page || 1),
    page_size: String(params.page_size || 20),
    whole_word: String(params.whole_word !== false),
  });
  const res = await fetch(`${API}/api/search?${sp}`);
  if (!res.ok) throw new Error("Search failed");
  return res.json() as Promise<{
    total: number;
    items: SearchItem[];
    page: number;
    page_size: number;
    total_pages: number;
    whole_word?: boolean;
  }>;
}

export async function fetchFeatured(limit = 9) {
  const res = await fetch(`${API}/api/featured?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Featured failed");
  return res.json() as Promise<{ items: MaterialItem[] }>;
}

export async function createClips(lineIds: number[], paddingMs = 500) {
  const res = await fetch(`${API}/api/clips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line_ids: lineIds, padding_ms: paddingMs }),
  });
  if (!res.ok) throw new Error("Clip failed");
  return res.json();
}

export async function getClip(clipId: string) {
  const res = await fetch(`${API}/api/clips/${clipId}`);
  if (!res.ok) throw new Error("Get clip failed");
  return res.json();
}

export async function createShare(lineIds: number[], clipIds: string[] = []) {
  const res = await fetch(`${API}/api/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line_ids: lineIds, clip_ids: clipIds }),
  });
  if (!res.ok) throw new Error("Share failed");
  return res.json() as Promise<{ share_id: string; url: string }>;
}

export async function getShare(shareId: string) {
  const res = await fetch(`${API}/api/share/${shareId}`);
  if (!res.ok) throw new Error("Share not found");
  return res.json();
}

export function formatTime(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
