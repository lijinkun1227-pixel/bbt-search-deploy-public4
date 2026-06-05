import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SearchItem } from "@/lib/api";

export type BasketItem = SearchItem & {
  clipId?: string;
  clipStatus?: "idle" | "pending" | "ready" | "failed";
  playUrl?: string;
};

type BasketState = {
  items: BasketItem[];
  add: (item: SearchItem) => void;
  remove: (lineId: number) => void;
  clear: () => void;
  updateClip: (lineId: number, data: Partial<BasketItem>) => void;
};

export const useBasket = create<BasketState>()(
  persist(
    (set, get) => ({
      items: [],
      add: (item) => {
        if (get().items.some((i) => i.line_id === item.line_id)) return;
        set({ items: [...get().items, { ...item, clipStatus: "idle" }] });
      },
      remove: (lineId) =>
        set({ items: get().items.filter((i) => i.line_id !== lineId) }),
      clear: () => set({ items: [] }),
      updateClip: (lineId, data) =>
        set({
          items: get().items.map((i) =>
            i.line_id === lineId ? { ...i, ...data } : i
          ),
        }),
    }),
    { name: "quote-basket" }
  )
);
