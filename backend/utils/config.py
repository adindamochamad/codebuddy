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


pengaturan = PengaturanAplikasi()
