-- 《生活大爆炸》台词素材检索 — Supabase 初始 schema
-- 在 Supabase Dashboard → SQL Editor 中执行，或使用 Supabase CLI: supabase db push

-- 扩展（全文检索）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 剧集元数据
CREATE TABLE episodes (
  id                 BIGSERIAL PRIMARY KEY,
  season             SMALLINT NOT NULL,
  episode            SMALLINT NOT NULL,
  title              TEXT,
  source_video_path  TEXT,  -- Worker 所在机器上的本地路径，不进 Storage
  duration_ms        BIGINT,
  has_source_video   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (season, episode)
);

-- 台词行（搜索主体）
CREATE TABLE subtitle_lines (
  id                 BIGSERIAL PRIMARY KEY,
  episode_id         BIGINT NOT NULL REFERENCES episodes (id) ON DELETE CASCADE,
  start_ms           BIGINT NOT NULL,
  end_ms             BIGINT NOT NULL,
  text_en            TEXT NOT NULL,
  text_zh            TEXT,
  align_confidence   REAL,
  line_hash          CHAR(40) NOT NULL UNIQUE,
  search_vector      tsvector,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT subtitle_lines_time_ok CHECK (end_ms > start_ms)
);

CREATE INDEX idx_subtitle_lines_episode ON subtitle_lines (episode_id);
CREATE INDEX idx_subtitle_lines_search ON subtitle_lines USING GIN (search_vector);
CREATE INDEX idx_subtitle_lines_text_en_trgm ON subtitle_lines USING GIN (text_en gin_trgm_ops);
CREATE INDEX idx_subtitle_lines_text_zh_trgm ON subtitle_lines USING GIN (text_zh gin_trgm_ops);

-- 维护 search_vector（英+中）
CREATE OR REPLACE FUNCTION subtitle_lines_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.text_en, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(NEW.text_zh, '')), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subtitle_lines_search_vector
  BEFORE INSERT OR UPDATE OF text_en, text_zh ON subtitle_lines
  FOR EACH ROW EXECUTE FUNCTION subtitle_lines_search_vector_update();

-- 切片素材（元数据在 DB，文件在 Supabase Storage）
CREATE TABLE clip_assets (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subtitle_line_id   BIGINT NOT NULL REFERENCES subtitle_lines (id) ON DELETE CASCADE,
  padding_ms         INT NOT NULL DEFAULT 500,
  storage_path       TEXT,  -- Storage 内路径，如 clips/{id}.mp4
  duration_ms        INT,
  file_size          BIGINT,
  status             TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
  error_message      TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (subtitle_line_id, padding_ms)
);

CREATE INDEX idx_clip_assets_status ON clip_assets (status);

-- 分享包
CREATE TABLE share_bundles (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  line_ids           JSONB NOT NULL,
  clip_ids           JSONB,
  expires_at         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 字幕来源溯源（可选）
CREATE TABLE subtitle_sources (
  id                 BIGSERIAL PRIMARY KEY,
  season             SMALLINT NOT NULL,
  episode            SMALLINT NOT NULL,
  language           TEXT NOT NULL,
  provider           TEXT,
  external_file_id   TEXT,
  fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS：默认禁止匿名直连表；业务只通过后端 service_role 访问
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE subtitle_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE clip_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE subtitle_sources ENABLE ROW LEVEL SECURITY;

-- 分享页只读：允许匿名按 id 读取未过期的 share_bundles（若前端直连 Supabase 时使用）
CREATE POLICY share_bundles_public_read ON share_bundles
  FOR SELECT
  USING (expires_at IS NULL OR expires_at > now());

-- Storage bucket `clips` 需在 Dashboard 创建，并配置策略（见 docs/SUPABASE_SETUP.md）
