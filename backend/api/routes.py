"""Router terpadu — semua endpoint CodeBuddy.

Prefix /api sudah ditambahkan di main.py saat mounting.

Endpoint yang tersedia:
  OCR       POST /api/ocr/extract
  Code      POST /api/code/execute
            POST /api/code/validate
  Agent     POST /api/agent/tutor
            POST /api/agent/hint
  Students  POST /api/students/
            GET  /api/students/{student_id}/progress
  Exercises GET  /api/exercises/
            POST /api/exercises/generate

Rate Limiting:
  - OCR: 20 req/min per IP
  - Code Execution: 60 req/min per IP
  - Agent/LLM: 10 req/min per IP
  - Default: 60 req/min per IP
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import SesiDatabase
from api.schemas import (
    AttemptItem,
    ItemLatihan,
    PermintaanBicaraDariSuara,
    PermintaanBuatSiswa,
    PermintaanEksekusiKode,
    PermintaanGenerateLatihan,
    PermintaanHint,
    PermintaanTTS,
    PermintaanTutorAgen,
    PermintaanValidasiKode,
    ResponsBicaraDariSuara,
    ResponsDaftarLatihan,
    ResponsEkstrakOCR,
    ResponsEksekusiKode,
    ResponsHint,
    ResponsLatihanDihasilkan,
    ResponsProgresSiswa,
    ResponsSiswa,
    ResponsTTS,
    ResponsTutorAgen,
    ResponsValidasiKode,
    RingkasanLatihan,
)
from models.database import Progress, Student
from services.agent_service import code_buddy_agent
from services.code_executor import safe_executor
from services.llm_service import BAHASA_DAERAH, LayananLLMError, gemma_service
from services.ocr_service import LayananOCRError, ekstrak_teks_dari_gambar
from utils.config import pengaturan
from utils.pembatas_kueri import pembatas_per_ip

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_UPLOAD_BYTES = 5 * 1024 * 1024          # 5 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
_MANIFEST_PATH = Path(__file__).parent.parent / "data" / "exercises" / "manifest.json"


# =========================================================================== #
# OCR                                                                          #
# =========================================================================== #

@router.post(
    "/ocr/extract",
    response_model=ResponsEkstrakOCR,
    tags=["ocr"],
    summary="Ekstrak kode Python dari gambar tulisan tangan",
    responses={
        400: {"description": "Format file tidak valid atau bukan gambar"},
        413: {"description": "Ukuran file melebihi batas 5 MB"},
        503: {"description": "OCR tidak tersedia (PaddleOCR belum terpasang)"},
    },
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_ocr}/minute")
async def ekstrak_kode_dari_gambar(
    request: Request,
    berkas: UploadFile = File(..., description="Gambar JPG/PNG berisi kode (maks 5 MB)"),
) -> ResponsEkstrakOCR:
    """Unggah foto kode tulisan tangan dan dapatkan kode Python hasil OCR.

    Pipeline:
    1. Validasi format dan ukuran file.
    2. Simpan ke file sementara.
    3. Preprocess gambar (grayscale, denoise, Otsu binarization).
    4. Jalankan PaddleOCR dan rekonstruksi indentasi.
    5. Kembalikan kode + confidence score.
    """
    # Validasi content-type
    ct = (berkas.content_type or "").lower()
    if ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format file tidak didukung: {ct!r}. Gunakan JPG atau PNG.",
        )

    # Baca dan validasi ukuran
    isi = await berkas.read()
    if len(isi) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File yang diunggah kosong.",
        )
    if len(isi) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Ukuran file melebihi batas {_MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    # Pakai Gemma 4 Vision sebagai primary, fallback PaddleOCR
    try:
        hasil = await ekstrak_teks_dari_gambar(isi)
    except LayananOCRError as exc:
        logger.error("OCR gagal: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Layanan OCR tidak tersedia: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Error tak terduga saat OCR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses gambar: {exc}",
        ) from exc

    logger.info(
        "OCR berhasil via %s: confidence=%.3f panjang_kode=%d",
        hasil.get("engine", "?"), hasil["confidence"], len(hasil["text"]),
    )
    return ResponsEkstrakOCR(
        success=True,
        code=hasil["text"],
        confidence=hasil["confidence"],
        lines=hasil.get("lines", []),
    )


# =========================================================================== #
# Code Execution                                                               #
# =========================================================================== #

@router.post(
    "/code/execute",
    response_model=ResponsEksekusiKode,
    tags=["code"],
    summary="Jalankan kode Python dalam sandbox RestrictedPython",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_per_minute}/minute")
async def eksekusi_kode(request: Request, payload: PermintaanEksekusiKode) -> ResponsEksekusiKode:
    """Jalankan kode Python dengan aman di sandbox RestrictedPython.

    - Timeout: 5 detik
    - Import, file I/O, dan akses sistem diblokir
    - Output dikembalikan sebagai string
    """
    import asyncio
    hasil = await asyncio.to_thread(safe_executor.execute, payload.kode)
    return ResponsEksekusiKode(
        sukses=hasil["success"],
        stdout=hasil["output"],
        stderr=hasil["error"] or "",
        error_kind=hasil["error_type"],
    )


@router.post(
    "/code/validate",
    response_model=ResponsValidasiKode,
    tags=["code"],
    summary="Cek syntax kode Python tanpa mengeksekusinya",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_per_minute}/minute")
async def validasi_syntax(request: Request, payload: PermintaanValidasiKode) -> ResponsValidasiKode:
    """Validasi syntax kode Python — cepat, tanpa eksekusi.

    Berguna untuk feedback real-time saat siswa mengetik.
    """
    import asyncio
    hasil = await asyncio.to_thread(safe_executor.validate_syntax, payload.kode)
    return ResponsValidasiKode(
        valid=hasil["valid"],
        error=hasil["error"],
        line=hasil["line"],
    )


# =========================================================================== #
# Agent / Tutor                                                                #
# =========================================================================== #

@router.post(
    "/agent/tutor",
    response_model=ResponsTutorAgen,
    tags=["agent"],
    summary="Sesi tutoring lengkap dengan analisis agentic multi-tahap",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_agent}/minute")
async def sesi_tutor_agentic(request: Request, payload: PermintaanTutorAgen) -> ResponsTutorAgen:
    """Orkestrasi tutoring otomatis: syntax → eksekusi → analisis LLM.

    Tahapan yang dijalankan secara otomatis:
    1. Validasi syntax
    2. Eksekusi di sandbox
    3. Analisis error (jika ada) dengan LLM
    4. Feedback kualitas kode (jika berhasil)

    `final_result`: `'success'` | `'syntax_error'` | `'runtime_error'` | `'timeout'`
    """
    try:
        sesi = await code_buddy_agent.tutor_session(
            code=payload.code,
            student_id=payload.student_id,
            exercise_id=payload.exercise_id,
            student_level=payload.student_level,
            bahasa=payload.bahasa,
        )
    except Exception as exc:
        logger.exception("Error pada tutor_session student_id=%d", payload.student_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menjalankan sesi tutoring: {exc}",
        ) from exc

    attempts = [AttemptItem(**a) for a in sesi["attempts"]]
    return ResponsTutorAgen(
        student_id=sesi["student_id"],
        exercise_id=sesi["exercise_id"],
        original_code=sesi["original_code"],
        student_level=sesi["student_level"],
        attempts=attempts,
        final_result=sesi["final_result"],
    )


@router.post(
    "/agent/hint",
    response_model=ResponsHint,
    tags=["agent"],
    summary="Dapatkan hint bertahap tanpa langsung memberi jawaban",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_agent}/minute")
async def petunjuk_bertahap(request: Request, payload: PermintaanHint) -> ResponsHint:
    """Hint progresif untuk membantu siswa berpikir mandiri.

    - **Level 1**: Pertanyaan pengarah saja
    - **Level 2**: Tunjukkan lokasi error, tanpa kode perbaikan
    - **Level 3**: Solusi lengkap dengan penjelasan
    """
    try:
        teks_hint = await code_buddy_agent.get_progressive_hint(
            code=payload.code,
            error=payload.error,
            hint_level=payload.hint_level,
            student_level=payload.student_level,
        )
    except Exception as exc:
        logger.warning("Hint gagal: %s", exc)
        teks_hint = "Coba baca pesan error dengan saksama dan cek baris yang disebutkan."

    return ResponsHint(hint=teks_hint, hint_level=payload.hint_level)


# =========================================================================== #
# Students                                                                     #
# =========================================================================== #

@router.post(
    "/students/",
    response_model=ResponsSiswa,
    status_code=status.HTTP_201_CREATED,
    tags=["students"],
    summary="Daftarkan siswa baru",
)
async def buat_siswa(
    payload: PermintaanBuatSiswa,
    sesi: SesiDatabase,
) -> ResponsSiswa:
    """Buat akun siswa baru dan simpan ke database.

    `level` opsional — bisa diisi `'beginner'`, `'intermediate'`, atau `'advanced'`.
    """
    siswa_baru = Student(
        name=payload.name,
        age=payload.age,
        level=payload.level or "beginner",
    )
    sesi.add(siswa_baru)
    try:
        await sesi.commit()
        await sesi.refresh(siswa_baru)
    except Exception as exc:
        await sesi.rollback()
        logger.error("Gagal membuat siswa: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyimpan data siswa ke database.",
        ) from exc

    logger.info("Siswa baru dibuat: id=%d name=%r", siswa_baru.id, siswa_baru.name)
    return ResponsSiswa.model_validate(siswa_baru)


@router.get(
    "/students/{student_id}/progress",
    response_model=ResponsProgresSiswa,
    tags=["students"],
    summary="Lihat statistik progres seorang siswa",
)
async def progres_siswa(student_id: int, sesi: SesiDatabase) -> ResponsProgresSiswa:
    """Kembalikan ringkasan progres latihan untuk satu siswa.

    Menghitung:
    - Jumlah latihan yang diselesaikan
    - Rata-rata skor tertimbang
    - Daftar progres per latihan
    """
    siswa = await sesi.scalar(select(Student).where(Student.id == student_id))
    if siswa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Siswa dengan id={student_id} tidak ditemukan.",
        )

    baris_progres = (
        await sesi.scalars(select(Progress).where(Progress.student_id == student_id))
    ).all()

    jumlah_selesai = sum(1 for p in baris_progres if p.completed)

    rata_skor_raw = await sesi.scalar(
        select(func.avg(Progress.avg_score)).where(
            Progress.student_id == student_id,
            Progress.avg_score.isnot(None),
        )
    )
    rata_skor = float(rata_skor_raw) if rata_skor_raw is not None else None

    return ResponsProgresSiswa(
        student_id=siswa.id,
        nama=siswa.name,
        level=siswa.level,
        latihan=[
            RingkasanLatihan(
                exercise_id=p.exercise_id,
                completed=p.completed,
                attempts=p.attempts,
                avg_score=p.avg_score,
            )
            for p in baris_progres
        ],
        total_selesai=jumlah_selesai,
        rata_rata_skor=rata_skor,
    )


# =========================================================================== #
# Exercises                                                                    #
# =========================================================================== #

def _muat_manifest() -> list[dict[str, Any]]:
    """Muat daftar latihan dari manifest.json — di-cache saat pertama kali."""
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("latihan", [])
    except FileNotFoundError:
        logger.warning("manifest.json tidak ditemukan di %s", _MANIFEST_PATH)
        return []
    except json.JSONDecodeError as exc:
        logger.error("manifest.json rusak: %s", exc)
        return []


@router.get(
    "/exercises/",
    response_model=ResponsDaftarLatihan,
    tags=["exercises"],
    summary="Daftar latihan yang tersedia",
)
async def daftar_latihan(
    difficulty: Optional[str] = Query(
        None,
        description="Filter berdasarkan kesulitan: 'beginner' | 'intermediate' | 'advanced'",
    ),
) -> ResponsDaftarLatihan:
    """Kembalikan daftar latihan statis dari manifest.

    Filter opsional berdasarkan `difficulty`.
    """
    semua = _muat_manifest()
    if difficulty:
        semua = [l for l in semua if l.get("difficulty") == difficulty]

    items = [
        ItemLatihan(
            exercise_id=l.get("exercise_id", ""),
            judul=l.get("judul", ""),
            ringkas=l.get("ringkas", ""),
            starter_code=l.get("starter_code", ""),
            difficulty=l.get("difficulty", "beginner"),
        )
        for l in semua
    ]
    return ResponsDaftarLatihan(total=len(items), latihan=items)


@router.post(
    "/exercises/generate",
    response_model=ResponsLatihanDihasilkan,
    tags=["exercises"],
    summary="Generate soal latihan baru menggunakan LLM",
    responses={
        502: {"description": "LLM (Ollama) tidak tersedia"},
    },
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_agent}/minute")
async def generate_latihan(request: Request, payload: PermintaanGenerateLatihan) -> ResponsLatihanDihasilkan:
    """Buat soal latihan Python baru secara dinamis menggunakan Gemma via Ollama.

    Contoh topic: `'variabel'`, `'loop'`, `'fungsi'`, `'list'`, `'rekursi'`
    """
    try:
        hasil = await gemma_service.generate_exercise(
            topic=payload.topic,
            difficulty=payload.difficulty,
            bahasa=payload.bahasa,
        )
    except LayananLLMError as exc:
        logger.error("LLM gagal generate latihan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Layanan AI tidak tersedia: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Error tak terduga saat generate latihan")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal membuat latihan: {exc}",
        ) from exc

    if "error" in hasil:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM mengembalikan respons tidak valid: {hasil.get('raw_response', '')[:200]}",
        )

    return ResponsLatihanDihasilkan(
        title=hasil.get("title", "Latihan Tanpa Judul"),
        instructions=hasil.get("instructions", ""),
        starter_code=hasil.get("starter_code", ""),
        solution=hasil.get("solution", ""),
        test_cases=hasil.get("test_cases", []),
    )


# =========================================================================== #
# Languages                                                                    #
# =========================================================================== #

@router.get(
    "/languages/",
    tags=["languages"],
    summary="Daftar bahasa daerah Indonesia yang didukung Gemma 4",
)
async def daftar_bahasa() -> dict[str, Any]:
    """Kembalikan daftar bahasa output AI yang tersedia.

    Gemma 4 mendukung 140+ bahasa. CodeBuddy fokus ke bahasa daerah Indonesia
    untuk akses pendidikan yang lebih inklusif.
    """
    return {
        "default": "id",
        "tersedia": [
            {"kode": kode, "nama": cfg["nama"], "salam": cfg["salam"]}
            for kode, cfg in BAHASA_DAERAH.items()
        ],
    }


# =========================================================================== #
# Audio (TTS + STT)                                                            #
# =========================================================================== #

from fastapi.responses import FileResponse  # noqa: E402

@router.post(
    "/audio/tts",
    tags=["audio"],
    summary="Generate suara dari teks (TTS) — untuk anak SD yang belum lancar baca",
    response_class=FileResponse,
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_per_minute}/minute")
async def text_to_speech(request: Request, payload: PermintaanTTS):
    """Konversi teks → file MP3 menggunakan edge-tts.

    Bahasa Indonesia natural dengan suara perempuan (Gadis) atau laki-laki (Ardi).
    Untuk bahasa daerah, fallback ke voice Indonesia.
    """
    from services.audio_service import tts_service, LayananAudioError  # noqa: PLC0415

    try:
        mp3_path = await tts_service.bicara(
            payload.teks,
            bahasa=payload.bahasa,
            gender=payload.gender,
        )
    except LayananAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"TTS gagal: {exc}",
        ) from exc

    return FileResponse(
        mp3_path,
        media_type="audio/mpeg",
        filename="codebuddy_tts.mp3",
    )


@router.post(
    "/audio/stt",
    tags=["audio"],
    summary="Transcribe audio → teks (STT) menggunakan Whisper offline",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_per_minute}/minute")
async def speech_to_text(
    request: Request,
    berkas: UploadFile = File(..., description="File audio (WAV/MP3/M4A) — maks 25 MB"),
    bahasa: str = "id",
):
    """Transcribe rekaman suara siswa menjadi teks.

    Berguna untuk:
    - Anak SD yang belum lancar mengetik
    - Siswa tunanetra
    - Pertanyaan natural dalam Bahasa Indonesia/daerah
    """
    from services.audio_service import stt_service, LayananAudioError  # noqa: PLC0415

    if not berkas.content_type or not berkas.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bukan file audio. Content-type: {berkas.content_type}",
        )

    isi = await berkas.read()
    if len(isi) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Audio melebihi 25 MB.",
        )

    sufiks = "." + (berkas.filename.split(".")[-1] if berkas.filename and "." in berkas.filename else "wav")
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=sufiks, delete=False) as tmp:
            tmp.write(isi)
            tmp_path = tmp.name

        hasil = await stt_service.dengar(tmp_path, bahasa=bahasa)
        return hasil

    except LayananAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"STT gagal: {exc}",
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.post(
    "/audio/ask",
    response_class=FileResponse,
    tags=["audio"],
    summary="End-to-end: rekam suara → AI jawab dengan suara",
)
@pembatas_per_ip.limit(f"{pengaturan.rate_limit_agent}/minute")
async def tanya_pakai_suara(
    request: Request,
    berkas: UploadFile = File(..., description="Rekaman pertanyaan dalam Bahasa Indonesia"),
    bahasa: str = "id",
    student_level: str = "beginner",
):
    """Pipeline lengkap untuk anak SD:
    1. Rekam pertanyaan (suara)
    2. Whisper transcribe → teks
    3. Gemma 4 jawab dalam Bahasa Indonesia/daerah
    4. edge-tts ubah jawaban → suara MP3
    5. Return MP3 untuk diputar

    Untuk anak yang belum lancar baca-tulis — bisa tanya pakai suara, dapat
    jawaban suara dalam bahasa ibu mereka.
    """
    from services.audio_service import stt_service, bicara_dari_pertanyaan, LayananAudioError  # noqa: PLC0415

    isi = await berkas.read()
    if not isi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File audio kosong. Rekam pertanyaan lagi, lalu kirim ulang.",
        )
    sufiks = "." + (berkas.filename.split(".")[-1] if berkas.filename and "." in berkas.filename else "wav")

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=sufiks, delete=False) as tmp:
            tmp.write(isi)
            tmp_path = tmp.name

        # 1. STT
        stt_hasil = await stt_service.dengar(tmp_path, bahasa=bahasa)
        pertanyaan = stt_hasil["teks"]

        if not pertanyaan.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Tidak ada suara yang terdeteksi. Coba merekam lebih dekat ke mikrofon, "
                    "bicara sedikit lebih keras, atau perpanjang rekaman beberapa detik."
                ),
            )

        # 2-4. AI + TTS
        hasil = await bicara_dari_pertanyaan(pertanyaan, bahasa=bahasa, student_level=student_level)

        # Header HTTP hanya boleh ASCII printable (0x20–0x7E).
        # Teks Indonesia + emoji di luar rentang itu menyebabkan
        # "Invalid HTTP header value" di uvicorn — filter ketat ke ASCII saja.
        def sanitasi_header(teks: str, maks: int = 200) -> str:
            hanya_ascii = "".join(
                karakter for karakter in teks[:maks]
                if 0x20 <= ord(karakter) <= 0x7E
            )
            return hanya_ascii

        return FileResponse(
            hasil["jawaban_audio"],
            media_type="audio/mpeg",
            filename="codebuddy_jawaban.mp3",
            headers={
                "X-Pertanyaan": sanitasi_header(pertanyaan),
                "X-Jawaban": sanitasi_header(hasil["jawaban_teks"]),
            },
        )

    except LayananAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Audio service gagal: {exc}",
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
