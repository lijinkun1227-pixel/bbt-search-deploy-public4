# 《生活大爆炸》台词素材检索 — 产品实现手册

> **文档版本**：v1.1（数据库：**Supabase**）  
> **适用场景**：个人学习 / 课程 Demo / 小团队内部工具  
> **Supabase 入门**：先看 [`docs/SUPABASE_SETUP.md`](SUPABASE_SETUP.md)  
> **AI Coding 用法**：按章节顺序推进；每完成一节在 `docs/CHANGELOG.md` 打勾；向 Cursor 提问时 `@` 本文件 + `@docs/SUPABASE_SETUP.md`。

---

## 目录

1. [产品边界与成功标准](#1-产品边界与成功标准)
2. [技术架构（含模块注释）](#2-技术架构含模块注释)
3. [语料库建设方案](#3-语料库建设方案)
4. [数据存储与对象存储方案（低成本）](#4-数据存储与对象存储方案低成本)
5. [后端模块与 API 契约](#5-后端模块与-api-契约)
6. [前端设计（MVP + 数据流 + 交互）](#6-前端设计mvp--数据流--交互)
7. [视频切片与素材关系流水线](#7-视频切片与素材关系流水线)
8. [分阶段实现清单（AI Coding 行动表）](#8-分阶段实现清单ai-coding-行动表)
9. [部署方案（可实施、低运维）](#9-部署方案可实施低运维)
10. [风险、合规与备选路径](#10-风险合规与备选路径)
11. [附录](#11-附录)

---

## 1. 产品边界与成功标准

### 1.1 MVP 做什么

| 能力 | MVP | 二期 |
|------|-----|------|
| 关键词搜索台词（中/英/或双语） | ✅ | 模糊音译、同义词 |
| 展示季/集/时间码/上下文 | ✅ | 角色筛选 |
| 勾选多条 → 素材篮 | ✅ | 跨剧集收藏夹 |
| 分享链接（只读页） | ✅ | 短链 + 密码 |
| 双语对照展示 | ✅ | 用户切换主语言 |
| 按时间轴生成短视频片段 | ✅（异步） | GIF、水印 |
| 用户账号 / 付费 | ❌ | 视需求 |

### 1.2 非目标（防止 scope creep）

- 不提供完整剧集在线播放与下载整集
- 不做 UGC 上传剧集
- 不做推荐算法 Feed
- 不做移动端原生 App（响应式 Web 即可）

### 1.3 验收标准（里程碑）

| 阶段 | 验收 |
|------|------|
| M1 数据 | 至少 1 季双语入库；CLI 搜索 < 300ms |
| M2 API | `GET /search` 与 CLI 结果一致 |
| M3 前端 | 浏览器完成：搜索 → 勾选 → 分享页可打开 |
| M4 切片 | 选 1 条 → 2 分钟内可在分享页预览 clip |
| M5 部署 | 公网 HTTPS 可访问；Supabase Storage 可上传/播放 clip |

---

## 2. 技术架构（含模块注释）

> 说明：下文「技术架构」按**可演进的分层**设计；注释写在架构图与模块表中，便于 Cursor 生成代码时对齐职责。

### 2.1 总体架构图

```mermaid
flowchart TB
  subgraph Client["客户端层"]
    WEB["Web App (Next.js)\n搜索 / 素材篮 / 分享页"]
  end

  subgraph Gateway["接入层"]
    NGINX["Nginx / Caddy\nHTTPS 反向代理"]
  end

  subgraph App["应用层"]
    API["API Service (FastAPI 或 Next Route)\n搜索 / 素材篮 / 分享 / 任务下发"]
    WORKER["Clip Worker\nFFmpeg 切片 + 上传对象存储"]
  end

  subgraph Data["数据层（Supabase 云）"]
    SB[("Supabase PostgreSQL\n台词 / 索引 / clip 元数据")]
    ST["Supabase Storage\n桶 clips：切片 mp4"]
  end

  subgraph Local["本机 / VPS（仅计算）"]
    REDIS[("Redis 可选\n切片任务队列")]
    SRC["源视频目录\nSOURCE_VIDEO_ROOT"]
  end

  subgraph Pipeline["离线流水线 (不在请求路径)"]
    INGEST["ingest: 字幕解析 + 入库"]
    ALIGN["align: 双语对齐"]
    INDEX["index: 全文检索刷新"]
    PRECLIP["preclip: 批量预热常用片段 可选"]
  end

  WEB --> NGINX --> API
  API --> SB
  API --> ST
  API --> REDIS
  REDIS --> WORKER
  WORKER --> SRC
  WORKER --> ST
  WORKER --> SB
  INGEST --> SB
  ALIGN --> SB
  INDEX --> SB
  PRECLIP --> ST
```

### 2.2 逻辑分层与职责（带注释）

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation  展示层                                        │
│  - pages: 搜索页、分享页                                      │
│  - components: 结果卡片、素材篮、播放器                       │
│  注释: 只做展示与交互，不直连数据库；只调 API                   │
├─────────────────────────────────────────────────────────────┤
│  Application   应用层                                        │
│  - SearchService: 查询、高亮、分页                            │
│  - ClipService: 创建切片任务、查询 clip_url                   │
│  - ShareService: 编码/解码分享 payload                        │
│  注释: 业务规则集中在此，便于单测                               │
├─────────────────────────────────────────────────────────────┤
│  Domain        领域层                                        │
│  - SubtitleLine, ClipAsset, ShareBundle 实体                  │
│  - 时间轴校验、去重规则（同集同起止时间）                        │
│  注释: 与框架无关的纯逻辑                                       │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure 基础设施层                                   │
│  - SubtitleRepository, ClipRepository                        │
│  - SupabaseClient (DB + Storage 封装)                        │
│  - JobQueue (Redis + worker，或 DB 轮询 clip_assets)           │
│  注释: Supabase 换账号/桶名只改这一层；密钥仅用 service_role    │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 仓库目录规划（Monorepo）

```text
bigbang-quote-finder/
├── apps/
│   ├── web/                 # Next.js 前端
│   └── api/                 # FastAPI（推荐）或 web/app/api
├── packages/
│   └── shared/              # 共享类型、常量、时间工具
├── pipeline/                # 离线语料脚本（Python）
│   ├── parse_srt.py
│   ├── align_bilingual.py
│   ├── import_supabase.py
│   └── clip_worker.py
├── supabase/
│   └── migrations/          # SQL 迁移（Dashboard 或 CLI 执行）
├── deploy/
│   ├── docker-compose.yml   # 仅 api / worker / redis（无自建 PG）
│   ├── .env.example
│   └── nginx.conf
├── docs/
│   ├── PRODUCT_IMPLEMENTATION_MANUAL.md   # 本文件
│   ├── SUPABASE_SETUP.md    # Supabase 创建与密钥配置
│   ├── API.md
│   ├── DATA_SCHEMA.md
│   └── designs/             # 页面设计稿放这里
└── .cursor/
    └── rules/               # AI 编码规范
```

### 2.4 技术选型（固定，减少 Cursor 摇摆）

| 层级 | 选型 | 注释 |
|------|------|------|
| 前端 | Next.js 14 + TypeScript + Tailwind | App Router；分享页可 SSG |
| 后端 | FastAPI + Python 3.11 | 字幕/FFmpeg 生态好；与 pipeline 同语言 |
| 主库 | **Supabase**（托管 PostgreSQL + `pg_trgm` / tsvector） | 免运维；Table Editor 可视化管理 |
| 切片文件 | **Supabase Storage** 桶 `clips` | 与数据库同账号；免费档够 Demo |
| 队列 | Redis 7（本机/VPS）或 DB 轮询 | 小白可先 DB 轮询，省去 Redis |
| 切片 | FFmpeg 6 | 在 Worker 本机读 `SOURCE_VIDEO_ROOT` |
| 部署 | Supabase 云 + 轻量 VPS/本机 Worker | 见第 9 章；**可不自建数据库** |

### 2.5 运行时数据流（在线请求）

```mermaid
sequenceDiagram
  participant U as 用户
  participant W as Web
  participant A as API
  participant DB as Supabase DB
  participant ST as Supabase Storage
  participant Q as Redis
  participant K as Clip Worker

  U->>W: 输入关键词
  W->>A: GET /api/search?q=
  A->>DB: FTS 查询 subtitle_lines
  DB-->>A: 行列表 + 高亮 snippet
  A-->>W: JSON 结果

  U->>W: 勾选台词 → 生成片段
  W->>A: POST /api/clips {line_ids, padding_ms}
  A->>DB: 查 clip_assets 是否 ready
  alt 已有且 status=ready
    A->>ST: create signed URL（私有桶）
    A-->>W: play_url
  else 未生成
    A->>DB: insert clip_assets pending
    A->>Q: push clip_id
    A-->>W: 202 + clip_id
    Q->>K: consume
    K->>K: FFmpeg 从 SOURCE_VIDEO_ROOT 切片
    K->>ST: upload clips/{id}.mp4
    K->>DB: storage_path + status=ready
    W->>A: GET /api/clips/{id} 轮询
    A->>ST: signed URL
    A-->>W: ready + play_url
  end
```

---

## 3. 语料库建设方案

### 3.1 语料组成

| 资产类型 | 格式 | 用途 | 是否进对象存储 |
|----------|------|------|----------------|
| 原始字幕 | `.srt` / `.ass` | 解析、双语、搜索 | ❌ 解析后入库即可 |
| 原始视频 | `.mp4` / `.mkv` | FFmpeg 切片源 | ⚠️ 见 3.4 |
| 结构化台词 | DB 行 | 搜索、展示 | **Supabase PostgreSQL** |
| 切片素材 | `.mp4`（5–30s） | 预览、分享、下载 | ✅ **Supabase Storage** |
| 缩略图 | `.jpg` 可选 | 卡片封面 | ✅ Supabase Storage |

### 3.2 字幕：获取渠道与操作步骤

> **合规**：仅使用你有权使用的字幕；公开产品需注明来源与版权声明。课程 Demo 建议规模可控、不对外传播整集。

#### 推荐来源（按优先级）

| 来源 | 说明 | 操作 |
|------|------|------|
| **OpenSubtitles.org** | 社区字幕，量全；需注册 API | 1. 注册 → API Key<br>2. 按 `The Big Bang Theory` + SxxExx 搜索<br>3. 下载 EN + ZH-CN/ZH.srt<br>4. 使用 `pipeline/download_opensubtitles.py`（Cursor 实现）批量拉取 |
| **Subscene / podnapisi** | 备用；注意站点可用性 | 手动补缺失集 |
| **自有转录** | 无法律风险 | Whisper 对自有视频转写（成本高，作补充） |

**命名规范（强制）**：

```text
data/raw/subtitles/
  en/S01E01.srt
  zh/S01E01.srt
```

**OpenSubtitles API 注意**：

- 遵守速率限制；本地缓存已下载文件，避免重复请求
- 记录 `file_id` / `upload_date` 到 `subtitle_sources` 表便于溯源

#### 字幕解析规则

1. 时间统一为 **毫秒整数** `start_ms`, `end_ms`
2. 去掉 HTML 标签、音乐符号 `♪`
3. 合并极短相邻行（< 500ms 且同说话人可配置）
4. 生成 `line_hash = sha1(season|episode|start_ms|text_en_normalized)`

### 3.3 双语对齐策略

```mermaid
flowchart LR
  EN[英文字幕行] --> M{按时间重叠匹配}
  ZH[中文字幕行] --> M
  M -->|overlap > 50%| OK[写入 text_zh]
  M -->|无匹配| MISS[text_zh = null flag]
```

**算法要点**：

- 对每条 EN 行，找 ZH 行使得 `overlap_duration / en_duration > 0.5`
- 一对多：取重叠最长的 ZH
- 写入 `subtitle_lines.align_confidence`（0–1）供前端展示「机翻对齐」提示

### 3.4 视频：获取渠道与存放策略（低成本核心）

> **重要**：本手册**不推荐**任何盗版站点链接。视频应来自：**你已购买的蓝光/Digital Copy、录制权许可内容、或课程提供的样例集**。

| 策略 | 描述 | 成本 | MVP 建议 |
|------|------|------|----------|
| **A. 用户自备源视频（推荐）** | 视频仅存在于**服务器本地目录** `SOURCE_VIDEO_ROOT`，不上传对象存储 | 最低 | ✅ 默认 |
| **B. 样例集** | 仅入库 1–2 季用于 Demo | 低 | ✅ 与 A 结合 |
| **C. 全量上云源视频** | 12 季全量 MP4 放对象存储 | 极高（数百 GB） | ❌ 不做 |

**源视频目录约定**：

```text
/data/source_videos/          # 不提交 git，不对外暴露 HTTP
  S01E01.mp4
  S01E02.mp4
```

`episodes` 表字段：`source_video_path` 或 `source_video_key`（若未来上云）。

### 3.5 语料建设流水线（离线，分步执行）

| 步骤 | 脚本 | 输入 | 输出 |
|------|------|------|------|
| 1 下载字幕 | `pipeline/01_fetch_subtitles.py` | OpenSubtitles API | `data/raw/subtitles/**` |
| 2 解析 | `pipeline/02_parse_srt.py` | raw srt | `data/staging/lines.jsonl` |
| 3 对齐 | `pipeline/03_align_bilingual.py` | jsonl en+zh | `data/staging/lines_aligned.jsonl` |
| 4 入库 | `pipeline/04_import_supabase.py` | jsonl + `DATABASE_URL` | Supabase `subtitle_lines` |
| 5 建索引 | `pipeline/05_refresh_search_index.py` | Supabase | GIN / tsvector 触发器 |
| 6 注册剧集 | `pipeline/06_register_episodes.py` | 视频目录扫描 | `episodes` 表 |
| 7 预热切片 可选 | `pipeline/07_preclip_popular.py` | 热词 Top N | `clip_assets` |

**执行顺序（AI Coding 每次只做一步）**：

```bash
# 示例：在 pipeline 目录
python 01_fetch_subtitles.py --season 1
python 02_parse_srt.py --season 1
python 03_align_bilingual.py --season 1
python 04_import_supabase.py --season 1
python 05_refresh_search_index.py
python 06_register_episodes.py --root /data/source_videos
```

### 3.6 语料质量检查清单

- [ ] 每集 EN 行数 > 0，且 `duration` 与视频长度误差 < 5%
- [ ] 随机抽 20 条：双语时间对齐肉眼可接受
- [ ] 搜索 `bazinga`、`penny`、`谢尔顿` 有合理命中
- [ ] `episodes` 中每集 `has_source_video=true` 比例可查

---

## 4. 数据存储方案（Supabase + 本地源视频）

### 4.1 原则

| 存什么 | 存哪里 | 原因 |
|--------|--------|------|
| 台词文本、时间、季集、索引、clip 元数据 | **Supabase PostgreSQL** | 免自建库；Dashboard 可视化管理 |
| 切片 mp4、缩略图 | **Supabase Storage**（桶 `clips`） | 与 DB 同一项目；免费档够 Demo |
| 原始全集 mp4 | **本机 / VPS** `SOURCE_VIDEO_ROOT` | 不上云，避免存储费爆炸 |
| 原始 srt | 解析后可删 | 可选写入 `subtitle_sources` |

> **新手第一步**：按 [`docs/SUPABASE_SETUP.md`](SUPABASE_SETUP.md) 创建项目、执行迁移、创建 `clips` 桶。

### 4.2 数据库表结构

完整 SQL 见：**`supabase/migrations/001_initial_schema.sql`**（在 Supabase SQL Editor 执行）。

与旧版差异摘要：

| 表 | 说明 |
|----|------|
| `episodes` | 季集元数据；`source_video_path` 为 Worker 本机路径 |
| `subtitle_lines` | 搜索主体；`search_vector` 由触发器维护 |
| `clip_assets` | 用 `storage_path`（如 `clips/{uuid}.mp4`）关联 Storage，不再使用 MinIO `bucket` 字段 |
| `share_bundles` | 分享 ID 与 `line_ids` / `clip_ids` |
| RLS | 默认开启；分享表可设匿名只读策略（见迁移文件） |

### 4.3 后端如何连接 Supabase

| 场景 | 方式 | 密钥 |
|------|------|------|
| FastAPI / pipeline / Worker | `supabase-py` 或 `asyncpg` + `DATABASE_URL` | **service_role**（仅服务端） |
| Next.js 读分享页（可选） | `@supabase/supabase-js` | **anon** + RLS 策略 |
| 上传切片 | `storage.from('clips').upload(...)` | service_role |
| 播放私有桶 | `createSignedUrl(path, 3600)` | API 返回给前端 |

**禁止**：在浏览器或前端环境变量中放置 `service_role`。

### 4.4 Supabase Storage 路径约定

```text
Bucket: clips   （与 SUPABASE_STORAGE_BUCKET 一致）
  clips/{clip_asset_id}.mp4
  thumbs/{clip_asset_id}.jpg   # 可选
```

- **Public 桶（MVP）**：`getPublicUrl` 即可播放，配置最简单  
- **Private 桶（推荐正式）**：仅 API 签发 signed URL  

### 4.5 成本对比（小白友好）

| 方案 | 月成本 | 说明 |
|------|--------|------|
| **Supabase 免费档 + 本机源视频** | **$0 起** | 数据库 + Storage 有配额；够课程 Demo |
| 自建 VPS PostgreSQL + MinIO | ¥80–120 | 运维高；手册 v1.0 方案，已弃用为默认 |
| 源视频上传 Supabase | 很高 | **禁止** |

假设累计生成约 **10GB** 切片：落在 Supabase Storage 免费额度内时需关注官方限额；超出再考虑 Pro 或迁 R2。

**结论**：**Supabase 管库 + 管短片；本机只管全集源视频与 FFmpeg**。

---

## 5. 后端模块与 API 契约

### 5.1 模块拆分（实现时按包创建）

| 模块路径 | 职责 |
|----------|------|
| `api/routers/search.py` | 搜索、筛选、高亮 |
| `api/routers/clips.py` | 创建任务、查询状态、预签名 URL |
| `api/routers/share.py` | 创建/获取分享 bundle |
| `api/services/search_service.py` | 组装 SQL、snippet |
| `api/services/clip_service.py` | 幂等创建 clip、查缓存 |
| `api/adapters/supabase_client.py` | Supabase DB + Storage 封装 |
| `pipeline/clip_worker.py` | 消费 Redis、调 FFmpeg |

### 5.2 API 列表（MVP）

#### `GET /api/search`

| 参数 | 类型 | 说明 |
|------|------|------|
| q | string | 关键词，必填 |
| lang | en \| zh \| both | 搜索字段 |
| season | int? | 筛选 |
| episode | int? | 筛选 |
| page | int | 默认 1 |
| page_size | int | 默认 20，最大 50 |

**响应示例**：

```json
{
  "total": 120,
  "items": [{
    "line_id": 1001,
    "season": 1,
    "episode": 1,
    "start_ms": 125000,
    "end_ms": 128500,
    "text_en": "I'm not crazy. My mother had me tested.",
    "text_zh": "我没疯，我妈带我去做过测试。",
    "snippet_en": "I'm not <em>crazy</em>...",
    "snippet_zh": null,
    "has_clip": false
  }]
}
```

#### `POST /api/clips`

```json
{ "line_ids": [1001], "padding_ms": 500 }
```

- 返回：`{ "jobs": [{ "clip_id": "uuid", "status": "pending" }] }`  
- 已存在 `ready`：直接 `{ "clip_id", "status": "ready", "play_url": "..." }`

#### `GET /api/clips/{clip_id}`

- `status`, `play_url`（signed）, `error_message`

#### `POST /api/share`

```json
{ "line_ids": [1001, 1002], "clip_ids": ["uuid"] }
```

- 返回：`{ "share_id": "uuid", "url": "https://app.example.com/s/xxx" }`

#### `GET /api/share/{share_id}`

- 返回 bundle 详情（台词 + clip play_url）

### 5.3 FFmpeg 切片参数（固定写入 worker）

```bash
ffmpeg -y \
  -ss {start_sec} -to {end_sec} -i "{source_video_path}" \
  -c:v libx264 -preset veryfast -crf 23 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  "{output_path}"
```

`start_sec = (line.start_ms - padding_ms) / 1000`，下限 0。

---

## 6. 前端设计（MVP + 数据流 + 交互）

> **设计稿**：请将 Figma/截图放到 `docs/designs/`，命名：  
> `01-search.png`、`02-results.png`、`03-basket.png`、`04-share.png`。  
> Cursor 实现时：`@docs/designs/01-search.png` + 本章交互说明。

### 6.1 信息架构（页面）

```text
/                 → 搜索首页（含历史热词）
/search?q=        → 搜索结果页
/basket           → 素材篮（可用全局侧栏代替路由）
/s/{shareId}      → 分享只读页（无需登录）
```

### 6.2 页面状态与数据流

```mermaid
stateDiagram-v2
  [*] --> Home
  Home --> Searching: 提交关键词
  Searching --> Results: API success
  Searching --> Error: API fail
  Results --> Results: 翻页/筛选
  Results --> Basket: 勾选 add
  Basket --> Clipping: 生成片段
  Clipping --> Basket: 轮询 ready
  Basket --> ShareCreated: 创建分享
  ShareCreated --> [*]
```

**全局状态（推荐 Zustand）**：

```typescript
// packages/shared/types.ts 概念
interface BasketItem {
  lineId: number;
  season: number;
  episode: number;
  textEn: string;
  textZh?: string;
  startMs: number;
  endMs: number;
  clipId?: string;
  clipStatus?: 'idle' | 'pending' | 'ready' | 'failed';
  playUrl?: string;
}
```

### 6.3 页面交互细则

#### 6.3.1 首页 `/`

| 元素 | 行为 |
|------|------|
| 搜索框 | Enter 或点搜索 → `router.push(/search?q=)` |
| 语言切换 | `both` / `en` / `zh`，写入 query `lang=` |
| 热词 chips | 点击填入 `bazinga`、`roommate agreement` 等 |
| 空状态 | 展示使用说明 + 版权提示 |

#### 6.3.2 搜索结果页 `/search`

| 元素 | 行为 |
|------|------|
| 结果卡片 | 左：季集标签 + 时间码；中：双语（关键词高亮）；右：操作区 |
| 高亮 | 使用 API `snippet_*` HTML，前端 `dangerouslySetInnerHTML` 需 sanitize |
| 「加入素材篮」 | toggle；已选显示勾选态；写入 localStorage + Zustand |
| 「预览上下文」 | 展开前后各 1 行（API `context` 字段或二次请求） |
| 筛选 | 季下拉、集下拉 → 重新请求 |
| 分页 | 触底或分页器 → `page++` |
| 加载 | 骨架屏；>300ms 显示 loading |

#### 6.3.3 素材篮（侧栏或 `/basket`）

| 元素 | 行为 |
|------|------|
| 列表 | 按添加顺序；可删除、清空 |
| 批量生成片段 | 对无 `clipId` 项 `POST /api/clips`；pending 显示 spinner |
| 轮询 | 每 2s `GET /api/clips/{id}`，ready 后嵌入 `<video controls>` |
| 复制文本 | 复制 Markdown：`[S01E01 00:02:05] EN / ZH` |
| 创建分享 | `POST /api/share` → toast 显示链接 + 复制按钮 |

#### 6.3.4 分享页 `/s/{shareId}`

| 元素 | 行为 |
|------|------|
| 只读 | 无编辑；展示创建时间与条数 |
| 每条 | 双语 + 内嵌播放器（signed url 过期则显示「刷新页面」） |
| 二次传播 | 浏览器原生分享或复制链接 |

### 6.4 组件清单（实现顺序）

1. `SearchBar`  
2. `ResultCard`  
3. `BasketDrawer`  
4. `ClipPlayer`  
5. `SharePageLayout`  
6. `FilterSeasonEpisode`  

### 6.5 与设计稿对齐检查表

- [ ] 主色、字号、圆角与稿一致（写入 `tailwind.config` token）  
- [ ] 移动端：素材篮变底部抽屉  
- [ ] 双语排版：上下堆叠 vs 左右栏（以设计稿为准）  

---

## 7. 视频切片与素材关系流水线

```mermaid
flowchart TD
  A[用户请求 line_id] --> B{clip_assets 存在且 ready?}
  B -->|是| C[返回预签名 URL]
  B -->|否| D[插入 clip_assets pending]
  D --> E[Redis 入队]
  E --> F[Worker 取 episode.source_video_path]
  F --> G{文件存在?}
  G -->|否| H[status=failed NO_SOURCE]
  G -->|是| I[FFmpeg 切片]
  I --> J[上传 Supabase Storage]
  J --> K[更新 DB ready + storage_path]
  K --> C
```

**幂等**：`UNIQUE(subtitle_line_id, padding_ms)` 防止重复切片浪费存储。

---

## 8. 分阶段实现清单（AI Coding 行动表）

> 每次向 Cursor 提交任务时复制对应「Prompt 模板」。

### Phase 0：初始化（0.5 天）

- [ ] 创建 monorepo 目录、`docker-compose.yml` 骨架  
- [ ] `.cursor/rules`：Python/TS 规范、时间单位 ms  
- [ ] `docs/API.md` 从第 5 章同步  

**Prompt 模板**：

```text
按 @docs/PRODUCT_IMPLEMENTATION_MANUAL.md 第 2.3 节创建 monorepo 骨架，
包含 apps/web (Next.js)、apps/api (FastAPI)、pipeline/、deploy/，不写业务逻辑。
```

### Phase 1：Supabase 与字幕管道（3–5 天）

- [ ] 按 `docs/SUPABASE_SETUP.md` 创建项目并执行 `supabase/migrations/001_initial_schema.sql`  
- [ ] 配置 `deploy/.env` 中 `DATABASE_URL` / `SUPABASE_URL` / `service_role`  
- [ ] 实现 `02_parse_srt` ~ `04_import_supabase`  
- [ ] 实现 `05_refresh_search_index`  
- [ ] 在 Supabase Table Editor 确认有数据；CLI：`python -m pipeline.search "bazinga"`  

**Prompt 模板**：

```text
实现 pipeline/02_parse_srt.py，输入 data/raw/subtitles/en/S01E01.srt，
输出符合 DATA_SCHEMA 的 jsonl，附 pytest。
```

### Phase 2：搜索 API（1 天）

- [ ] `GET /api/search`  
- [ ] 单元测试：已知 line 必须能搜到  

### Phase 3：前端搜索与素材篮（3 天）

- [ ] 首页 + 结果页 + Zustand 篮  
- [ ] 对接 search API  

### Phase 4：Supabase Storage + Clip Worker（3–4 天）

- [ ] Storage 创建桶 `clips` 并配置策略（见 SUPABASE_SETUP）  
- [ ] `supabase_client.py` + `clip_worker.py`（上传 + 更新 `clip_assets`）  
- [ ] `POST/GET /api/clips`（signed URL）  
- [ ] 前端轮询与播放器  

### Phase 5：分享（1 天）

- [ ] `share_bundles` + 分享页 SSG  

### Phase 6：部署上线（1–2 天）

- [ ] 按第 9 章执行  

---

## 9. 部署方案（Supabase + 轻量计算）

### 9.1 目标拓扑

```text
        Internet
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌─────────────┐  ┌──────────────────────────┐
│  Supabase   │  │  VPS 或 本机（开发期）     │
│  (云端)     │  │  Next.js :3000           │
│  PostgreSQL │  │  FastAPI :8000           │
│  Storage    │  │  Clip Worker + FFmpeg    │
│             │  │  Redis（可选）            │
│             │  │  /data/source_videos     │
└─────────────┘  └──────────────────────────┘
```

- **数据库、切片文件**：不在 VPS 上自建，由 Supabase 托管  
- **VPS/本机**：只跑网站、API、切片 Worker；**源视频放本地盘**

**月成本参考**：

| 组件 | 成本 |
|------|------|
| Supabase Free | $0（有配额限制） |
| VPS（仅 Web+Worker，1C2G 可起步） | ¥30–50，或开发期仅用本机 $0 |
| 源视频磁盘 | 自有硬盘，不计入云账单 |

### 9.2 环境变量（`deploy/.env`）

见 **`deploy/.env.example`**。必填：

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
DATABASE_URL=postgresql://postgres.xxx:...@....pooler.supabase.com:6543/postgres
SUPABASE_STORAGE_BUCKET=clips
SOURCE_VIDEO_ROOT=/data/source_videos
PUBLIC_WEB_URL=https://your-domain.com
```

### 9.3 部署步骤（推荐顺序）

#### A. 仅本地开发（零 VPS，最适合小白）

1. 完成 [`docs/SUPABASE_SETUP.md`](SUPABASE_SETUP.md)  
2. 本地 `cp deploy/.env.example deploy/.env` 并填入 Supabase 密钥  
3. 跑 pipeline 导入 1 季字幕  
4. `cd apps/api && uvicorn main:app --reload`  
5. `cd apps/web && npm run dev`  
6. 本机放 1 个 `S01E01.mp4` 到 `SOURCE_VIDEO_ROOT`，测试切片上传 Storage  

#### B. 公网访问（Vercel + Supabase + 家用/云 Worker）

| 组件 | 部署位置 |
|------|----------|
| Next.js | **Vercel**（连 `NEXT_PUBLIC_SUPABASE_*` 可选） |
| FastAPI | **Railway / Render / 小 VPS** |
| Clip Worker | **必须**能访问 `SOURCE_VIDEO_ROOT` 的机器（VPS 挂盘） |
| DB + clips | **Supabase**（已就绪） |

步骤摘要：

1. Supabase 项目 + 迁移 + `clips` 桶  
2. 本地 pipeline 导入全库（`DATABASE_URL` 指向 Supabase）  
3. 部署 API，环境变量注入 `SUPABASE_*`  
4. 部署 Web，配置 `API_BASE_URL`  
5. Worker 同机部署，挂载源视频目录  
6. 冒烟：搜索 → 生成 clip → Storage 有文件 → 分享页可播  

#### C. 单机 Docker（仅 api / web / worker / redis）

`docker-compose.yml` **不再包含** postgres、minio。示例服务：

| 服务 | 说明 |
|------|------|
| web | Next.js |
| api | FastAPI，环境变量指向 Supabase |
| worker | FFmpeg + 上传 Storage |
| redis | 可选任务队列 |
| caddy | HTTPS 反代 |

### 9.4 日常运维

| 任务 | 方式 |
|------|------|
| 看数据 | Supabase **Table Editor** |
| 看切片文件 | Supabase **Storage** 面板 |
| DB 备份 | Supabase 自动备份（Pro）或 `pg_dump` 连 `DATABASE_URL` |
| 清理失败 clip | SQL 删 `clip_assets` + Storage 删对象 |
| 日志 | VPS：`docker compose logs api worker` |

### 9.5 扩容路径

| 瓶颈 | 动作 |
|------|------|
| Supabase 容量/连接数 | 升级 Pro；或只把 Storage 迁 R2 |
| 切片慢 | 增加 Worker 实例 + Redis |
| 搜索慢 | Supabase 加索引；二期 Meilisearch |

### 9.6 本地开发环境

```bash
# 无需本地 PostgreSQL / MinIO
cp deploy/.env.example deploy/.env
# 填 Supabase 密钥后：
cd pipeline && python 04_import_supabase.py --season 1
cd apps/api && uvicorn main:app --reload
cd apps/web && npm run dev
# 可选：docker run -d -p 6379:6379 redis:7-alpine
```

---

## 10. 风险、合规与备选路径

| 风险 | 缓解 |
|------|------|
| 版权问题 | 不公开源视频；分享页仅短 clip；README 免责声明 |
| 无源视频 | 仅文本模式；clip 按钮灰显 `NO_SOURCE` |
| OpenSubtitles 下架 | 多源备份；保留已解析 DB |
| Supabase 免费额度用尽 | 删旧 clip / 升级 Pro / Storage 迁 R2 |
| 预签名过期 | 分享页 API 调用 `createSignedUrl` 刷新 |
| service_role 泄露 | 立即在 Supabase 控制台轮换密钥 |

**备选 MVP（零视频）**：仅用 Supabase DB + 搜索 + 文本分享，不启 Worker → **约 1 周**；后续再加切片。

---

## 11. 附录

### 11.1 文档与 Cursor 协作索引

| 文档 | 内容 |
|------|------|
| `docs/PRODUCT_IMPLEMENTATION_MANUAL.md` | 本手册 |
| `docs/SUPABASE_SETUP.md` | Supabase 创建、密钥、Storage |
| `supabase/migrations/001_initial_schema.sql` | 建表 SQL |
| `deploy/.env.example` | 环境变量模板 |
| `docs/API.md` | 接口明细（从第 5 章拆出） |
| `docs/DATA_SCHEMA.md` | 表字段、jsonl 格式 |
| `docs/designs/*.png` | UI 设计稿 |

### 11.2 推荐热词（用于测试与首页 chips）

`bazinga`, `roommate agreement`, `soft kitty`, `penny`, `doppler effect`, `谢尔顿`, `莱纳德`, `如何搭讪`

### 11.3 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-04 | 初版：架构、语料、存储、前端、部署 |
| v1.1 | 2026-06-04 | 数据库与切片存储改为 **Supabase**；新增 SUPABASE_SETUP、迁移 SQL |

---

**下一步（你提供设计稿后）**：将 `docs/designs/` 下截图与第 6.5 节对齐，我可再出一版「组件级 UI 规格补丁」写入本手册第 6 章。
