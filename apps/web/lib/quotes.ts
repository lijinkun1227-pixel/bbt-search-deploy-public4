/** 首页随机展示的经典台词 */
export type HeroQuote = {
  en: string;
  zh: string;
  attribution: string;
};

export const HERO_QUOTES: HeroQuote[] = [
  {
    en: "Bazinga!",
    zh: "逗你玩！",
    attribution: "Sheldon",
  },
  {
    en: "I'm not crazy. My mother had me tested.",
    zh: "我没疯，我妈带我去做过测试。",
    attribution: "Sheldon",
  },
  {
    en: "Soft kitty, warm kitty, little ball of fur…",
    zh: "软软的小猫，暖暖的小猫……",
    attribution: "Sheldon",
  },
  {
    en: "That's my spot.",
    zh: "那是我的专座。",
    attribution: "Sheldon",
  },
  {
    en: "Howard, you know me to be a very smart man.",
    zh: "霍华德，你知道我非常聪明。",
    attribution: "Sheldon",
  },
];

export function pickRandomQuote(): HeroQuote {
  return HERO_QUOTES[Math.floor(Math.random() * HERO_QUOTES.length)];
}
