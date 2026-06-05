# 部署指南：Netlify（前端）+ Render（API）

本指南面向技术小白，按顺序操作即可让**搜索台词**在线上可用。

> **说明**：视频切片生成需要 FFmpeg + 源视频文件，Render 免费实例无法存放你的本地 MKV。线上可搜索台词；切片功能仍需本机 API 或带硬盘的 VPS。

---

## 架构一览

```
用户浏览器
    ↓ 打开网页
Netlify（Next.js 前端）
    ↓ 调用 NEXT_PUBLIC_API_URL
Render（FastAPI 后端）
    ↓ 查询数据库
Supabase（PostgreSQL + Storage）
```

---

## 第一步：把代码推到 GitHub

1. 在 GitHub 新建一个仓库（Private 也可以）。
2. 在本项目根目录执行（若尚未关联远程）：

```bash
git init
git add .
git commit -m "prepare netlify + render deploy"
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

确保 **不要** 把 `deploy/.env` 提交上去（已在 `.gitignore` 中）。

---

## 第二步：在 Render 部署 API

### 方式 A：用 Blueprint（推荐）

1. 登录 [render.com](https://render.com)，连接 GitHub。
2. 点击 **New → Blueprint**，选择本仓库。
3. Render 会读取根目录的 `render.yaml` 并创建 `bigbang-quote-api` 服务。
4. 在创建过程中，为以下变量填入你 `deploy/.env` 里的真实值：

| 变量名 | 说明 |
|--------|------|
| `SUPABASE_URL` | Supabase 项目 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role 密钥（**不是** anon key） |
| `DATABASE_URL` | Supabase 数据库连接串 |
| `PUBLIC_WEB_URL` | 先填 `http://localhost:3000`，Netlify 建好后再改成 Netlify 地址 |
| `CORS_ORIGINS` | 可先留空，Netlify 地址确定后填入 |

5. 点击部署，等待状态变为 **Live**。
6. 记下 API 地址，形如：`https://bigbang-quote-api.onrender.com`
7. 浏览器访问 `https://你的-api.onrender.com/health`，应看到 `{"ok":true}`。

### 方式 B：手动创建 Web Service

| 设置项 | 值 |
|--------|-----|
| Root Directory | （留空，用仓库根目录） |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

环境变量同方式 A。

---

## 第三步：在 Netlify 部署前端

1. 登录 [netlify.com](https://netlify.com)，**Add new site → Import an existing project**，连 GitHub 选本仓库。
2. Netlify 会自动读取根目录 `netlify.toml`，**Build settings 建议全部留空**（由 `netlify.toml` 接管）：

| 设置项 | 值 |
|--------|-----|
| Base directory | **留空**（由 `netlify.toml` 指定 `apps/web`） |
| Build command | **留空** |
| Publish directory | **留空**（由 `netlify.toml` 指定 `.next`） |

> `netlify.toml` 里已写 `publish = ".next"`（相对 `apps/web`）。  
> 若网页后台手填了 Publish directory，请**清空**，避免和配置文件冲突。

3. 展开 **Environment variables**，用 **Add a variable** 添加（不要粘贴整份 `deploy/.env`）：

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://bigbang-quote-api.onrender.com` |

> ✅ **Netlify 真的只需要这一条。** 前端代码只读取 `NEXT_PUBLIC_API_URL`（见 `apps/web/lib/api.ts`）。
>
> ⚠️ **不要** 把 `SUPABASE_SERVICE_ROLE_KEY`、`DATABASE_URL` 填到 Netlify。那些只给 Render API 用。
>
> ⚠️ 若用「Import .env file」文本框，**只能**写这一行，格式必须是 `KEY=VALUE`，不要加引号。

4. 点击 **Deploy site**，等待部署成功。
5. 记下 Netlify 地址，形如：`https://random-name-123.netlify.app`

---

## 第四步：把 Netlify 地址写回 Render（修 CORS）

1. 回到 Render → `bigbang-quote-api` → **Environment**。
2. 修改：

```
PUBLIC_WEB_URL=https://random-name-123.netlify.app
```

3. 若你有多个域名（自定义域名、预览站），可额外设置：

```
CORS_ORIGINS=https://random-name-123.netlify.app,https://你的自定义域名.com
```

4. 保存后 Render 会自动重新部署。

---

## 第五步：验证

1. 打开 Netlify 站点首页，应能正常显示。
2. 搜索 `bazinga`，应出现结果列表。
3. 若失败，按下面「排错」检查。

---

## 先分清两种「有问题」

| 类型 | 表现 | 和环境变量有关吗 |
|------|------|------------------|
| **A. 构建失败** | Netlify Deploys 显示红色 Failed，Building 阶段失败 | ❌ 多半无关，是代码或目录配置问题 |
| **B. 构建成功但搜索失败** | 网站能打开，搜词后报错或没结果 | ✅ 和 `NEXT_PUBLIC_API_URL`、Render CORS 有关 |

---

## 排错清单

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| Netlify **Building 失败**，报 `publish directory cannot be the same as the base directory` | `netlify.toml` 缺 `publish = ".next"`，或 UI 里 Publish 与 Base 相同 | 用最新 `netlify.toml` 推送到 GitHub，UI 三项留空，重新 Deploy |
| Netlify **Building 失败**（其他） | `ClipPlayer.tsx` 未修复 | 确认 GitHub 有最新代码 |
| 搜索报「请确认后端 API…」 | `NEXT_PUBLIC_API_URL` 未设或设错 | Netlify 环境变量检查 → **Trigger deploy** 重新构建 |
| 浏览器 Console 报 CORS 错误 | Render 未允许 Netlify 域名 | 检查 Render 的 `PUBLIC_WEB_URL` 是否等于 Netlify 地址 |
| API `/health` 打不开 | Render 服务未启动或冷启动中 | 等 30 秒重试；看 Render Logs |
| 随机片段为空 | 数据库尚无 ready 状态的 clip | 正常，先搜索台词即可 |

**本地调试线上 API**：在 `apps/web/.env.local` 临时写 `NEXT_PUBLIC_API_URL=https://你的-api.onrender.com`，`npm run dev` 测试。

---

## 关于视频切片（进阶）

Render 免费实例：

- 没有你的 `E:/.../source_videos` 视频文件
- 默认未安装 FFmpeg

因此**线上生成切片**需要额外方案（本机跑 API、或 VPS 挂硬盘）。当前方案 1 的目标是：**公网可搜索台词**，这对剪辑者找素材已经很有用。

---

## 环境变量对照表

| 变量 | Render API | Netlify 前端 |
|------|:----------:|:------------:|
| `SUPABASE_URL` | ✅ | ❌ |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | ❌ |
| `DATABASE_URL` | ✅ | ❌ |
| `PUBLIC_WEB_URL` | ✅ | ❌ |
| `CORS_ORIGINS` | ✅ 可选 | ❌ |
| `SOURCE_VIDEO_ROOT` | ✅（线上可忽略） | ❌ |
| `NEXT_PUBLIC_API_URL` | ❌ | ✅ **必填** |
