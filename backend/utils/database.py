"""Engine SQLAlchemy async, factory session, dan inisialisasi/seeding DB."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from utils.config import pengaturan

logger = logging.getLogger(__name__)

mesin_async = create_async_engine(
    pengaturan.database_url,
    echo=pengaturan.debug,
    # SQLite: check_same_thread tidak berlaku di mode async aiosqlite
    connect_args={"check_same_thread": False} if "sqlite" in pengaturan.database_url else {},
)

pembuat_sesi_async = async_sessionmaker(
    mesin_async,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def dapatkan_sesi_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI: satu sesi DB per request.

    Commit dilakukan oleh handler. Rollback otomatis saat context manager keluar
    dengan exception.
    """
    async with pembuat_sesi_async() as sesi:
        try:
            yield sesi
        except Exception:
            await sesi.rollback()
            raise


async def init_db() -> None:
    """Buat semua tabel dan jalankan seeding awal jika DB kosong.

    Dipanggil saat aplikasi startup (lifespan di main.py).
    Aman dijalankan berulang kali — CREATE TABLE IF NOT EXISTS.
    """
    # Pastikan folder SQLite ada
    url_parse = make_url(pengaturan.database_url)
    if url_parse.drivername.startswith("sqlite") and url_parse.database:
        folder_db = Path(url_parse.database).parent
        if str(folder_db) not in (".", ""):
            folder_db.mkdir(parents=True, exist_ok=True)

    # Import model agar metadata terdaftar sebelum create_all
    from models.database import Basis  # noqa: PLC0415

    async with mesin_async.begin() as koneksi:
        await koneksi.run_sync(Basis.metadata.create_all)

    logger.info("Database siap: %s", pengaturan.database_url)
    await _seed_jika_kosong()


async def _seed_jika_kosong() -> None:
    """Isi DB dengan data contoh jika belum ada siswa sama sekali."""
    from sqlalchemy import select  # noqa: PLC0415
    from models.database import Student  # noqa: PLC0415

    async with pembuat_sesi_async() as sesi:
        ada_siswa = await sesi.scalar(select(Student).limit(1))
        if ada_siswa is not None:
            return  # sudah ada data, skip seeding

    logger.info("Database kosong — menjalankan seeding awal...")
    await _seed_siswa_contoh()


async def _seed_siswa_contoh() -> None:
    """Tambahkan 3 siswa contoh untuk demo hackathon."""
    from models.crud import create_student  # noqa: PLC0415

    contoh = [
        {"name": "Budi Santoso",   "age": 13, "level": "beginner"},
        {"name": "Siti Rahayu",    "age": 15, "level": "intermediate"},
        {"name": "Ahmad Fauzi",    "age": 12, "level": "beginner"},
    ]

    async with pembuat_sesi_async() as sesi:
        for data in contoh:
            try:
                siswa = await create_student(sesi, **data)
                logger.info("Seed: siswa '%s' (id=%d) dibuat.", siswa.name, siswa.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Seed siswa '%s' gagal (mungkin sudah ada): %s", data["name"], exc)
                await sesi.rollback()
