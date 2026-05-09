"""Operasi CRUD async untuk semua model CodeBuddy.

Semua fungsi menerima AsyncSession dari SQLAlchemy 2.x dan mengembalikan
model ORM atau None. Commit harus dilakukan oleh pemanggil (atau lihat
fungsi yang sudah otomatis commit di bawah).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import CodeSubmission, Progress, Student

logger = logging.getLogger(__name__)


# =========================================================================== #
# Student                                                                      #
# =========================================================================== #

async def create_student(
    db: AsyncSession,
    name: str,
    age: Optional[int] = None,
    level: str = "beginner",
) -> Student:
    """Buat dan simpan siswa baru ke database.

    Args:
        db: Sesi SQLAlchemy async.
        name: Nama lengkap siswa.
        age: Usia siswa (opsional).
        level: Level awal — 'beginner' | 'intermediate' | 'advanced'.

    Returns:
        Objek Student yang sudah tersimpan (dengan id terisi).

    Contoh::

        siswa = await create_student(db, name="Budi", age=12)
        print(siswa.id)  # 1
    """
    siswa = Student(name=name, age=age, level=level)
    db.add(siswa)
    await db.commit()
    await db.refresh(siswa)
    logger.info("Siswa baru dibuat: id=%d name=%r level=%s", siswa.id, siswa.name, siswa.level)
    return siswa


async def get_student(
    db: AsyncSession,
    student_id: int,
) -> Optional[Student]:
    """Ambil satu siswa berdasarkan ID.

    Args:
        db: Sesi SQLAlchemy async.
        student_id: Primary key siswa.

    Returns:
        Objek Student atau None jika tidak ditemukan.
    """
    return await db.scalar(select(Student).where(Student.id == student_id))


async def list_students(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[Student]:
    """Daftar semua siswa dengan pagination.

    Args:
        db: Sesi SQLAlchemy async.
        limit: Jumlah maksimum baris.
        offset: Baris yang dilewati (untuk pagination).

    Returns:
        List Student.
    """
    hasil = await db.scalars(
        select(Student).order_by(Student.created_at.desc()).limit(limit).offset(offset)
    )
    return list(hasil.all())


async def update_student_level(
    db: AsyncSession,
    student_id: int,
    level: str,
) -> Optional[Student]:
    """Perbarui level siswa.

    Returns:
        Siswa yang sudah diperbarui, atau None jika tidak ditemukan.
    """
    siswa = await get_student(db, student_id)
    if siswa is None:
        return None
    siswa.level = level
    await db.commit()
    await db.refresh(siswa)
    return siswa


# =========================================================================== #
# CodeSubmission                                                               #
# =========================================================================== #

async def create_submission(
    db: AsyncSession,
    student_id: int,
    code: str,
    result: dict[str, Any],
    photo_path: Optional[str] = None,
) -> CodeSubmission:
    """Simpan satu pengiriman kode ke database.

    Args:
        db: Sesi SQLAlchemy async.
        student_id: ID siswa yang mengirimkan kode.
        code: Kode Python yang dikirimkan.
        result: Dict hasil dari agent_service.tutor_session() atau
                code_executor.execute(). Kunci yang digunakan:
                - ``errors``: list error (dari attempts agen)
                - ``fixed_code`` / ``corrected_code``: kode yang diperbaiki
                - ``score``: float skor akhir (0–100)
                - ``final_result``: string hasil ('success', 'runtime_error', dst.)
        photo_path: Path foto opsional (hasil OCR).

    Returns:
        Objek CodeSubmission yang sudah tersimpan.

    Contoh::

        sub = await create_submission(
            db, student_id=1, code='print(x)',
            result={'final_result': 'runtime_error', 'score': 30.0, 'errors': [...]}
        )
    """
    # Ekstrak field dari result (fleksibel terhadap format agen maupun executor)
    errors_raw = result.get("errors") or _ekstrak_errors_dari_attempts(result)
    fixed_code = (
        result.get("fixed_code")
        or result.get("corrected_code")
        or _ekstrak_fixed_code_dari_attempts(result)
    )
    score = result.get("score") or _hitung_skor_dari_result(result)

    sub = CodeSubmission(
        student_id=student_id,
        code=code,
        photo_path=photo_path,
        errors=errors_raw if isinstance(errors_raw, list) else None,
        fixed_code=fixed_code,
        score=score,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    logger.info(
        "Submission baru: id=%d student=%d score=%.1f final=%s",
        sub.id, student_id, score or 0, result.get("final_result", "?"),
    )
    return sub


async def get_student_submissions(
    db: AsyncSession,
    student_id: int,
    limit: int = 10,
) -> list[CodeSubmission]:
    """Ambil pengiriman kode terbaru dari satu siswa.

    Args:
        db: Sesi SQLAlchemy async.
        student_id: ID siswa.
        limit: Jumlah maksimum hasil (default 10, maks disarankan 100).

    Returns:
        List CodeSubmission diurutkan dari terbaru.
    """
    hasil = await db.scalars(
        select(CodeSubmission)
        .where(CodeSubmission.student_id == student_id)
        .order_by(CodeSubmission.timestamp.desc())
        .limit(max(1, min(limit, 100)))
    )
    return list(hasil.all())


# =========================================================================== #
# Progress                                                                     #
# =========================================================================== #

async def update_progress(
    db: AsyncSession,
    student_id: int,
    exercise_id: str,
    score: float,
) -> Progress:
    """Perbarui atau buat rekord progres untuk satu latihan (upsert).

    Jika rekord sudah ada: tambah attempts, perbarui avg_score dan
    last_attempt, set completed=True jika score >= 70.

    Jika belum ada: buat rekord baru.

    Args:
        db: Sesi SQLAlchemy async.
        student_id: ID siswa.
        exercise_id: ID latihan dari manifest.
        score: Skor percobaan ini (0–100).

    Returns:
        Objek Progress yang sudah diperbarui/dibuat.
    """
    rekord = await db.scalar(
        select(Progress).where(
            Progress.student_id == student_id,
            Progress.exercise_id == exercise_id,
        )
    )

    sekarang = datetime.now(timezone.utc)

    if rekord is None:
        rekord = Progress(
            student_id=student_id,
            exercise_id=exercise_id,
            attempts=1,
            avg_score=score,
            completed=score >= 70,
            last_attempt=sekarang,
        )
        db.add(rekord)
    else:
        # Hitung rata-rata bergerak: avg_baru = (avg_lama * n + skor_baru) / (n+1)
        n = rekord.attempts
        avg_lama = rekord.avg_score or 0.0
        rekord.avg_score = round((avg_lama * n + score) / (n + 1), 2)
        rekord.attempts = n + 1
        rekord.last_attempt = sekarang
        if score >= 70:
            rekord.completed = True

    await db.commit()
    await db.refresh(rekord)
    logger.info(
        "Progress diperbarui: student=%d exercise=%s attempts=%d avg=%.1f completed=%s",
        student_id, exercise_id, rekord.attempts, rekord.avg_score or 0, rekord.completed,
    )
    return rekord


async def get_progress(
    db: AsyncSession,
    student_id: int,
    exercise_id: str,
) -> Optional[Progress]:
    """Ambil satu rekord progres.

    Returns:
        Progress atau None jika belum pernah mencoba latihan ini.
    """
    return await db.scalar(
        select(Progress).where(
            Progress.student_id == student_id,
            Progress.exercise_id == exercise_id,
        )
    )


# =========================================================================== #
# Statistik                                                                    #
# =========================================================================== #

async def get_student_stats(
    db: AsyncSession,
    student_id: int,
) -> dict[str, Any]:
    """Hitung statistik lengkap seorang siswa.

    Args:
        db: Sesi SQLAlchemy async.
        student_id: ID siswa.

    Returns:
        Dict dengan kunci::

            {
                "student_id": int,
                "total_submissions": int,
                "success_rate": float,   # persen submission dengan score >= 70
                "avg_score": float,
                "exercises_completed": int,
                "exercises_attempted": int,
                "level": str,
            }

        Mengembalikan None jika siswa tidak ditemukan.
    """
    siswa = await get_student(db, student_id)
    if siswa is None:
        return {}

    # Total submission
    total_sub = await db.scalar(
        select(func.count()).where(CodeSubmission.student_id == student_id)
    ) or 0

    # Submission dengan score >= 70
    sukses_sub = await db.scalar(
        select(func.count()).where(
            CodeSubmission.student_id == student_id,
            CodeSubmission.score >= 70,
        )
    ) or 0

    # Rata-rata skor semua submission
    avg_skor_sub = await db.scalar(
        select(func.avg(CodeSubmission.score)).where(
            CodeSubmission.student_id == student_id,
            CodeSubmission.score.isnot(None),
        )
    )

    # Latihan selesai & dicoba
    selesai = await db.scalar(
        select(func.count()).where(
            Progress.student_id == student_id,
            Progress.completed.is_(True),
        )
    ) or 0
    dicoba = await db.scalar(
        select(func.count()).where(Progress.student_id == student_id)
    ) or 0

    success_rate = round((sukses_sub / total_sub * 100), 1) if total_sub > 0 else 0.0

    return {
        "student_id": student_id,
        "name": siswa.name,
        "level": siswa.level,
        "total_submissions": total_sub,
        "success_rate": success_rate,
        "avg_score": round(float(avg_skor_sub), 1) if avg_skor_sub is not None else 0.0,
        "exercises_completed": selesai,
        "exercises_attempted": dicoba,
    }


# =========================================================================== #
# Helpers internal                                                             #
# =========================================================================== #

def _ekstrak_errors_dari_attempts(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Ekstrak daftar error dari format tutor_session attempts."""
    attempts = result.get("attempts", [])
    for attempt in reversed(attempts):
        err = attempt.get("error")
        if err:
            return [err]
        ai = attempt.get("ai_feedback") or {}
        errs = ai.get("errors")
        if errs:
            return errs
    return []


def _ekstrak_fixed_code_dari_attempts(result: dict[str, Any]) -> Optional[str]:
    """Ekstrak corrected_code dari feedback LLM dalam attempts."""
    for attempt in reversed(result.get("attempts", [])):
        ai = attempt.get("ai_feedback") or {}
        kode = ai.get("corrected_code") or ai.get("fixed_code")
        if kode:
            return kode
    return None


def _hitung_skor_dari_result(result: dict[str, Any]) -> float:
    """Hitung skor 0–100 berdasarkan final_result atau success flag."""
    # Format tutor_session
    final = result.get("final_result", "")
    if final == "success":
        return 100.0
    if final == "syntax_error":
        return 20.0
    if final == "runtime_error":
        return 40.0
    if final == "timeout":
        return 10.0

    # Format executor langsung
    if result.get("success") is True:
        return 100.0
    if result.get("success") is False:
        return 30.0

    return 0.0
