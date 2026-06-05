import type { Metadata } from "next";
import "./globals.css";
import { BasketDrawer } from "@/components/BasketDrawer";

export const metadata: Metadata = {
  title: "生活大爆炸 · 台词素材",
  description: "搜索台词，生成双语素材片段",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-5xl items-center justify-center px-4 py-4">
            <a href="/" className="text-center text-sm font-medium tracking-wide text-slate-700 hover:text-brand">
              The Big Bang Theory · 台词素材库
            </a>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl px-4 py-8 pb-48">{children}</main>
        <BasketDrawer />
      </body>
    </html>
  );
}
