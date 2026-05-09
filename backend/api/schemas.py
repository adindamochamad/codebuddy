"""Skema request/response Pydantic untuk semua endpoint CodeBuddy."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Health                                                                       #
# --------------------------------------------------------------------------- #

class ResponsKesehatan(BaseModel):
    status: str = "ok"
    layanan: str = Field(default="CodeBuddy API")


# --------------------------------------------------------------------------- #
# OCR                                                                          #
# --------------------------------------------------------------------------- #

class ResponsEkstrakOCR(BaseModel):
    """Hasil ekstraksi kode dari gambar."""

    success: bool
    code: str = Field(description="Kode Python yang berhasil diekstrak")
    confidence: float = Field(ge=0.0, le=1.0, description="Tingkat kepercayaan OCR (0–1)")
    lines: list[dict[str, Any]] = Field(default_factory=list, description="Detail baris mentah OCR")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"success": True, "code": "print('halo')", "confidence": 0.95, "lines": []}
            ]
        }
    }


# Backward compat (masih dipakai api/ocr.py lama)
class ResponsOCR(BaseModel):
    text: str
    lines: list[dict[str, Any]]
    engine: str


# --------------------------------------------------------------------------- #
# Code Execution                                                               #
# --------------------------------------------------------------------------- #

class PermintaanEksekusiKode(BaseModel):
    kode: str = Field(
        ..., min_length=1, max_length=8000,
        description="Kode Python yang akan dijalankan di sandbox",
        examples=["print('halo dunia')"],
    )


class ResponsEksekusiKode(BaseModel):
    sukses: bool
    stdout: str
    stderr: str
    error_kind: Optional[str] = None


class PermintaanValidasiKode(BaseModel):
    kode: str = Field(
        ..., min_length=1, max_length=8000,
        description="Kode Python yang akan dicek sintaksnya",
        examples=["def f():\n    pass"],
    )


class ResponsValidasiKode(BaseModel):
    valid: bool
    error: Optional[str] = None
    line: Optional[int] = None


# --------------------------------------------------------------------------- #
# Agent / Tutor                                                                #
# --------------------------------------------------------------------------- #

class PesanChat(BaseModel):
    role: str
    content: str


class PermintaanTutor(BaseModel):
    """Payload untuk sesi tutor berbasis chat sederhana (backward compat)."""

    pesan: str = Field(..., min_length=1)
    konteks_sistem: Optional[str] = Field(default=None)
    riwayat: Optional[list[PesanChat]] = None


class ResponsTutor(BaseModel):
    reply: str
    model: str


class PermintaanTutorAgen(BaseModel):
    """Payload untuk sesi tutoring lengkap via CodeBuddyAgent."""

    code: str = Field(
        ..., min_length=1, max_length=8000,
        description="Kode Python dari siswa (teks langsung atau hasil OCR)",
        examples=["for i in range(10)\n    print(i)"],
    )
    student_id: int = Field(..., ge=1, description="ID siswa")
    exercise_id: Optional[str] = Field(None, description="ID latihan dari manifest")
    student_level: str = Field(
        "beginner",
        description="Level siswa: 'beginner' | 'intermediate' | 'advanced'",
    )
    bahasa: str = Field(
        "id",
        description="Bahasa output AI: 'id'|'jw'|'su'|'min'|'bbc' (Indonesia/Jawa/Sunda/Minang/Batak)",
    )


class AttemptItem(BaseModel):
    """Satu tahap dalam pipeline tutoring."""

    stage: str
    success: bool
    output: str = ""
    error: Optional[dict[str, Any]] = None
    ai_feedback: Optional[dict[str, Any]] = None


class ResponsTutorAgen(BaseModel):
    """Hasil lengkap sesi tutoring agentic."""

    student_id: int
    exercise_id: Optional[str]
    original_code: str
    student_level: str
    attempts: list[AttemptItem]
    final_result: str = Field(
        description="'success' | 'syntax_error' | 'runtime_error' | 'timeout'"
    )


class PermintaanHint(BaseModel):
    code: str = Field(..., min_length=1, max_length=8000)
    error: str = Field(..., min_length=1, description="Pesan error yang diterima siswa")
    hint_level: int = Field(1, ge=1, le=3, description="1=pertanyaan, 2=lokasi, 3=solusi")
    student_level: str = Field("beginner")


class ResponsHint(BaseModel):
    hint: str
    hint_level: int


# --------------------------------------------------------------------------- #
# Students                                                                     #
# --------------------------------------------------------------------------- #

class PermintaanBuatSiswa(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Budi Santoso"])
    age: Optional[int] = Field(None, ge=5, le=100)
    level: Optional[str] = Field(None, description="'beginner' | 'intermediate' | 'advanced'")


class ResponsSiswa(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    age: Optional[int]
    level: Optional[str]
    created_at: datetime


class RingkasanLatihan(BaseModel):
    exercise_id: str
    completed: bool
    attempts: int
    avg_score: Optional[float]


class ResponsProgresSiswa(BaseModel):
    student_id: int
    nama: Optional[str]
    level: Optional[str]
    latihan: list[RingkasanLatihan]
    total_selesai: int
    rata_rata_skor: Optional[float]


# --------------------------------------------------------------------------- #
# Exercises                                                                    #
# --------------------------------------------------------------------------- #

class ItemLatihan(BaseModel):
    exercise_id: str
    judul: str
    ringkas: str
    starter_code: str
    difficulty: str


class ResponsDaftarLatihan(BaseModel):
    total: int
    latihan: list[ItemLatihan]


class PermintaanGenerateLatihan(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100, examples=["variabel", "loop", "fungsi"])
    difficulty: str = Field(
        "beginner",
        description="'beginner' | 'intermediate' | 'advanced'",
    )
    bahasa: str = Field("id", description="Bahasa soal: id|jw|su|min|bbc")


class KasusUji(BaseModel):
    input: Optional[str]
    expected_output: str
    description: str


class ResponsLatihanDihasilkan(BaseModel):
    title: str
    instructions: str
    starter_code: str
    solution: str
    test_cases: list[dict[str, Any]]


# --------------------------------------------------------------------------- #
# Audio                                                                        #
# --------------------------------------------------------------------------- #

class PermintaanTTS(BaseModel):
    teks: str = Field(..., min_length=1, max_length=2000)
    bahasa: str = Field("id", description="id|jw|su|min|bbc")
    gender: str = Field("female", description="'female' atau 'male' (hanya untuk Indonesia)")


class ResponsTTS(BaseModel):
    audio_url: str
    bahasa: str
    durasi_estimasi_detik: float


class PermintaanBicaraDariSuara(BaseModel):
    bahasa: str = Field("id")
    student_level: str = Field("beginner")


class ResponsBicaraDariSuara(BaseModel):
    pertanyaan: str
    jawaban_teks: str
    audio_url: str
    bahasa: str
