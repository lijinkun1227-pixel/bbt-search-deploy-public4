# 项目进度

## 已完成

- [x] Phase 0：monorepo 骨架（apps/api, apps/web, pipeline）
- [x] Phase 1：字幕解析、双语对齐、Supabase 导入、MKV 视频登记
- [x] Phase 2：搜索 / 切片 / 分享 API
- [x] Phase 3：Next.js 搜索页 + 素材篮
- [x] Phase 4：FFmpeg 切片 + Supabase Storage 上传

## 你的数据

- 字幕：S01E01、S01E02（en/zh）
- 视频：请将 `S01E01.mkv`、`S01E02.mkv` 放入 `data/source_videos/`

## 前端更新

- 首页居中主视觉：The Big Bang Theory + 随机经典台词
- 首页随机 9 张素材卡片（`GET /api/featured`）
- 搜索/首页点击卡片 → 悬浮层播放，支持左右切换

## 下一步

- Phase 5：分享页打磨
- Phase 6：部署 Vercel + 云 Worker
