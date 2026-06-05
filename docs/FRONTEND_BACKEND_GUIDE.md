# 前后端交互逻辑 · 小白复习手册

> 适用对象：非技术背景的产品/剪辑同学，想理解「点搜索后背后发生了什么」。
>
> 项目：生活大爆炸台词素材检索（按单词找视频切片）

---

## 1. 一句话概括

**浏览器里的网页（前端）负责界面；云上的 Python 服务（后端 API）负责查数据库、生成切片；数据库和文件存放在 Supabase。**

你在页面上点「搜索」，前端把关键词发给后端，后端去 Supabase 查台词，再把结果返回给页面显示。

---

## 2. 三个角色 + 各自干什么

```
┌─────────────┐      HTTP 请求       ┌─────────────┐      SQL 查询       ┌─────────────┐
│   前端 Web   │  ───────────────►  │  后端 API    │  ───────────────►  │  Supabase   │
│  (Next.js)   │  ◄───────────────  │  (FastAPI)   │  ◄───────────────  │  数据库+存储  │
│  用户看到的   │      JSON 数据       │  业务逻辑     │      台词/切片元数据  │  台词+视频文件 │
└─────────────┘                      └─────────────┘                      └─────────────┘
```

| 角色 | 技术 | 代码位置 | 本地地址 | 线上地址（示例） |
|------|------|----------|----------|------------------|
| 前端 | Next.js + React | `apps/web/` | `http://localhost:3000` | `https://search-p.netlify.app` |
| 后端 API | Python FastAPI | `apps/api/` | `http://localhost:8000` | `https://bigbang-quote-api.onrender.com` |
| 数据层 | Supabase (PostgreSQL + Storage) | `supabase/` | 云端，无本地 | `https://xxx.supabase.co` |

**重要**：前端**不直接**连 Supabase 数据库（安全策略 RLS 禁止），所有数据都通过后端 API 中转。

---

## 3. 前端如何找到后端？——环境变量

前端所有请求的发送地址，由这一行决定（`apps/web/lib/api.ts`）：

```ts
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

| 场景 | `NEXT_PUBLIC_API_URL` 填什么 |
|------|------------------------------|
| 本机开发 | `http://localhost:8000`（写在 `apps/web/.env.local`） |
| Netlify 线上 | `https://bigbang-quote-api.onrender.com`（写在 Netlify 环境变量） |

`NEXT_PUBLIC_` 前缀表示：这个值会在**构建时**写进前端代码，浏览器里能用到。

---

## 4. 核心用户流程（按页面）

### 4.1 首页 `/`

```
用户打开首页
    → HomeContent 组件加载
    → 调用 fetchFeatured()  →  GET /api/featured?limit=9
    → 后端从 Supabase 随机取已有视频切片
    → 返回 JSON，首页展示 9 个预览卡片

用户输入关键词点「搜索」
    → SearchBar 用 router.push 跳转到 /search?q=xxx
    （这是前端路由，不经过后端）
```

### 4.2 搜索页 `/search?q=bazinga`

```
URL 参数变化（q、lang、page）
    → useEffect 触发
    → 调用 searchQuotes({ q, lang, page })
    →  GET /api/search?q=bazinga&lang=both&page=1&...
    → 后端在 subtitle_lines 表里做全文/整词匹配
    → 返回 { total, items[], page, total_pages }
    → ResultCard 列表渲染

用户点击某条结果
    → 打开 ClipDetailOverlay 浮层
    → 可预览台词、加入素材篮、尝试生成切片
```

### 4.3 生成视频切片（素材篮）

```
用户在素材篮点「生成视频片段」
    → createClips([line_id, ...])
    →  POST /api/clips  { line_ids, padding_ms }
    → 后端用 FFmpeg 从本地/服务器源视频裁切
    → 上传到 Supabase Storage（clips 桶）
    → 返回 clip_id、play_url

⚠️ 线上 Render 实例没有你的 MKV 源文件，此功能线上通常不可用；
   本机同时跑 API + 放好源视频时可用。
```

### 4.4 分享页 `/s/[shareId]`

```
用户打开分享链接
    → getShare(shareId)
    →  GET /api/share/{shareId}
    → 后端查 share_bundles 表，返回台词列表和关联切片
```

---

## 5. 后端 API 接口一览

