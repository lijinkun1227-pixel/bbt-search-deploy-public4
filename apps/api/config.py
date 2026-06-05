from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / "deploy" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    supabase_url: str
    supabase_service_role_key: str
    database_url: str
    supabase_storage_bucket: str = "clips"
    source_video_root: str = str(ROOT / "data" / "source_videos")
    public_web_url: str = "http://localhost:3000"
    # 额外允许的前端域名，逗号分隔，如 https://xxx.netlify.app,https://www.example.com
    cors_origins: str = ""
    api_port: int = 8000

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins: list[str] = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        for raw in (self.public_web_url, self.cors_origins):
            for part in raw.split(","):
                o = part.strip().rstrip("/")
                if o and o not in origins:
                    origins.append(o)
        return origins


settings = Settings()
