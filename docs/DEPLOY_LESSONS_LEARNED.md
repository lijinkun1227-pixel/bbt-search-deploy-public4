# 上线踩坑总结 · Netlify + Render 部署实录

> 记录本项目从「本机能用」到「公网可搜索」的完整排障过程。
>
> 部署方案：**Netlify（前端）+ Render（API）+ Supabase（数据库，已有）**

---

## 1. 我们最终做成了什么


| 组件      | 平台       | 地址（示例）                                   | 状态              |
| ------- | -------- | ---------------------------------------- | --------------- |
| 前端      | Netlify  | `https://search-p.netlify.app`           | ✅ 已上线           |
| 后端 API  | Render   | `https://bigbang-quote-api.onrender.com` | ✅ 已上线           |
| 数据库     | Supabase | 云端                                       | ✅ 本机已导入数据       |
| 公网搜索台词  | —        | —                                        | ✅ 可用            |
| 公网生成新切片 | —        | —                                        | ❌ 需本机 API + 源视频 |


---

## 2. 问题时间线总览


| #   | 现象                                                                           | 根因                                            | 解决                            |
| --- | ---------------------------------------------------------------------------- | --------------------------------------------- | ----------------------------- |
| 1   | 把 `deploy/.env` 整份复制到 Netlify，页面/search 不工作                                  | 前端不读那些变量；缺 `NEXT_PUBLIC_API_URL`              | Netlify 只配一行 API 地址           |
| 2   | 以为只部署 Netlify 就行                                                             | 架构是前后端分离，Python API 不能跑在 Netlify              | API 单独部署到 Render              |
| 3   | Netlify Building 失败：`publish directory cannot be the same as base directory` | `netlify.toml` 只写了 `base`，publish 默认与 base 相同 | 加 `publish = ".next"`         |
| 4   | 同上，UI 三项已留空仍失败                                                               | 同上，`publishOrigin: default` 仍会冲突              | 由 `netlify.toml` 显式指定 publish |
| 5   | 更早一次 Building 失败：TypeScript 类型错误                                             | `ClipPlayer.tsx` 类型检查不通过                      | 修复后重新推送 GitHub                |
| 6   | Netlify 部署成功，搜索报「请确认后端 API…」                                                 | 表面像前端配置问题，实为 API 返回 500                       | 查 Render Logs                 |
| 7   | Render Logs：`database "postgres" does not exist`                             | `DATABASE_URL` 区域写错（`aws-0` vs `aws-1`）       | 从本机 `deploy/.env` 原样复制正确连接串   |
| 8   | `PUBLIC_WEB_URL` 末尾有 `/`                                                     | 用户担心格式问题                                      | 代码自动 `rstrip("/")`，有无均可；建议不加  |


---

## 3. 问题详解

### 问题 1：环境变量放错地方

**现象**

- 本机 `localhost:3000` 正常
- Netlify 部署后搜索无结果或报错

**原因**

项目有两套环境变量，用途不同：


| 文件/位置                 | 内容                    | 谁读取        |
| --------------------- | --------------------- | ---------- |
| `deploy/.env`         | Supabase、数据库、视频路径     | Python 后端  |
| `apps/web/.env.local` | `NEXT_PUBLIC_API_URL` | Next.js 前端 |


把 `deploy/.env` 粘贴到 Netlify，前端代码**根本不会读** `DATABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY` 等。

前端唯一需要的公网配置：

```
NEXT_PUBLIC_API_URL=https://bigbang-quote-api.onrender.com
```

**教训**

> 环境变量要按「谁用」分平台填，不能一份 `.env` 走天下。

---

### 问题 2：前后端必须分开部署

**现象**

- 希望「只用一个 Netlify」搞定一切

**原因**


| 技术             | Netlify 能否运行 |
| -------------- | ------------ |
| Next.js 前端     | ✅            |
| Python FastAPI | ❌            |
| FFmpeg 裁视频     | ❌            |
| 访问本机 MKV 文件    | ❌            |


**解决**

采用方案 1：**Netlify（前端）+ Render（API）**，Supabase 继续托管数据。

**教训**

> 「前后端分离」不是故意复杂，而是两种技术栈需要不同的运行环境。

---

### 问题 3 & 4：Netlify 构建失败（publish 目录）

**现象**

```
Error: Your publish directory cannot be the same as the base directory
```

构建日志显示 `npm run build` **已成功**，失败发生在 `@netlify/plugin-nextjs` 插件阶段。

**原因**

`netlify.toml` 配置了：

```toml
base = "apps/web"
```

但未指定 `publish`。Netlify 默认 `publish = base`（都是 `apps/web`），Next.js 插件不允许二者相同。

即使 Netlify 网页后台 Base / Publish 留空，也会出现 `publishOrigin: default` 的同样错误。

**解决**

在 `netlify.toml` 增加（路径**相对** `apps/web`）：

```toml
publish = ".next"
```

**教训**

> Monorepo 子目录部署 Next.js 时，`base` 和 `publish` 不能相同；`publish` 应指向 `.next`。

---

### 问题 5：TypeScript 构建错误（ClipPlayer）

**现象**

```
ClipPlayer.tsx:43 Type error: Argument of type 'string | undefined' ...
```

**原因**

`normalizeClipPlayUrl()` 可能返回 `undefined`，直接传给 `onUrlFixed?.(fixed)` 时 strict 模式报错。Netlify 生产构建比 `npm run dev` 更严格。

**解决**

```ts
if (fixed && fixed !== playUrl) {
  setSrc(fixed);
  onUrlFixed?.(fixed);
}
```

**教训**

> 本地 dev 能跑 ≠ 生产 build 能过；上线前在本机跑一次 `npm run build`。

---

### 问题 6：页面能开，搜索仍失败

