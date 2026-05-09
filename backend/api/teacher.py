"""Endpoint Mode Guru — dashboard kelas dengan AI insight.

Untuk guru SD/SMP yang mengajar coding ke 30+ siswa secara bersamaan:
- Lihat progress seluruh kelas dalam satu pandangan
- AI auto-detect siswa yang stuck di topik tertentu
- AI kasih saran fokus pelajaran berikutnya
- Identifikasi pola error yang sering muncul
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import SesiDatabase
from models.database import CodeSubmission, Progress, Student
from services.llm_service import LayananLLMError, gemma_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get(
    "/dashboard",
    summary="Dashboard kelas — agregasi statistik seluruh siswa",
)
async def dashboard_kelas(sesi: SesiDatabase) -> dict[str, Any]:
    """Kembalikan ringkasan kelas:
    - Total siswa, total submission hari ini
    - Distribusi level (beginner/intermediate/advanced)
    - Top 5 latihan yang paling banyak dicoba
    - Top 5 error yang paling sering terjadi
    - Siswa yang stuck (banyak attempt tapi belum lulus)
    """
    # Total siswa
    total_siswa = await sesi.scalar(select(func.count(Student.id))) or 0

    # Distribusi level
    rows_level = await sesi.execute(
        select(Student.level, func.count(Student.id)).group_by(Student.level)
    )
    distribusi_level = {row[0]: row[1] for row in rows_level.all()}

    # Total submission
    total_submission = await sesi.scalar(select(func.count(CodeSubmission.id))) or 0

    # Submission yang berhasil (skor >= 70)
    sukses_submission = await sesi.scalar(
        select(func.count(CodeSubmission.id)).where(CodeSubmission.score >= 70)
    ) or 0

    # Top 5 latihan yang paling banyak dicoba
    top_latihan = (
        await sesi.execute(
            select(Progress.exercise_id, func.sum(Progress.attempts).label("total"))
            .group_by(Progress.exercise_id)
            .order_by(desc("total"))
            .limit(5)
        )
    ).all()
    latihan_populer = [
        {"exercise_id": r[0], "total_attempts": int(r[1] or 0)} for r in top_latihan
    ]

    # Siswa yang stuck — > 5 attempts tapi belum complete
    stuck_rows = (
        await sesi.execute(
            select(Progress, Student)
            .join(Student, Student.id == Progress.student_id)
            .where(Progress.attempts >= 5, Progress.completed.is_(False))
            .order_by(desc(Progress.attempts))
            .limit(10)
        )
    ).all()
    siswa_stuck = [
        {
            "student_id": p.student_id,
            "nama": s.name,
            "exercise_id": p.exercise_id,
            "attempts": p.attempts,
            "avg_score": p.avg_score,
        }
        for p, s in stuck_rows
    ]

    # Top 5 error type — dari kolom errors di submissions
    error_rows = (
        await sesi.execute(
            select(CodeSubmission.errors).where(CodeSubmission.errors.isnot(None))
        )
    ).all()
    error_counter: Counter[str] = Counter()
    for (errs,) in error_rows:
        if isinstance(errs, list):
            for e in errs:
                if isinstance(e, dict):
                    err_type = e.get("type") or e.get("category") or "Unknown"
                    error_counter[err_type] += 1
    top_errors = [{"type": k, "count": v} for k, v in error_counter.most_common(5)]

    success_rate = (
        round(sukses_submission / total_submission * 100, 1) if total_submission > 0 else 0.0
    )

    return {
        "ringkasan": {
            "total_siswa": total_siswa,
            "total_submission": total_submission,
            "submission_sukses": sukses_submission,
            "success_rate_persen": success_rate,
        },
        "distribusi_level": distribusi_level,
        "latihan_populer": latihan_populer,
        "siswa_stuck": siswa_stuck,
        "top_errors": top_errors,
    }


@router.get(
    "/insights",
    summary="AI Insight — Gemma 4 menganalisis pola kelas + saran pengajaran",
)
async def insight_kelas(sesi: SesiDatabase) -> dict[str, Any]:
    """Gemma 4 menganalisis data kelas dan memberi rekomendasi untuk guru.

    Output:
    - Kondisi kelas saat ini
    - Topik yang paling perlu perhatian
    - 3 saran konkret untuk pelajaran berikutnya
    """
    # Kumpulkan data dasar
    data = await dashboard_kelas(sesi)

    prompt = (
        "Kamu adalah konsultan kurikulum coding untuk guru SD di Indonesia. "
        "Berikut data kelas dari sistem CodeBuddy:\n\n"
        f"- Total siswa: {data['ringkasan']['total_siswa']}\n"
        f"- Total submission: {data['ringkasan']['total_submission']}\n"
        f"- Success rate: {data['ringkasan']['success_rate_persen']}%\n"
        f"- Distribusi level: {data['distribusi_level']}\n"
        f"- Latihan populer: {data['latihan_populer']}\n"
        f"- Siswa yang stuck: {len(data['siswa_stuck'])} siswa\n"
        f"- Error paling sering: {data['top_errors']}\n\n"
        "Berikan analisis dan saran untuk guru. Kembalikan HANYA JSON:\n"
        "{\n"
        '  "kondisi_kelas": "ringkasan kondisi dalam 2 kalimat",\n'
        '  "topik_perhatian": "topik/konsep yang paling perlu di-review",\n'
        '  "saran_pengajaran": ['
        '"saran 1 konkret untuk besok", '
        '"saran 2", '
        '"saran 3"'
        "],\n"
        '  "siswa_butuh_bantuan": "siapa yang perlu perhatian khusus dan kenapa"\n'
        "}\n\n"
        "Gunakan Bahasa Indonesia yang ramah dan praktis untuk guru."
    )

    schema = {
        "type": "object",
        "properties": {
            "kondisi_kelas": {"type": "string"},
            "topik_perhatian": {"type": "string"},
            "saran_pengajaran": {"type": "array", "items": {"type": "string"}},
            "siswa_butuh_bantuan": {"type": "string"},
        },
        "required": ["kondisi_kelas", "topik_perhatian", "saran_pengajaran", "siswa_butuh_bantuan"],
    }

    try:
        ai_insight = await gemma_service._call_ollama_structured(prompt, schema)
    except LayananLLMError as exc:
        logger.warning("LLM gagal generate insight: %s", exc)
        ai_insight = {
            "kondisi_kelas": "AI insight tidak tersedia saat ini.",
            "topik_perhatian": "—",
            "saran_pengajaran": ["Pastikan Ollama berjalan untuk fitur ini."],
            "siswa_butuh_bantuan": "—",
        }

    return {"data_kelas": data, "ai_insight": ai_insight}


@router.get(
    "/student/{student_id}/timeline",
    summary="Timeline aktivitas seorang siswa untuk guru",
)
async def timeline_siswa(student_id: int, sesi: SesiDatabase) -> dict[str, Any]:
    """Detail aktivitas seorang siswa untuk guru:
    - 20 submission terakhir
    - Pola error yang sering dia buat
    - Rekomendasi: apakah dia siap naik level?
    """
    siswa = await sesi.scalar(select(Student).where(Student.id == student_id))
    if siswa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Siswa id={student_id} tidak ditemukan.",
        )

    # 20 submission terakhir
    subs = (
        await sesi.scalars(
            select(CodeSubmission)
            .where(CodeSubmission.student_id == student_id)
            .order_by(desc(CodeSubmission.timestamp))
            .limit(20)
        )
    ).all()

    submissions_data = [
        {
            "id": s.id,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "score": s.score,
            "errors_count": len(s.errors) if isinstance(s.errors, list) else 0,
        }
        for s in subs
    ]

    # Error patterns
    error_counter: Counter[str] = Counter()
    for s in subs:
        if isinstance(s.errors, list):
            for e in s.errors:
                if isinstance(e, dict):
                    error_counter[e.get("type", "Unknown")] += 1

    pola_error = [{"type": k, "count": v} for k, v in error_counter.most_common(5)]

    # Saran: berdasarkan rata-rata 5 submission terakhir
    last_5_scores = [s.score for s in subs[:5] if s.score is not None]
    rata_recent = sum(last_5_scores) / len(last_5_scores) if last_5_scores else 0
    if rata_recent >= 85:
        rekomendasi = "Siap naik ke level berikutnya."
    elif rata_recent >= 60:
        rekomendasi = "Cukup baik. Latih konsistensi sebelum naik level."
    else:
        rekomendasi = "Butuh bimbingan tambahan, ulangi dasar dulu."

    return {
        "siswa": {
            "id": siswa.id,
            "nama": siswa.name,
            "level": siswa.level,
        },
        "submissions": submissions_data,
        "pola_error": pola_error,
        "rata_skor_5_terakhir": round(rata_recent, 1),
        "rekomendasi_guru": rekomendasi,
    }
