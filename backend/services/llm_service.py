"""Klien async ke Ollama — GemmaService untuk analisis kode dan tutoring."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

import httpx

from utils.config import pengaturan

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemma4:e4b"
_TIMEOUT = 60.0
_MAX_RETRIES = 3


# Bahasa daerah Indonesia yang didukung — Gemma 4 fasih 140+ bahasa
BAHASA_DAERAH: dict[str, dict[str, str]] = {
    "id": {
        "nama": "Bahasa Indonesia",
        "instruksi": "Jawab dalam Bahasa Indonesia yang ramah dan mudah dipahami anak SD.",
        "salam": "Halo! Aku CodeBuddy, tutor coding untuk kamu!",
    },
    "jw": {
        "nama": "Basa Jawa Krama",
        "instruksi": (
            "Wangsulana nganggo basa Jawa krama alus sing gampang dipahami bocah SD. "
            "Gunakake tembung-tembung sing prasaja lan kebak sumanggem."
        ),
        "salam": "Sugeng rawuh! Kula CodeBuddy, tutor coding kanggo panjenengan!",
    },
    "su": {
        "nama": "Basa Sunda",
        "instruksi": (
            "Jawab dina basa Sunda nu lemes jeung gampang dipikaharti budak SD. "
            "Pake kecap-kecap nu basajan sareng nyumangetan."
        ),
        "salam": "Wilujeng sumping! Abdi CodeBuddy, tutor coding pikeun anjeun!",
    },
    "min": {
        "nama": "Bahaso Minang",
        "instruksi": (
            "Jawek dalam bahaso Minang nan elok dan mudah dipahami anak SD. "
            "Pakai kato-kato nan sederhana dan manyamangaikan."
        ),
        "salam": "Salamaik datang! Ambo CodeBuddy, tutor coding untuak adiak!",
    },
    "bbc": {
        "nama": "Bahasa Batak Toba",
        "instruksi": (
            "Alusi ma alusna marhite hata Batak Toba na denggan jala mudah diantusi anak SD. "
            "Pamake hata-hata na sederhana jala mambahen marsihaposan."
        ),
        "salam": "Horas! Au CodeBuddy, tutor coding tu ho!",
    },
}


def _get_bahasa_config(bahasa: str) -> dict[str, str]:
    """Ambil konfigurasi bahasa, default ke Bahasa Indonesia."""
    return BAHASA_DAERAH.get(bahasa, BAHASA_DAERAH["id"])


class LayananLLMError(RuntimeError):
    """Gagal memanggil API Ollama atau respons tidak valid."""


class GemmaService:
    """Layanan LLM berbasis Gemma via Ollama untuk analisis kode dan tutoring."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._base_url = (base_url or pengaturan.ollama_base_url).rstrip("/")
        self._model = model

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def analyze_code(
        self,
        code: str,
        error: Optional[dict[str, Any]] = None,
        student_level: str = "beginner",
        bahasa: str = "id",
    ) -> dict[str, Any]:
        """Analisis kode siswa — pakai function calling Gemma 4 untuk JSON terstruktur.

        Args:
            code: Kode Python yang akan dianalisis.
            error: Dict error opsional (misal dari executor_service).
            student_level: 'beginner' | 'intermediate' | 'advanced'.
            bahasa: 'id' | 'jw' | 'su' | 'min' | 'bbc' — bahasa output AI.

        Returns:
            Dict dengan kunci: understanding, errors, suggestions,
            corrected_code, encouragement.
        """
        prompt = self._build_analyze_prompt(code, error, student_level, bahasa)
        # Coba function calling dulu (Gemma 4), fallback ke text parsing
        schema = {
            "type": "object",
            "properties": {
                "understanding": {"type": "string"},
                "errors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "line": {"type": ["integer", "null"]},
                            "explanation": {"type": "string"},
                            "fix": {"type": "string"},
                        },
                    },
                },
                "suggestions": {"type": "array", "items": {"type": "string"}},
                "corrected_code": {"type": "string"},
                "encouragement": {"type": "string"},
            },
            "required": ["understanding", "errors", "suggestions", "corrected_code", "encouragement"],
        }
        try:
            return await self._call_ollama_structured(prompt, schema)
        except LayananLLMError:
            raw = await self._call_ollama(prompt)
            return self._parse_json_response(raw)

    async def generate_exercise(
        self,
        topic: str,
        difficulty: str = "beginner",
        bahasa: str = "id",
    ) -> dict[str, Any]:
        """Buat soal latihan Python — pakai function calling untuk output terstruktur.

        Args:
            topic: Topik soal, misal 'variabel', 'loop', 'fungsi'.
            difficulty: 'beginner' | 'intermediate' | 'advanced'.
            bahasa: 'id' | 'jw' | 'su' | 'min' | 'bbc' — bahasa untuk soal.

        Returns:
            Dict dengan kunci: title, instructions, starter_code, solution, test_cases.
        """
        prompt = self._build_exercise_prompt(topic, difficulty, bahasa)
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "instructions": {"type": "string"},
                "starter_code": {"type": "string"},
                "solution": {"type": "string"},
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "input": {"type": ["string", "null"]},
                            "expected_output": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["title", "instructions", "starter_code", "solution", "test_cases"],
        }
        try:
            return await self._call_ollama_structured(prompt, schema)
        except LayananLLMError:
            raw = await self._call_ollama(prompt)
            return self._parse_json_response(raw)

    # ------------------------------------------------------------------ #
    # Prompt builders                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_analyze_prompt(
        code: str,
        error: Optional[dict[str, Any]],
        student_level: str,
        bahasa: str = "id",
    ) -> str:
        bahasa_cfg = _get_bahasa_config(bahasa)
        level_desc = {
            "beginner": "pemula (anak SD, baru belajar Python — pakai analogi sangat sederhana seperti makanan, mainan, atau hewan)",
            "intermediate": "menengah (sudah paham dasar Python)",
            "advanced": "lanjut (bisa terima penjelasan teknis mendalam)",
        }.get(student_level, "pemula (anak SD)")

        error_section = ""
        if error:
            error_section = (
                f"\nPesan error yang diterima siswa:\n"
                f"{json.dumps(error, ensure_ascii=False, indent=2)}\n"
            )

        return f"""Kamu adalah tutor Python untuk anak Indonesia. Siswa di level {level_desc}.

PENTING: {bahasa_cfg['instruksi']}
Bahasa output: {bahasa_cfg['nama']}.
{error_section}
Analisis kode berikut. Kembalikan HANYA JSON valid:

```python
{code}
```

Format JSON wajib (output dalam {bahasa_cfg['nama']}, kecuali kode tetap Python):
{{
  "understanding": "penjelasan singkat apa yang dicoba kode ini lakukan (1-2 kalimat dalam {bahasa_cfg['nama']})",
  "errors": [
    {{
      "line": 5,
      "explanation": "penjelasan error dalam {bahasa_cfg['nama']} yang mudah dipahami anak SD",
      "fix": "cara memperbaiki dengan contoh konkret"
    }}
  ],
  "suggestions": [
    "saran dalam {bahasa_cfg['nama']}"
  ],
  "corrected_code": "kode Python yang sudah diperbaiki (gunakan \\n untuk baris baru)",
  "encouragement": "pesan semangat hangat dalam {bahasa_cfg['nama']}, panggil seperti memanggil adik atau anak"
}}

Aturan:
- Jika tidak ada error: `"errors": []`.
- `corrected_code` HARUS Python (kode tidak diterjemahkan ke bahasa daerah).
- Penjelasan, saran, semangat WAJIB dalam {bahasa_cfg['nama']}.
- Gunakan analogi yang familiar untuk anak Indonesia (warung, sekolah, layangan, dll.)
- JANGAN tambahkan teks di luar blok JSON.
"""

    @staticmethod
    def _build_exercise_prompt(topic: str, difficulty: str, bahasa: str = "id") -> str:
        bahasa_cfg = _get_bahasa_config(bahasa)
        difficulty_desc = {
            "beginner": "sangat mudah untuk anak SD — satu konsep saja, pakai variabel dan print sederhana",
            "intermediate": "sedang — boleh pakai fungsi, kondisi if/else, dan loop",
            "advanced": "menantang — bisa pakai OOP, rekursi, atau struktur data",
        }.get(difficulty, "sangat mudah untuk anak SD")

        return f"""Kamu adalah tutor Python kreatif untuk anak Indonesia.
Buat SATU soal latihan Python tentang topik: "{topic}".
Tingkat kesulitan: {difficulty_desc}.

PENTING: {bahasa_cfg['instruksi']}
Bahasa instruksi soal: {bahasa_cfg['nama']}.

Kembalikan HANYA JSON valid:
{{
  "title": "Judul soal yang menarik dalam {bahasa_cfg['nama']}",
  "instructions": "Instruksi lengkap dalam {bahasa_cfg['nama']}, ramah anak SD. Pakai konteks Indonesia (warung, sekolah, sepak bola, layangan, dll).",
  "starter_code": "Kode BELUM LENGKAP — siswa harus mengisi bagian yang kosong. WAJIB gunakan salah satu atau kombinasi: (1) '# TODO: <petunjuk>' untuk baris yang harus diisi, (2) 'pass' sebagai placeholder fungsi kosong, (3) '___' untuk nilai/ekspresi yang harus diisi. JANGAN tulis solusi lengkap di sini. Contoh format:\\n# TODO: isi nama variabelmu\\nnama = ___\\n# TODO: cetak sapaan\\nprint(___)",
  "solution": "# Solusi Python lengkap yang benar (komentar dalam {bahasa_cfg['nama']})",
  "test_cases": [
    {{
      "input": "nilai input atau null",
      "expected_output": "output yang diharapkan",
      "description": "deskripsi singkat dalam {bahasa_cfg['nama']}"
    }}
  ]
}}

Aturan WAJIB untuk starter_code:
- HARUS ada minimal 2 baris dengan '# TODO:' atau '___' yang perlu diisi siswa.
- JANGAN tulis kode yang langsung bisa dijalankan dan menghasilkan output benar.
- JANGAN sertakan solusinya di starter_code.
- Siswa harus mengisi sendiri agar program berjalan.
- Soal pakai konteks Indonesia/lokal yang familiar untuk anak.
- test_cases minimal 2 kasus uji.
- JANGAN tambahkan teks apapun di luar blok JSON.
"""

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    async def _call_ollama_structured(
        self, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Panggil Ollama dengan format JSON terstruktur (Gemma 4 function calling).

        Menggunakan parameter `format` Ollama untuk memastikan output selalu
        valid JSON sesuai schema — tidak perlu regex parsing.
        """
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0.3},
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content: str = data.get("message", {}).get("content") or ""
                return json.loads(content.strip())
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LayananLLMError(f"Structured call gagal: {exc}") from exc

    async def _call_ollama(self, prompt: str) -> str:
        """POST prompt ke Ollama dengan retry 3x dan timeout 30 detik.

        Retry dilakukan pada: timeout, connection error, HTTP 5xx.
        Tidak retry pada HTTP 4xx (error klien, tidak akan sembuh sendiri).
        Delay antar retry: 1s → 2s → 4s (exponential backoff).
        """
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        last_exc: Exception = RuntimeError("Belum ada percobaan.")
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content: str = data.get("message", {}).get("content") or ""
                    return content.strip()

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "Ollama timeout (percobaan %d/%d): %s", attempt, _MAX_RETRIES, exc
                )

            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "Ollama tidak terjangkau (percobaan %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.error(
                    "Ollama HTTP error %s (percobaan %d/%d): %s",
                    exc.response.status_code,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if exc.response.status_code < 500:
                    # Error 4xx tidak akan sembuh dengan retry
                    break

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.error(
                    "Error tak terduga saat memanggil Ollama (percobaan %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )

            if attempt < _MAX_RETRIES:
                delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.info("Menunggu %ds sebelum mencoba ulang...", delay)
                await asyncio.sleep(delay)

        raise LayananLLMError(
            f"Ollama tidak merespons setelah {_MAX_RETRIES} percobaan: {last_exc}"
        )

    @staticmethod
    def _parse_json_response(response: str) -> dict[str, Any]:
        """Ekstrak dan parse JSON dari respons LLM.

        Strategi (urutan prioritas):
        1. Parse langsung sebagai JSON.
        2. Ekstrak dari blok ```json ... ``` atau ``` ... ```.
        3. Cari objek JSON pertama dengan regex (greedy).
        4. Fallback: kembalikan dict error dengan raw response.
        """
        # 1. Parse langsung
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 2. Blok markdown ```json ... ``` atau ``` ... ```
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Objek JSON pertama di dalam teks bebas
        obj_match = re.search(r"\{.*\}", response, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group())
            except json.JSONDecodeError:
                pass

        logger.error(
            "Gagal mem-parse JSON dari respons LLM. Cuplikan: %.300s", response
        )
        return {
            "error": "Gagal mem-parse respons LLM sebagai JSON.",
            "raw_response": response[:500],
        }


# Singleton yang siap dipakai di seluruh aplikasi
gemma_service = GemmaService()


# ------------------------------------------------------------------ #
# Gemma 4 Vision Service — OCR tulisan tangan via multimodal         #
# ------------------------------------------------------------------ #

class GemmaVisionService:
    """Ekstraksi kode Python dari gambar menggunakan Gemma 4 multimodal.

    Menggantikan PaddleOCR — tidak perlu instalasi dependensi berat.
    Gemma 4 membaca gambar secara native dan memahami konteks kode Python.

    Contoh::

        svc = GemmaVisionService()
        hasil = await svc.ekstrak_kode(image_bytes)
        # {'code': 'print("halo")', 'confidence': 0.92, 'language': 'python'}
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or pengaturan.ollama_base_url).rstrip("/")
        self._model = model or pengaturan.ollama_vision_model

    async def ekstrak_kode(
        self,
        image_bytes: bytes,
        bahasa_pelajar: str = "id",
    ) -> dict[str, Any]:
        """Ekstrak kode Python dari bytes gambar menggunakan Gemma 4 Vision.

        Args:
            image_bytes: Konten file gambar (JPG/PNG).
            bahasa_pelajar: Kode bahasa untuk konteks ('id' = Indonesia).

        Returns:
            Dict dengan kunci:
            - ``code``       : str — kode Python hasil ekstraksi
            - ``confidence`` : float — estimasi kepercayaan (0–1)
            - ``raw_text``   : str — teks mentah dari model
            - ``engine``     : str — 'gemma4-vision'
        """
        import base64  # noqa: PLC0415

        img_b64 = base64.b64encode(image_bytes).decode()

        prompt = (
            "Kamu adalah sistem OCR untuk kode Python tulisan tangan siswa.\n"
            "Lihat gambar ini dengan seksama.\n\n"
            "Tugas:\n"
            "1. Baca semua teks kode Python yang ada di gambar\n"
            "2. Pertahankan indentasi dengan tepat (sangat penting untuk Python!)\n"
            "3. Perbaiki karakter yang mungkin salah baca (misal: O vs 0, l vs 1)\n\n"
            "Kembalikan HANYA JSON ini (tanpa teks lain):\n"
            '{"code": "kode python yang diekstrak dengan newline sebagai \\n", '
            '"confidence": 0.95, '
            '"notes": "catatan jika ada bagian yang tidak terbaca"}'
        )

        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_b64],
                }
            ],
            "stream": False,
            "options": {"temperature": 0.1},  # rendah agar output deterministik
        }

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw = data.get("message", {}).get("content", "").strip()

                parsed = GemmaService._parse_json_response(raw)
                if "error" in parsed:
                    logger.warning("Vision: JSON parse gagal, pakai raw text")
                    return {
                        "code": raw,
                        "confidence": 0.5,
                        "raw_text": raw,
                        "engine": "gemma4-vision",
                    }

                return {
                    "code": parsed.get("code", ""),
                    "confidence": float(parsed.get("confidence", 0.8)),
                    "raw_text": raw,
                    "engine": "gemma4-vision",
                    "notes": parsed.get("notes", ""),
                }

            except httpx.TimeoutException as exc:
                logger.warning("Vision timeout percobaan %d/%d", attempt, _MAX_RETRIES)
                if attempt == _MAX_RETRIES:
                    raise LayananLLMError(f"Gemma Vision timeout: {exc}") from exc
            except httpx.ConnectError as exc:
                raise LayananLLMError(
                    "Ollama tidak berjalan. Jalankan: ollama serve"
                ) from exc

            await asyncio.sleep(2 ** (attempt - 1))

        raise LayananLLMError("Gemma Vision gagal setelah semua percobaan.")

    async def analisis_gambar_kode(
        self,
        image_bytes: bytes,
        student_level: str = "beginner",
    ) -> dict[str, Any]:
        """Ekstrak DAN analisis kode dalam satu panggilan — efisien untuk Gemma 4.

        Gemma 4 membaca gambar + langsung memberi feedback dalam satu inference.
        Ini keunggulan unik dibanding pipeline OCR terpisah.
        """
        import base64  # noqa: PLC0415

        img_b64 = base64.b64encode(image_bytes).decode()

        level_desc = {
            "beginner": "pemula (gunakan analogi sederhana)",
            "intermediate": "menengah",
            "advanced": "lanjut (bisa teknis)",
        }.get(student_level, "pemula")

        prompt = (
            f"Kamu adalah tutor Python untuk siswa level {level_desc}.\n"
            "Lihat gambar kode Python tulisan tangan ini.\n\n"
            "Lakukan dua hal sekaligus:\n"
            "1. Baca kode dengan tepat (pertahankan indentasi)\n"
            "2. Analisis kode tersebut\n\n"
            "Kembalikan JSON ini saja:\n"
            "{\n"
            '  "code": "kode yang diekstrak",\n'
            '  "understanding": "apa yang dicoba kode ini lakukan",\n'
            '  "errors": [{"line": 1, "explanation": "...", "fix": "..."}],\n'
            '  "corrected_code": "kode yang diperbaiki",\n'
            '  "encouragement": "pesan semangat dalam Bahasa Indonesia"\n'
            "}"
        )

        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
            "stream": False,
            "options": {"temperature": 0.3},
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw = data.get("message", {}).get("content", "").strip()
                return GemmaService._parse_json_response(raw)
        except httpx.ConnectError as exc:
            raise LayananLLMError("Ollama tidak berjalan.") from exc
        except Exception as exc:  # noqa: BLE001
            raise LayananLLMError(f"Gemma Vision analisis gagal: {exc}") from exc


