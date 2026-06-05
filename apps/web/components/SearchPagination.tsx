"use client";

import { useRouter, useSearchParams } from "next/navigation";

type Props = {
  page: number;
  totalPages: number;
  total: number;
};

export function SearchPagination({ page, totalPages, total }: Props) {
  const router = useRouter();
  const sp = useSearchParams();

  if (totalPages <= 1) return null;

  function go(p: number) {
    const next = new URLSearchParams(sp.toString());
    next.set("page", String(p));
    router.push(`/search?${next.toString()}`);
  }

  const pages: number[] = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let p = start; p <= end; p++) pages.push(p);

  return (
    <nav className="flex flex-col items-center gap-3 border-t border-slate-200 pt-6" aria-label="分页">
      <p className="text-sm text-slate-500">
        共 {total} 条，第 {page} / {totalPages} 页
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => go(page - 1)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          上一页
        </button>
        {start > 1 && (
          <>
            <button type="button" onClick={() => go(1)} className="rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100">
              1
            </button>
            {start > 2 && <span className="text-slate-400">…</span>}
          </>
        )}
        {pages.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => go(p)}
            className={`min-w-[2.25rem] rounded-lg px-2 py-1.5 text-sm ${
              p === page ? "bg-brand text-white" : "border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {p}
          </button>
        ))}
        {end < totalPages && (
          <>
            {end < totalPages - 1 && <span className="text-slate-400">…</span>}
            <button
              type="button"
              onClick={() => go(totalPages)}
              className="rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100"
            >
              {totalPages}
            </button>
          </>
        )}
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => go(page + 1)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          下一页
        </button>
      </div>
    </nav>
  );
}
