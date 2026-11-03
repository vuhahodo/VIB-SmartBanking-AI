from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent  # web/backend


def default_ai_dir() -> Path:
    # Ưu tiên biến môi trường AI_DIR
    env_dir = os.getenv("AI_DIR")
    if env_dir:
        return Path(env_dir)
    # Đường dẫn trong Docker container
    docker_ai = Path("/app/ai")
    if docker_ai.exists():
        return docker_ai
    # Đường dẫn chạy local từ repo root
    local_ai = BACKEND_DIR.parent.parent / "ai"
    if local_ai.exists():
        return local_ai
    return BACKEND_DIR / "ai"


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường (hoặc file web/backend/.env)."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://vib_admin:SecureVIBPassword2026!@postgres-svc.vib-banking.svc.cluster.local:5432/vib_db"
    # HS256 cần khóa >= 32 byte. Production: sinh bằng `python -c "import secrets; print(secrets.token_hex(32))"`
    JWT_SECRET: str = "vib-super-secure-jwt-secret-key-production-2026-very-long"
    JWT_EXPIRE_MINUTES: int = 120
    # Thư mục chứa predict.py + models/. Local: <repo>/ai, trong Docker: /app/ai
    AI_DIR: Path = default_ai_dir()
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost",
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
    ]
    # Bật endpoint liệt kê tài khoản demo cho màn hình đăng nhập
    DEMO_MODE: bool = True


settings = Settings()
