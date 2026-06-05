# API 摘要

Base URL: `http://localhost:8000`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/search?q=&lang=both&page=1` | 搜索台词 |
| POST | `/api/clips` | `{ line_ids, padding_ms }` 生成切片 |
| GET | `/api/clips/{id}` | 查询切片状态与 play_url |
| POST | `/api/share` | `{ line_ids, clip_ids? }` |
| GET | `/api/share/{id}` | 分享包详情 |
