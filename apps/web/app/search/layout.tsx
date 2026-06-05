import { Suspense } from "react";

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<p className="text-center text-slate-500">加载中…</p>}>
      {children}
    </Suspense>
  );
}
