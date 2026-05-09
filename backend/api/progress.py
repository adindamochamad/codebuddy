"""Endpoint progres siswa."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from api.deps import SesiDatabase
from api.schemas import ResponsProgresSiswa, RingkasanLatihan
from models.database import Progress, Student

router = APIRouter(prefix="/students", tags=["students"])


@router.get(
    "/{id_siswa}/progress",
    response_model=ResponsProgresSiswa,
    summary="Statistik progres satu siswa",
)
async def progres_siswa(id_siswa: int, sesi: SesiDatabase) -> ResponsProgresSiswa:
    """Menggabungkan baris Progress untuk siswa dan ringkasan agregat."""
    stmt_siswa = select(Student).where(Student.id == id_siswa)
    hasil_siswa = await sesi.execute(stmt_siswa)
    siswa = hasil_siswa.scalar_one_or_none()
    if siswa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Siswa id={id_siswa} tidak ditemukan.",
        )

    stmt_progres = select(Progress).where(Progress.student_id == id_siswa)
    hasil_progres = await sesi.execute(stmt_progres)
    baris_progres = hasil_progres.scalars().all()

    daftar_ringkas = [
        RingkasanLatihan(
            exercise_id=p.exercise_id,
            completed=p.completed,
            attempts=p.attempts,
            avg_score=p.avg_score,
        )
        for p in baris_progres
    ]

    jumlah_selesai = sum(1 for p in baris_progres if p.completed)
    stmt_avg = select(func.avg(Progress.avg_score)).where(
        Progress.student_id == id_siswa,
        Progress.avg_score.isnot(None),
    )
    rata_opsional = await sesi.execute(stmt_avg)
    rata_skor = rata_opsional.scalar_one()
    rata_float = float(rata_skor) if rata_skor is not None else None

    return ResponsProgresSiswa(
        student_id=siswa.id,
        nama=siswa.name,
        level=siswa.level,
        latihan=daftar_ringkas,
        total_selesai=jumlah_selesai,
        rata_rata_skor=rata_float,
    )
