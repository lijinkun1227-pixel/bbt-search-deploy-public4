# 数据模型说明（Supabase）

> 权威 SQL：`supabase/migrations/001_initial_schema.sql`  
> 配置步骤：`docs/SUPABASE_SETUP.md`

## 表一览

| 表名 | 用途 |
|------|------|
| `episodes` | 季/集元数据；`source_video_path` 为 Worker 本地路径 |
| `subtitle_lines` | 可搜索台词行；`line_hash` 去重 |
| `clip_assets` | 切片任务状态；`storage_path` 对应 Storage 对象 |
| `share_bundles` | 分享包 `line_ids` / `clip_ids` |
| `subtitle_sources` | 字幕下载溯源（可选） |

## Storage

| 桶名 | 对象路径示例 |
|------|----------------|
| `clips` | `clips/{clip_asset_id}.mp4` |

## pipeline 输出 jsonl（单行示例）

```json
{
  "season": 1,
  "episode": 1,
  "start_ms": 125000,
  "end_ms": 128500,
  "text_en": "I'm not crazy. My mother had me tested.",
  "text_zh": "我没疯，我妈带我做过测试。",
  "align_confidence": 0.92,
  "line_hash": "a1b2c3..."
}
```

## 环境变量

见 `deploy/.env.example`。