# Singleton Vision
gemma_vision_service = GemmaVisionService()


# ------------------------------------------------------------------ #
# Backward-compatible standalone function (dipakai api/tutor.py)     #
# ------------------------------------------------------------------ #

async def kirim_chat_tutor(
    pesan_user: str,
    *,
    konteks_sistem: Optional[str] = None,
    riwayat: Optional[list[dict[str, str]]] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> dict[str, Any]:
    """Memanggil /api/chat Ollama dengan model yang dikonfigurasi.

    Mengembalikan dict dengan kunci `reply` dan metadata mentah opsional.
    Dipertahankan untuk kompatibilitas dengan api/tutor.py.
    """
    url = f"{pengaturan.ollama_base_url.rstrip('/')}/api/chat"
    pesan: list[dict[str, str]] = []
    if konteks_sistem:
        pesan.append({"role": "system", "content": konteks_sistem})
    if riwayat:
        pesan.extend(riwayat)
    pesan.append({"role": "user", "content": pesan_user})

    payload = {
        "model": pengaturan.ollama_model,
        "messages": pesan,
        "stream": False,
    }

    async def _panggil(target: httpx.AsyncClient) -> dict[str, Any]:
        try:
            respons = await target.post(url, json=payload)
            respons.raise_for_status()
            data = respons.json()
        except httpx.HTTPError as exc:
            raise LayananLLMError(f"HTTP Ollama gagal: {exc}") from exc
        except ValueError as exc:
            raise LayananLLMError(f"Respons Ollama bukan JSON valid: {exc}") from exc

        message = data.get("message") or {}
        konten = message.get("content") or ""
        return {
            "reply": konten.strip(),
            "model": data.get("model") or pengaturan.ollama_model,
            "done": data.get("done", True),
            "raw": data,
        }

    if client is None:
        async with httpx.AsyncClient(timeout=120.0) as client_baru:
            return await _panggil(client_baru)
    return await _panggil(client)
