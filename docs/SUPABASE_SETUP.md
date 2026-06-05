# Supabase 配置指南（代码小白向）

本项目的**主数据库**与**切片文件存储**均使用 [Supabase](https://supabase.com)（免费档即可起步）。

---

## 1. 创建项目

1. 打开 https://supabase.com 并注册/登录  
2. **New project** → 填写名称（如 `bigbang-quotes`）、数据库密码（务必保存）  
3. 等待约 2 分钟，项目状态变为 **Active**

---

## 2. 获取连接信息

在 **Project Settings → API**：

| 变量名 | 用途 |
|--------|------|
| `Project URL` | `SUPABASE_URL` |
| `anon` `public` key | 前端（若直连 Supabase，MVP 可不用） |
| `service_role` `secret` key | **仅后端 / pipeline / Worker**，切勿提交 git 或暴露到浏览器 |

在 **Project Settings → Database → Connection string**：

| 模式 | 用途 |
|------|------|
| **URI**（Session pooler 或 Direct） | `DATABASE_URL`，给 Python pipeline、`psql` |
| 推荐 pipeline 用 **Transaction** pooler 端口 `6543` | 批量导入更稳 |

复制到本地 `deploy/.env`（从 `.env.example` 复制）：

```bash
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
SUPABASE_STORAGE_BUCKET=clips
```

---

## 3. 建表

**方式 A（推荐新手）**：Dashboard → **SQL Editor** → 粘贴并运行  
`supabase/migrations/001_initial_schema.sql` 的全部内容。

**方式 B**：安装 [Supabase CLI](https://supabase.com/docs/guides/cli)，在项目根目录：

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

执行后在 **Table Editor** 应能看到：`episodes`、`subtitle_lines`、`clip_assets`、`share_bundles`。

---

## 4. 创建 Storage 桶（存切片 mp4）

**自动创建（推荐）**：

```bash
python scripts/init_supabase_storage.py
```

**或手动**：  
1. **Storage** → **New bucket**  
2. Name：`clips`（与 `SUPABASE_STORAGE_BUCKET` 一致）  
3. **Public bucket**：MVP 可设为 Public，分享页用公开 URL 最简单；正式环境建议 Private + 后端签名 URL  

**Private 桶时的策略示例**（SQL Editor）：

```sql
-- 允许 service_role 上传；匿名只读已生成对象（按路径前缀，可按需收紧）
CREATE POLICY "clips authenticated upload"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'clips');

-- MVP 简化：公开读 clips 目录（仅 Demo）
CREATE POLICY "clips public read"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'clips');
```

Worker 上传路径约定：`clips/{clip_asset_id}.mp4`。

---

## 5. 导入语料（pipeline）

在本地配置好 `DATABASE_URL` 后：

```bash
cd pipeline
python 04_import_supabase.py --season 1
python 05_refresh_search_index.py
```

在 **Table Editor → subtitle_lines** 中应能看到数据。

---

## 6. 安全提醒

- `service_role` 可绕过 RLS，**只放在服务器环境变量**  
- 不要把 `.env` 提交到 GitHub  
- 免费档有存储与带宽上限，见 Supabase 定价页  

---

## 7. 与手册其他章节的关系

| 原自建方案 | Supabase 方案 |
|------------|---------------|
| Docker 里的 PostgreSQL | Supabase 托管 PostgreSQL |
| MinIO 存 clips | Supabase Storage 桶 `clips` |
| `pg_dump` 自备份 | Dashboard 备份 / Pro 时间点恢复 |

源视频全集仍放在**本机或 VPS 本地目录**，不上传 Supabase（节省费用）。
