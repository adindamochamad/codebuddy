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
    """Tambahkan siswa contoh + submissions + progress untuk demo hackathon."""
    from datetime import timedelta  # noqa: PLC0415
    from models.database import CodeSubmission, Progress, Student  # noqa: PLC0415

    daftar_siswa = [
        {"name": "Andi Pratama",    "age": 10, "level": "beginner"},
        {"name": "Siti Nurhaliza",  "age": 11, "level": "intermediate"},
        {"name": "Pak Wayan Darma", "age": 35, "level": "advanced"},
        {"name": "Budi Santoso",    "age": 9,  "level": "beginner"},
        {"name": "Dewi Lestari",    "age": 12, "level": "beginner"},
    ]

    async with pembuat_sesi_async() as sesi:
        # Buat siswa
        siswa_ids = []
        for data in daftar_siswa:
            siswa = Student(**data)
            sesi.add(siswa)
        await sesi.commit()

        from sqlalchemy import select  # noqa: PLC0415
        semua_siswa = (await sesi.scalars(select(Student))).all()
        siswa_ids = [s.id for s in semua_siswa]
        logger.info("Seed: %d siswa dibuat.", len(siswa_ids))

        # Submissions contoh — simulasi riwayat belajar
        from datetime import datetime, timezone  # noqa: PLC0415
        sekarang = datetime.now(timezone.utc)

        contoh_submissions = [
            # Andi (beginner) — beberapa error, belajar bertahap
            {"student_id": siswa_ids[0], "code": 'print("Halo Dunia!")', "errors": None, "score": 100.0,
             "timestamp": sekarang - timedelta(days=5)},
            {"student_id": siswa_ids[0], "code": 'nama = "Andi"\nprint("Halo " + nama + umur)', "score": 30.0,
             "errors": [{"type": "TypeError", "message": "can only concatenate str", "line": 2}],
             "timestamp": sekarang - timedelta(days=4)},
            {"student_id": siswa_ids[0], "code": 'nama = "Andi"\numur = 10\nprint("Halo " + nama)', "score": 80.0,
             "errors": None, "timestamp": sekarang - timedelta(days=3)},
            {"student_id": siswa_ids[0], "code": 'for i in range(5)\n    print("*")', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=2)},
            {"student_id": siswa_ids[0], "code": 'for i in range(5):\n    print("*")', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=1)},
            # Siti (intermediate) — lebih konsisten
            {"student_id": siswa_ids[1], "code": 'def luas(p, l):\n    return p * l\nprint(luas(5,3))', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=6)},
            {"student_id": siswa_ids[1], "code": 'angka = [3,15,7,22]\nhasil = [n for n in angka if n > 10]\nprint(hasil)', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=4)},
            {"student_id": siswa_ids[1], "code": 'def jumlah(n):\n    return sum(range(1, n+1))\nprint(jumlah(10))', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=2)},
            # Pak Wayan (advanced, guru yang tes)
            {"student_id": siswa_ids[2], "code": 'def faktorial(n):\n    if n == 0: return 1\n    return n * faktorial(n-1)\nprint(faktorial(5))', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=3)},
            # Budi (beginner) — stuck di loop
            {"student_id": siswa_ids[3], "code": 'for i in range(5)\n    print(i)', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=5)},
            {"student_id": siswa_ids[3], "code": 'for i in range(5)\n    print(i)', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=4)},
            {"student_id": siswa_ids[3], "code": 'for i in range(5)\n    print(i)', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=3)},
            {"student_id": siswa_ids[3], "code": 'for i in range(5)\n    print(i)', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=2)},
            {"student_id": siswa_ids[3], "code": 'for i in range(5)\n    print(i)', "score": 20.0,
             "errors": [{"type": "SyntaxError", "message": "expected ':'", "line": 1}],
             "timestamp": sekarang - timedelta(days=1)},
            # Dewi (beginner) — campuran sukses dan error
            {"student_id": siswa_ids[4], "code": 'print("Halo!")', "score": 100.0,
             "errors": None, "timestamp": sekarang - timedelta(days=4)},
            {"student_id": siswa_ids[4], "code": 'x = 5\nprint(x / 0)', "score": 40.0,
             "errors": [{"type": "ZeroDivisionError", "message": "division by zero", "line": 2}],
             "timestamp": sekarang - timedelta(days=3)},
            {"student_id": siswa_ids[4], "code": 'nama = input("Siapa namamu? ")\nprint(nama)', "score": 70.0,
             "errors": None, "timestamp": sekarang - timedelta(days=1)},
        ]

        for sub_data in contoh_submissions:
            sub = CodeSubmission(
                student_id=sub_data["student_id"],
                code=sub_data["code"],
                errors=sub_data.get("errors"),
                score=sub_data["score"],
                timestamp=sub_data["timestamp"],
            )
            sesi.add(sub)
        await sesi.commit()
        logger.info("Seed: %d submissions contoh dibuat.", len(contoh_submissions))

        # Progress per exercise
        contoh_progress = [
            # Andi — hello_print selesai, loop_bintang selesai, variabel_nama sedang
            {"student_id": siswa_ids[0], "exercise_id": "hello_print", "completed": True, "attempts": 1, "avg_score": 100.0},
            {"student_id": siswa_ids[0], "exercise_id": "variabel_nama", "completed": True, "attempts": 3, "avg_score": 70.0},
            {"student_id": siswa_ids[0], "exercise_id": "loop_bintang", "completed": True, "attempts": 2, "avg_score": 60.0},
            # Siti — banyak yang selesai
            {"student_id": siswa_ids[1], "exercise_id": "hello_print", "completed": True, "attempts": 1, "avg_score": 100.0},
            {"student_id": siswa_ids[1], "exercise_id": "variabel_nama", "completed": True, "attempts": 1, "avg_score": 95.0},
            {"student_id": siswa_ids[1], "exercise_id": "loop_bintang", "completed": True, "attempts": 1, "avg_score": 100.0},
            {"student_id": siswa_ids[1], "exercise_id": "fungsi_luas_persegi", "completed": True, "attempts": 2, "avg_score": 85.0},
            {"student_id": siswa_ids[1], "exercise_id": "list_filter", "completed": True, "attempts": 1, "avg_score": 100.0},
            # Pak Wayan — semua selesai
            {"student_id": siswa_ids[2], "exercise_id": "rekursi_faktorial", "completed": True, "attempts": 1, "avg_score": 100.0},
            # Budi — stuck di loop_bintang (banyak attempt, belum selesai)
            {"student_id": siswa_ids[3], "exercise_id": "hello_print", "completed": True, "attempts": 2, "avg_score": 60.0},
            {"student_id": siswa_ids[3], "exercise_id": "loop_bintang", "completed": False, "attempts": 7, "avg_score": 25.0},
            # Dewi — baru mulai
            {"student_id": siswa_ids[4], "exercise_id": "hello_print", "completed": True, "attempts": 1, "avg_score": 100.0},
            {"student_id": siswa_ids[4], "exercise_id": "variabel_nama", "completed": False, "attempts": 3, "avg_score": 55.0},
        ]

        for prog_data in contoh_progress:
            prog = Progress(
                student_id=prog_data["student_id"],
                exercise_id=prog_data["exercise_id"],
                completed=prog_data["completed"],
                attempts=prog_data["attempts"],
                avg_score=prog_data["avg_score"],
                last_attempt=sekarang - timedelta(days=1),
            )
            sesi.add(prog)
        await sesi.commit()
        logger.info("Seed: %d progress records dibuat.", len(contoh_progress))
