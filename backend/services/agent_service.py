"""Agen orkestrasi workflow tutoring kode — CodeBuddyAgent.

Workflow::

    Kode masuk
        │
        ▼
    [STAGE 1] Validasi Syntax ──── GAGAL ──▶ LLM jelaskan error ──▶ selesai
        │ LULUS
        ▼
    [STAGE 2] Eksekusi Sandbox ─── ERROR ──▶ [STAGE 3] Analisis Error + LLM fix ──▶ selesai
        │ SUKSES
        ▼
    [STAGE 4] Analisis Kualitas ──▶ LLM feedback ──▶ selesai
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from services.code_executor import SafeCodeExecutor, safe_executor
from services.llm_service import (
    GemmaService,
    LayananLLMError,
    gemma_service,
    kirim_chat_tutor,
)

logger = logging.getLogger(__name__)

# Nama stage yang konsisten di seluruh aplikasi
_STAGE_SYNTAX = "syntax_validation"
_STAGE_EXEC = "execution"
_STAGE_ANALYSIS = "error_analysis"
_STAGE_SUCCESS = "success_analysis"


# --------------------------------------------------------------------------- #
# ErrorInfo & ErrorDetector                                                    #
# --------------------------------------------------------------------------- #

class ErrorInfo:
    """Error Python yang sudah dipetakan ke Bahasa Indonesia."""

    __slots__ = ("raw_type", "raw_message", "category", "message_id", "suggestion")

    def __init__(
        self,
        raw_type: str,
        raw_message: str,
        category: str,
        message_id: str,
        suggestion: str,
    ) -> None:
        self.raw_type = raw_type
        self.raw_message = raw_message
        self.category = category    # 'syntax' | 'runtime' | 'logic' | 'timeout' | 'security'
        self.message_id = message_id  # Pesan Bahasa Indonesia
        self.suggestion = suggestion  # Saran singkat

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.raw_type,
            "message_raw": self.raw_message,
            "category": self.category,
            "message_id": self.message_id,
            "suggestion": self.suggestion,
        }


class ErrorDetector:
    """Deteksi dan klasifikasi error Python ke Bahasa Indonesia.

    Database kesalahan umum yang dipetakan ke penjelasan dan saran
    dalam Bahasa Indonesia yang ramah untuk pemula.

    Contoh::

        detector = ErrorDetector()
        info = detector.detect("NameError", "name 'x' is not defined")
        # info.message_id → "Variabel atau fungsi belum didefinisikan"
        # info.category   → "runtime"
    """

    # (category, message_id, suggestion)
    _ERROR_MAP: dict[str, tuple[str, str, str]] = {
        "NameError": (
            "runtime",
            "Variabel atau fungsi belum didefinisikan",
            "Pastikan nama variabel sudah benar dan sudah diberi nilai sebelum dipakai.",
        ),
        "SyntaxError": (
            "syntax",
            "Kesalahan penulisan kode (Syntax Error)",
            "Cek tanda kurung, titik dua, atau kutip yang tidak sesuai.",
        ),
        "IndentationError": (
            "syntax",
            "Indentasi (spasi) salah",
            "Gunakan 4 spasi secara konsisten untuk setiap level indentasi.",
        ),
        "TabError": (
            "syntax",
            "Campuran tab dan spasi untuk indentasi",
            "Pilih salah satu: hanya spasi (disarankan 4 spasi) atau hanya tab.",
        ),
        "TypeError": (
            "runtime",
            "Tipe data tidak sesuai",
            "Pastikan operasi dilakukan pada tipe yang cocok (misal: tidak menjumlah string dan angka).",
        ),
        "ValueError": (
            "runtime",
            "Nilai tidak valid untuk operasi ini",
            "Cek apakah nilai yang dimasukkan sesuai dengan yang diharapkan fungsi.",
        ),
        "IndexError": (
            "runtime",
            "Indeks di luar jangkauan list/string",
            "Pastikan indeks tidak melebihi panjangnya (ingat: dimulai dari 0).",
        ),
        "KeyError": (
            "runtime",
            "Kunci tidak ditemukan di dictionary",
            "Gunakan .get() atau periksa dulu apakah kunci ada dengan operator `in`.",
        ),
        "AttributeError": (
            "runtime",
            "Atribut atau method tidak ditemukan",
            "Cek nama method/atribut dan pastikan tipe objek yang digunakan sudah benar.",
        ),
        "ZeroDivisionError": (
            "runtime",
            "Tidak bisa dibagi dengan nol",
            "Tambahkan pengecekan `if pembagi != 0` sebelum melakukan pembagian.",
        ),
        "RecursionError": (
            "runtime",
            "Rekursi terlalu dalam (kemungkinan infinite loop)",
            "Pastikan fungsi rekursif memiliki kondisi berhenti (base case) yang jelas.",
        ),
        "TimeoutError": (
            "timeout",
            "Kode berjalan terlalu lama (batas waktu 5 detik)",
            "Cek apakah ada loop `while True` atau kondisi loop yang tidak pernah terpenuhi.",
        ),
        "SecurityError": (
            "security",
            "Operasi tidak diizinkan dalam sandbox",
            "Hindari penggunaan import, buka file, atau akses ke sistem operasi.",
        ),
        "MemoryError": (
            "runtime",
            "Memori habis",
            "Hindari membuat list, string, atau objek yang terlalu besar.",
        ),
        "OverflowError": (
            "runtime",
            "Angka terlalu besar untuk diproses",
            "Cek operasi matematika yang mungkin menghasilkan angka sangat besar.",
        ),
        "ValidationError": (
            "syntax",
            "Kode tidak lolos validasi awal",
            "Cek panjang atau konten kode yang dikirimkan.",
        ),
    }

    _FALLBACK: tuple[str, str, str] = (
        "runtime",
        "Terjadi error saat menjalankan kode",
        "Baca pesan error dengan saksama dan cek baris yang disebutkan.",
    )

    def detect(
        self,
        error_type: Optional[str],
        raw_message: str,
    ) -> ErrorInfo:
        """Petakan tipe error Python ke ErrorInfo bahasa Indonesia.

        Args:
            error_type: Nama tipe exception (misal 'NameError', atau None).
            raw_message: Pesan error asli dari Python/sandbox.

        Returns:
            ErrorInfo yang sudah dipetakan.
        """
        category, message_id, suggestion = self._ERROR_MAP.get(
            error_type or "", self._FALLBACK
        )
        return ErrorInfo(
            raw_type=error_type or "UnknownError",
            raw_message=raw_message,
            category=category,
            message_id=message_id,
            suggestion=suggestion,
        )

    @staticmethod
    def classify_final_result(attempts: list[dict[str, Any]]) -> str:
        """Tentukan hasil akhir sesi dari daftar attempt stages.

        Returns:
            'success' | 'syntax_error' | 'runtime_error' | 'timeout'
        """
        for attempt in reversed(attempts):
            if attempt.get("success") and attempt.get("stage") in (_STAGE_EXEC, _STAGE_SUCCESS):
                return "success"
            err = attempt.get("error") or {}
            category = err.get("category", "")
            raw_type = err.get("type", "")
            if category == "syntax" or raw_type in ("SyntaxError", "IndentationError", "TabError"):
                return "syntax_error"
            if category == "timeout" or raw_type == "TimeoutError":
                return "timeout"
        return "runtime_error"


# --------------------------------------------------------------------------- #
# CodeBuddyAgent                                                               #
# --------------------------------------------------------------------------- #

class CodeBuddyAgent:
    """Agen tutoring kode yang mengorkestrasikan workflow analisis otomatis.

    Agen mengambil keputusan secara mandiri di setiap tahap::

        1. Validasi syntax → jika gagal, minta LLM jelaskan → selesai
        2. Eksekusi sandbox → jika error, analisis + minta LLM → selesai
        3. Jika sukses, minta LLM evaluasi kualitas kode → selesai

    Fitur agentic:
    - Keputusan otomatis kapan harus berhenti vs melanjutkan pipeline.
    - Menyesuaikan kedalaman penjelasan LLM dengan level siswa.
    - Graceful fallback di setiap panggilan LLM.
    - Hint bertahap (3 level) yang tidak langsung memberi jawaban.

    Contoh::

        agent = CodeBuddyAgent()
        sesi = await agent.tutor_session("print(x)", student_id=1)
        print(sesi["final_result"])   # "runtime_error"
        print(sesi["attempts"][-1]["ai_feedback"]["encouragement"])
    """

    def __init__(
        self,
        llm: Optional[GemmaService] = None,
        executor: Optional[SafeCodeExecutor] = None,
        error_detector: Optional[ErrorDetector] = None,
    ) -> None:
        """Dependency injection — semua opsional, default ke singleton global."""
        self._llm = llm or gemma_service
        self._executor = executor or safe_executor
        self._detector = error_detector or ErrorDetector()

    # ----------------------------------------------------------------------- #
    # Public API                                                               #
    # ----------------------------------------------------------------------- #

    async def tutor_session(
        self,
        code: str,
        student_id: int,
        exercise_id: Optional[str] = None,
        student_level: str = "beginner",
        bahasa: str = "id",
    ) -> dict[str, Any]:
        """Sesi tutoring lengkap — otomatis mengorkestrasi semua tahap.

        Args:
            code: Kode Python dari siswa (teks atau hasil OCR).
            student_id: ID siswa untuk logging dan personalisasi.
            exercise_id: ID latihan dari manifest (opsional).
            student_level: 'beginner' | 'intermediate' | 'advanced'.

        Returns:
            Dict sesi::

                {
                    "student_id": 1,
                    "exercise_id": "variabel_01",
                    "original_code": "...",
                    "student_level": "beginner",
                    "attempts": [
                        {
                            "stage": "syntax_validation",
                            "success": True,
                            "output": "",
                            "error": None,
                            "ai_feedback": None
                        },
                        ...
                    ],
                    "final_result": "success" | "syntax_error" | "runtime_error" | "timeout"
                }
        """
        logger.info(
            "[Agen] Sesi dimulai — student_id=%d exercise=%s level=%s kode_panjang=%d",
            student_id, exercise_id, student_level, len(code),
        )
        attempts: list[dict[str, Any]] = []

        # ── STAGE 1: Validasi Syntax ─────────────────────────────────────── #
        logger.info("[Agen][1/4] Validasi syntax...")
        cek = await asyncio.to_thread(self._executor.validate_syntax, code)

        if not cek["valid"]:
            logger.info("[Agen][1/4] Syntax tidak valid: %s (baris %s)", cek["error"], cek["line"])
            error_info = self._detector.detect("SyntaxError", cek["error"] or "")
            attempts.append(_buat_attempt(_STAGE_SYNTAX, False, error=error_info.to_dict()))

            ai = await self._analisis_aman(
                code,
                {"type": "SyntaxError", "message": cek["error"], "line": cek["line"]},
                student_level,
                bahasa,
            )
            attempts.append(_buat_attempt(_STAGE_ANALYSIS, False, error=error_info.to_dict(), ai_feedback=ai))
            return self._kemas_hasil(student_id, exercise_id, code, student_level, attempts)

        attempts.append(_buat_attempt(_STAGE_SYNTAX, True))
        logger.info("[Agen][1/4] Syntax OK")

        # ── STAGE 2: Eksekusi Sandbox ─────────────────────────────────────── #
        logger.info("[Agen][2/4] Eksekusi kode di sandbox...")
        exec_result = await asyncio.to_thread(self._executor.execute, code)
        output = exec_result.get("output", "")

        if not exec_result["success"]:
            error_info = self._detector.detect(
                exec_result.get("error_type"),
                exec_result.get("error") or "",
            )
            logger.info(
                "[Agen][2/4] Eksekusi gagal [%s/%s]: %s",
                error_info.category, error_info.raw_type, error_info.message_id,
            )
            attempts.append(_buat_attempt(_STAGE_EXEC, False, output=output, error=error_info.to_dict()))

            # ── STAGE 3: Analisis Error ───────────────────────────────────── #
            logger.info("[Agen][3/4] Memanggil LLM untuk analisis error...")
            ai = await self._analisis_aman(
                code,
                {"type": error_info.raw_type, "message": error_info.raw_message},
                student_level,
                bahasa,
            )
            attempts.append(_buat_attempt(
                _STAGE_ANALYSIS, False,
                output=output,
                error=error_info.to_dict(),
                ai_feedback=ai,
            ))
            return self._kemas_hasil(student_id, exercise_id, code, student_level, attempts)

        attempts.append(_buat_attempt(_STAGE_EXEC, True, output=output))
        logger.info("[Agen][2/4] Eksekusi sukses. Output: %.80r", output)

        # ── STAGE 4: Analisis Kualitas ───────────────────────────────────── #
        logger.info("[Agen][4/4] Memanggil LLM untuk feedback kualitas kode...")
        ai = await self._analisis_aman(code, None, student_level, bahasa)
        attempts.append(_buat_attempt(_STAGE_SUCCESS, True, output=output, ai_feedback=ai))

        logger.info("[Agen] Sesi selesai: SUCCESS")
        return self._kemas_hasil(student_id, exercise_id, code, student_level, attempts)

    async def get_progressive_hint(
        self,
        code: str,
        error: str,
        hint_level: int,
        student_level: str = "beginner",
    ) -> str:
        """Berikan hint bertahap — tidak langsung memberi jawaban.

        Strategi agentic: tahan solusi selengkap mungkin di level awal
        agar siswa berpikir sendiri terlebih dahulu.

        Args:
            code: Kode siswa saat ini.
            error: Pesan error yang diterima.
            hint_level: 1 = pertanyaan pengarah, 2 = tunjuk lokasi, 3 = solusi penuh.
            student_level: Level siswa untuk menyesuaikan bahasa.

        Returns:
            String hint dalam Bahasa Indonesia.

        Contoh::

            hint = await agent.get_progressive_hint(
                code='print(x)', error="NameError: name 'x' is not defined", hint_level=1
            )
            # "Apa yang seharusnya dilakukan variabel tersebut sebelum dicetak?"
        """
        hint_level = max(1, min(3, hint_level))  # clamp 1–3
        logger.info("[Agen] get_progressive_hint level=%d level_siswa=%s", hint_level, student_level)

        prompt = self._buat_prompt_hint(code, error, hint_level, student_level)
        try:
            hasil = await kirim_chat_tutor(prompt)
            teks = (hasil.get("reply") or "").strip()
            return teks or _HINT_FALLBACK[hint_level]
        except LayananLLMError as exc:
            logger.warning("[Agen] LLM tidak tersedia untuk hint: %s", exc)
            return _HINT_FALLBACK[hint_level]

    # ----------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ----------------------------------------------------------------------- #

    async def _analisis_aman(
        self,
        code: str,
        error: Optional[dict[str, Any]],
        student_level: str,
        bahasa: str = "id",
    ) -> dict[str, Any]:
        """Panggil GemmaService.analyze_code dengan graceful fallback."""
        try:
            return await self._llm.analyze_code(
                code, error=error, student_level=student_level, bahasa=bahasa
            )
        except LayananLLMError as exc:
            logger.warning("[Agen] LLM gagal — menggunakan fallback: %s", exc)
            return _ai_fallback(error)

    def _kemas_hasil(
        self,
        student_id: int,
        exercise_id: Optional[str],
        code: str,
        student_level: str,
        attempts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        final = ErrorDetector.classify_final_result(attempts)
        logger.info(
            "[Agen] Hasil dikemas: final_result=%s stages=%d",
            final, len(attempts),
        )
        return {
            "student_id": student_id,
            "exercise_id": exercise_id,
            "original_code": code,
            "student_level": student_level,
            "attempts": attempts,
            "final_result": final,
        }

    @staticmethod
    def _buat_prompt_hint(
        code: str,
        error: str,
        hint_level: int,
        student_level: str,
    ) -> str:
        level_desc = {
            "beginner": "pemula (gunakan bahasa sangat sederhana, hindari istilah teknis)",
            "intermediate": "menengah (boleh pakai istilah teknis ringan)",
            "advanced": "lanjut (boleh langsung teknis dan ke inti masalah)",
        }.get(student_level, "pemula")

        instruksi = {
            1: (
                "Berikan HANYA satu pertanyaan pengarah yang membantu siswa berpikir sendiri. "
                "JANGAN sebutkan solusi, kode perbaikan, atau lokasi error secara eksplisit. "
                "Maksimal 2 kalimat. "
                "Contoh yang baik: 'Apa yang perlu ada sebelum sebuah variabel bisa dipakai dalam print?'"
            ),
            2: (
                "Tunjukkan LOKASI permasalahan secara spesifik (sebutkan nama variabel, fungsi, atau "
                "baris yang bermasalah) dan jelaskan singkat MENGAPA itu salah. "
                "JANGAN berikan kode perbaikan. Maksimal 3 kalimat."
            ),
            3: (
                "Tampilkan SOLUSI LENGKAP: kode yang sudah diperbaiki beserta penjelasan "
                "langkah demi langkah mengapa setiap perubahan diperlukan. "
                "Tutup dengan semangat untuk terus belajar."
            ),
        }[hint_level]

        return (
            f"Kamu adalah tutor Python yang sabar untuk siswa level {level_desc}.\n\n"
            f"Kode siswa:\n```python\n{code}\n```\n\n"
            f"Error yang terjadi:\n{error}\n\n"
            f"Instruksi: {instruksi}\n\n"
            f"Jawab dalam Bahasa Indonesia yang hangat dan menyemangati."
        )


# --------------------------------------------------------------------------- #
# Fungsi & data pendukung                                                      #
# --------------------------------------------------------------------------- #

def _buat_attempt(
    stage: str,
    success: bool,
    output: str = "",
    error: Optional[dict[str, Any]] = None,
    ai_feedback: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Buat satu entri attempt untuk daftar attempts sesi."""
    return {
        "stage": stage,
        "success": success,
        "output": output,
        "error": error,
        "ai_feedback": ai_feedback,
    }


