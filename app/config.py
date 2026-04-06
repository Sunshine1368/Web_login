"""
app/config.py - 应用配置，通过环境变量或 .env 文件加载
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用基础配置
    app_name: str = "MiniGoogle"
    app_env: str = "development"
    debug: bool = True

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./mini_google.db"

    # JWT 配置
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 天

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"

    # ── 邮件 SMTP 配置 ──────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""          # 发件邮箱
    smtp_password: str = ""      # 邮箱密码 / App Password
    smtp_from_name: str = "TOOLKIT"
    smtp_tls: bool = True

    # ── Google OAuth ───────────────────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # ── 微信 OAuth ─────────────────────────────────────────────────────────────
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_redirect_uri: str = "http://localhost:8000/api/auth/wechat/callback"

    # ── 前端地址（OAuth 成功后跳转）────────────────────────────────────────────
    frontend_success_url: str = "https://toolkit.uno"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
