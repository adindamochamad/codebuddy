"""Konfigurasi aplikasi dari environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PengaturanAplikasi(BaseSettings):
    """Pengaturan yang bisa dioverride lewat variabel lingkungan."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nama_aplikasi: str = "CodeBuddy"
    debug: bool = False

    # SQLite async — path relatif terhadap cwd saat server jalan
    database_url: str = "sqlite+aiosqlite:///./data/codebuddy.db"

    # Ollama — override dengan OLLAMA_BASE_URL / OLLAMA_MODEL
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    ollama_vision_model: str = "gemma4:e4b"  # sama, Gemma 4 sudah multimodal

    # Batas eksekusi sandbox (karakter)
    kode_maksimal_panjang: int = 8000

    # CORS Origins — daftar domain yang diizinkan akses API
    # Development: localhost + Gradio default port
    # Produksi: tambahkan domain deployment kamu
    allowed_origins: list[str] = [
        "http://localhost:7860",
        "http://127.0.0.1:7860",
        "http://localhost:3000",  # untuk frontend React/Next.js jika ada
        "http://127.0.0.1:3000",
    ]

    # Rate Limiting — requests per menit per IP
    rate_limit_per_minute: int = 60
    rate_limit_ocr: int = 20      # OCR lebih berat, batas lebih ketat
    rate_limit_agent: int = 10    # Agent/LLM paling mahal


pengaturan = PengaturanAplikasi()
