from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent  # web/backend


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường (hoặc file web/backend/.env)."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://vib:vib@localhost:5432/vib_smartbanking"
    # HS256 cần khóa >= 32 byte. Production: sinh bằng `python -c "import secrets; print(secrets.token_hex(32))"`
    JWT_SECRET: str = "dev-only-secret-change-me-in-production-0123456789"
    JWT_EXPIRE_MINUTES: int = 120
    # Thư mục chứa predict.py + models/. Local: <repo>/ai, trong Docker: /app/ai
    AI_DIR: Path = BACKEND_DIR.parent.parent / "ai"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    # Bật endpoint liệt kê tài khoản demo cho màn hình đăng nhập
    DEMO_MODE: bool = True


settings = Settings()
