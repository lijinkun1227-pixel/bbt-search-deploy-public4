"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

const HOT = ["bazinga", "penny", "Sheldon", "谢尔顿"];

export function SearchBar({ defaultQ = "", defaultLang = "both" }: { defaultQ?: string; defaultLang?: string }) {
  const router = useRouter();
  const [q, setQ] = useState(defaultQ);
  const [lang, setLang] = useState(defaultLang);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    router.push(`/search?q=${encodeURIComponent(q.trim())}&lang=${lang}&page=1`);
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 focus:border-brand focus:outline-none"
          placeholder="搜索台词…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="rounded-lg border border-slate-300 px-3"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
        >
          <option value="both">双语</option>
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
        <button type="submit" className="rounded-lg bg-brand px-5 py-2 text-white hover:bg-brand-dark">
          搜索
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {HOT.map((w) => (
          <button
            key={w}
            type="button"
            className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700 hover:bg-slate-200"
            onClick={() => setQ(w)}
          >
            {w}
          </button>
        ))}
      </div>
    </form>
  );
}