_HINT_FALLBACK: dict[int, str] = {
    1: "Coba baca kembali kodenya dari awal — apa yang seharusnya terjadi di setiap baris?",
    2: (
        "Perhatikan pesan error dengan saksama — "
        "biasanya menyebut nama variabel atau nomor baris yang bermasalah."
    ),
    3: (
        "Maaf, tutor AI sedang tidak tersedia. "
        "Coba cek dokumentasi Python di python.org atau tanyakan ke teman."
    ),
}


def _ai_fallback(error: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Fallback AI feedback saat Ollama tidak tersedia."""
    ada_error = bool(error)
    return {
        "understanding": "Analisis AI tidak tersedia saat ini.",
        "errors": (
            [
                {
                    "line": None,
                    "explanation": error.get("message_id", str(error)),
                    "fix": error.get("suggestion", "Coba periksa kembali logika kode."),
                }
            ]
            if ada_error else []
        ),
        "suggestions": ["Jalankan kode, baca pesan error, dan coba perbaiki satu per satu."],
        "corrected_code": "",
        "encouragement": "Semangat! Setiap error adalah kesempatan belajar. Kamu pasti bisa!",
    }


# --------------------------------------------------------------------------- #
# Singleton                                                                    #
# --------------------------------------------------------------------------- #

code_buddy_agent = CodeBuddyAgent()