**现象**

- Netlify 绿色 Published
- 搜索页显示：「搜索失败，请确认后端 API 已部署且 NEXT_PUBLIC_API_URL 配置正确」

**排查过程**


| 检查项                         | 结果                              |
| --------------------------- | ------------------------------- |
| `GET /health`               | ✅ 200 `{"ok":true}`             |
| `GET /api/search?q=bazinga` | ❌ 500 Internal Server Error     |
| 浏览器能否打到 Render              | ✅ 能（不是 CORS、不是 localhost 默认值问题） |


**原因**

错误提示容易误导为「前端 URL 没配对」，实际是 **API 内部查数据库失败**。`/health` 不访问数据库，所以健康检查正常但搜索失败。

**教训**

> 看到前端报「API 配置错误」，要分两步查：① 请求有没有打到 API；② API 自己有没有 500。

---

### 问题 7：DATABASE_URL 区域写错（关键）

**现象**

Render Logs：

```
psycopg2.OperationalError: connection to server at "aws-0-ap-southeast-1.pooler.supabase.com" ...
FATAL: database "postgres" does not exist
```

**原因**

Render 上的 `DATABASE_URL` 使用了 `**aws-0-ap-southeast-1`**（可能来自文档示例或手填）。

本机 `deploy/.env` 正确值为 `**aws-1-ap-southeast-1**`，且用户名格式为 `postgres.<项目ref>`。

Supabase 不同区域/错误 pooler 主机名会导致看似「数据库不存在」的致命错误。

**解决**

1. 打开本机 `deploy/.env`
2. 将 `DATABASE_URL=` **整行**复制到 Render Environment
3. 或从 Supabase Dashboard → Database → Connection string → Transaction pooler 重新复制
4. 保存后等 Render 自动 redeploy

**验证**

浏览器访问：

```
https://bigbang-quote-api.onrender.com/api/search?q=bazinga&lang=both&page=1
```

应返回 JSON（含 `"total"`、`"items"`），随后 Netlify 搜索恢复正常。

**教训**

> `DATABASE_URL` 必须与本机可用的完全一致；`aws-0` 和 `aws-1` 差一个数字就会全盘失败。

---

### 问题 8：PUBLIC_WEB_URL 末尾斜杠

**现象**

用户问 `https://search-p.netlify.app/` 末尾 `/` 有没有影响。

**原因**

无实质影响。`apps/api/config.py` 中 `allowed_cors_origins` 会对每个域名执行 `.rstrip("/")`。

**建议**

统一不加末尾 `/`，与 `NEXT_PUBLIC_API_URL` 保持一致习惯。

---

## 4. 我们为上线改了哪些代码


| 文件                                   | 改动                                          |
| ------------------------------------ | ------------------------------------------- |
| `apps/api/config.py`                 | 新增 `CORS_ORIGINS`、`allowed_cors_origins` 属性 |
| `apps/api/main.py`                   | CORS 从配置读取，支持 Netlify 域名                    |
| `apps/web/components/ClipPlayer.tsx` | 修复 TypeScript 构建错误                          |
| `netlify.toml`                       | 新建；`base`、`publish`、`NODE_VERSION`          |
| `render.yaml`                        | 新建；Render Blueprint 部署模板                    |
| `docs/DEPLOY_NETLIFY_RENDER.md`      | 部署操作指南                                      |
| `deploy/.env.example`                | 补充 CORS、PUBLIC_WEB_URL 说明                   |
| `apps/web/.env.local.example`        | 补充线上 API 地址示例                               |


---

## 5. 最终正确配置速查

### Netlify（前端）

**环境变量（仅 1 条）**

```
NEXT_PUBLIC_API_URL=https://bigbang-quote-api.onrender.com
```

**Build settings（网页后台全留空，由 netlify.toml 控制）**

### Render（后端 API）


| 变量                          | 说明                                          |
| --------------------------- | ------------------------------------------- |
| `SUPABASE_URL`              | Supabase 项目 URL                             |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role 密钥                             |
| `DATABASE_URL`              | ⚠️ 与本机 `deploy/.env` 完全一致                   |
| `PUBLIC_WEB_URL`            | Netlify 地址，如 `https://search-p.netlify.app` |
| `CORS_ORIGINS`              | 可留空                                         |


### 部署后验证顺序

```
1. https://xxx.onrender.com/health          → {"ok":true}
2. https://xxx.onrender.com/api/search?q=bazinga  → JSON 有结果
3. https://xxx.netlify.app 搜索 bazinga     → 页面有列表
```

---

## 6. 给未来自己的备忘

1. **先分清是构建失败还是运行失败** — Netlify log 里 `npm run build` 成功但插件失败，多半是 `netlify.toml` 问题，不是环境变量。
2. `**NEXT_PUBLIC_`* 改完必须重新 Deploy** — 值在构建时写入，不 rebuild 不生效。
3. `**/health` 正常不代表 API 正常** — 只要涉及搜索/推荐，就要测 `/api/search`。
4. **复制 `DATABASE_URL` 用复制粘贴，不要手打** — 区域编号、用户名格式极易错。
5. **GitHub Desktop 完全够用** — 不必会命令行；改完文件 Commit → Push → 等平台自动部署。
6. **线上切片生成本身就不在本次方案内** — 需要本机 API + FFmpeg + 源视频。

---

## 7. 相关文档

- `[FRONTEND_BACKEND_GUIDE.md](./FRONTEND_BACKEND_GUIDE.md)` — 前后端交互逻辑复习
- `[DEPLOY_NETLIFY_RENDER.md](./DEPLOY_NETLIFY_RENDER.md)` — 逐步部署操作手册
- `[SUPABASE_SETUP.md](./SUPABASE_SETUP.md)` — 数据库与 Storage 配置

