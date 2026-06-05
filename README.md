# 生活大爆炸 · 台词素材检索

## 快速开始

### 1. 环境

```bash
pip install -r requirements.txt
cd apps/web && npm install
```

复制 `apps/web/.env.local.example` → `apps/web/.env.local`

### 2. 字幕与视频

- 字幕：`data/raw/subtitles/en|S01E01.srt`，`zh/S01E01.srt`
- 视频：**MKV/MP4 均可**，放到 `data/source_videos/S01E01.mkv`

`deploy/.env` 中：

```bash
SOURCE_VIDEO_ROOT=E:/pm learning/AI PM/vibe coding/4.product_engineering/data/source_videos
```

### 3. 导入语料（Phase 1）

```bash
python pipeline/02_parse_srt.py --season 1
python pipeline/03_align_bilingual.py --season 1
python pipeline/04_import_supabase.py --season 1
python pipeline/05_refresh_search_index.py
python pipeline/06_register_episodes.py
python pipeline/search_cli.py bazinga
```

### 4. 启动服务

```bash
# API
uvicorn apps.api.main:app --reload --port 8000

# Web
cd apps/web && npm run dev
```

浏览器打开 http://localhost:3000

### 5. 切片（Phase 4）

需安装 [FFmpeg](https://ffmpeg.org/)，Supabase Storage 创建 **clips** 桶（可 Public）。

在素材篮点击「生成视频片段」。

## 线上部署（Netlify + Render）

见 **`docs/DEPLOY_NETLIFY_RENDER.md`**（前端 Netlify、API Render，约 30 分钟可完成）。

## 文档

- `docs/DEPLOY_NETLIFY_RENDER.md` — 公网部署步骤
- `docs/PRODUCT_IMPLEMENTATION_MANUAL.md`
- `docs/SUPABASE_SETUP.md`