| 方法 | 路径 | 前端调用函数 | 是否访问数据库 |
|------|------|--------------|----------------|
| GET | `/health` | （部署自检用） | ❌ |
| GET | `/api/search` | `searchQuotes()` | ✅ |
| GET | `/api/featured` | `fetchFeatured()` | ✅ |
| POST | `/api/clips` | `createClips()` | ✅ + FFmpeg + Storage |
| GET | `/api/clips/{id}` | `getClip()` | ✅ |
| POST | `/api/share` | `createShare()` | ✅ |
| GET | `/api/share/{id}` | `getShare()` | ✅ |

完整说明见 [`API.md`](./API.md)。

---

## 6. 后端内部怎么处理搜索？

以搜索 `bazinga` 为例：

```
浏览器  GET /api/search?q=bazinga
    ↓
apps/api/routers/search.py        接收参数、校验
    ↓
apps/api/services/search_service.py
    → 拼 SQL（英文整词用正则 \ybazinga\y）
    → apps/api/db.py  get_conn() 连接 Supabase
    → 查 subtitle_lines JOIN episodes
    → 高亮关键词，组装 JSON
    ↓
返回给前端
```

---

## 7. 跨域（CORS）——为什么需要配？

浏览器的安全规则：**网页只能随便请求「自己域名」的接口**。

- 前端在 `https://search-p.netlify.app`
- API 在 `https://bigbang-quote-api.onrender.com`

域名不同，后端必须明确「允许 Netlify 来访问」，否则浏览器会拦截请求。

后端通过 `PUBLIC_WEB_URL` 和 `CORS_ORIGINS` 配置允许的域名（`apps/api/config.py`）。

---

## 8. 环境变量分工（最容易混的地方）

| 变量 | 给谁用 | 填在哪 |
|------|--------|--------|
| `NEXT_PUBLIC_API_URL` | 前端 → 知道 API 地址 | `apps/web/.env.local` / **Netlify** |
| `SUPABASE_URL` | 后端连 Supabase | `deploy/.env` / **Render** |
| `SUPABASE_SERVICE_ROLE_KEY` | 后端高权限密钥 | `deploy/.env` / **Render** |
| `DATABASE_URL` | 后端连 PostgreSQL | `deploy/.env` / **Render** |
| `PUBLIC_WEB_URL` | 后端 CORS 允许的前端地址 | `deploy/.env` / **Render** |
| `SOURCE_VIDEO_ROOT` | 后端找源视频切片 | 本机 `deploy/.env` |

**口诀**：

- **Netlify 只放一行** `NEXT_PUBLIC_API_URL`
- **Render 放后端那一套**（Supabase 相关）
- **不要把** `SERVICE_ROLE_KEY` 放到 Netlify

---

## 9. 本地 vs 线上对照

| | 本地开发 | 线上 |
|--|----------|------|
| 启动前端 | `cd apps/web && npm run dev` | Netlify 自动构建部署 |
| 启动后端 | `uvicorn apps.api.main:app --reload --port 8000` | Render 常驻进程 |
| 配置文件 | `.env.local` + `deploy/.env` | 各平台网页后台环境变量 |
| 源视频 | 本机硬盘 `SOURCE_VIDEO_ROOT` | Render 免费实例无源视频 |
| 谁能访问 | 仅本机 `localhost:3000` | 公网任何人 |

---

## 10. 自检清单（出问题时按顺序查）

1. **页面能开，搜索失败** → 查 `NEXT_PUBLIC_API_URL`、Render API `/health`、Render Logs
2. **浏览器 Console 报 CORS** → 查 Render 的 `PUBLIC_WEB_URL` 是否等于 Netlify 地址
3. **`/health` 正常，搜索 500** → 查 Render 的 `DATABASE_URL` 是否与本机 `deploy/.env` 一致
4. **构建失败** → 查 Netlify Deploy log（多为代码或 `netlify.toml` 配置）
5. **切片生成失败** → 线上预期行为；本机需 FFmpeg + 源视频

---

## 11. 相关文档

- [`API.md`](./API.md) — 接口字段说明
- [`DEPLOY_NETLIFY_RENDER.md`](./DEPLOY_NETLIFY_RENDER.md) — 部署操作步骤
- [`DEPLOY_LESSONS_LEARNED.md`](./DEPLOY_LESSONS_LEARNED.md) — 本次上线踩坑总结
