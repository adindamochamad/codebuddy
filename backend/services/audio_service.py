"""Audio service — TTS (text-to-speech) dan STT (speech-to-text) Bahasa Indonesia.

Untuk anak SD yang belum lancar baca-tulis, atau siswa tunanetra:
- TTS: AI bicara feedback dalam Bahasa Indonesia/daerah
- STT: Anak bisa "ngomong" pertanyaan, AI transcribe ke teks

Stack:
- TTS: edge-tts (Microsoft Edge TTS, free, suara natural Bahasa Indonesia)
- STT: faster-whisper (offline, lokal, support Bahasa Indonesia)

Kedua library ini gratis dan tidak butuh API key.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Voice IDs edge-tts untuk bahasa Indonesia (yang ada di edge-tts)
# `edge-tts --list-voices | grep id-ID`
TTS_VOICES: dict[str, dict[str, str]] = {
    "id": {
        "voice": "id-ID-GadisNeural",      # Suara perempuan natural Indonesia
        "voice_male": "id-ID-ArdiNeural",  # Suara laki-laki Indonesia
    },
    # Bahasa daerah belum punya voice TTS native
    # Fallback ke suara Indonesia (Gemma generate teks dalam bahasa daerah,
    # tapi pengucapan pakai voice Indonesia — masih bisa dimengerti)
    "jw": {"voice": "id-ID-GadisNeural"},
    "su": {"voice": "id-ID-GadisNeural"},
    "min": {"voice": "id-ID-GadisNeural"},
    "bbc": {"voice": "id-ID-GadisNeural"},
}


class LayananAudioError(RuntimeError):
    """Layanan audio (TTS/STT) gagal."""


# =========================================================================== #
# TTS — Text to Speech                                                         #
# =========================================================================== #

class TTSService:
    """Konversi teks → suara MP3 menggunakan edge-tts (Microsoft, gratis).

    Contoh::

        tts = TTSService()
        mp3_path = await tts.bicara("Halo, semangat belajar ya!", bahasa="id")
        # mp3_path: '/tmp/codebuddy_tts_xxx.mp3'
    """

    def __init__(self, default_bahasa: str = "id") -> None:
        self.default_bahasa = default_bahasa

    async def bicara(
        self,
        teks: str,
        bahasa: str = "id",
        gender: str = "female",
        rate: str = "+0%",
    ) -> str:
        """Generate file MP3 dari teks.

        Args:
            teks: Teks yang akan dibacakan.
            bahasa: 'id'/'jw'/'su'/'min'/'bbc' — pilih voice (fallback ke Indonesia).
            gender: 'female' (Gadis) atau 'male' (Ardi) — hanya untuk Indonesia.
            rate: Kecepatan, contoh: '+0%', '-20%', '+20%'.

        Returns:
            Path file MP3 hasil generate.
        """
        try:
            import edge_tts  # noqa: PLC0415
        except ImportError as exc:
            raise LayananAudioError("edge-tts belum terpasang.") from exc

        if not teks.strip():
            raise LayananAudioError("Teks kosong, tidak bisa di-TTS-kan.")

        voice_config = TTS_VOICES.get(bahasa, TTS_VOICES["id"])
        voice = voice_config.get(
            "voice_male" if gender == "male" else "voice",
            voice_config["voice"],
        )

        # Bersihkan teks dari markdown agar tidak terbaca aneh
        teks_bersih = self._bersihkan_untuk_tts(teks)

        # Generate MP3 ke file temporary
        out_path = tempfile.mktemp(suffix=".mp3", prefix="codebuddy_tts_")

        try:
            communicate = edge_tts.Communicate(
                teks_bersih,
                voice=voice,
                rate=rate,
            )
            await communicate.save(out_path)
            logger.info(
                "TTS generated: bahasa=%s voice=%s panjang_teks=%d → %s",
                bahasa, voice, len(teks_bersih), out_path,
            )
            return out_path
        except Exception as exc:  # noqa: BLE001
            raise LayananAudioError(f"TTS gagal: {exc}") from exc

    @staticmethod
    def _bersihkan_untuk_tts(teks: str) -> str:
        """Hapus markdown/kode agar TTS tidak terbaca aneh."""
        import re  # noqa: PLC0415

        # Hapus blok kode
        teks = re.sub(r"```[\s\S]*?```", " (lihat kode di layar) ", teks)
        # Hapus inline code
        teks = re.sub(r"`([^`]+)`", r"\1", teks)
        # Hapus bold/italic markers
        teks = re.sub(r"\*\*([^*]+)\*\*", r"\1", teks)
        teks = re.sub(r"\*([^*]+)\*", r"\1", teks)
        # Hapus heading markers
        teks = re.sub(r"^#+\s+", "", teks, flags=re.MULTILINE)
        # Hapus emoji yang aneh dibaca
        teks = re.sub(r"[❌✅🔴🟡⚠️💡🎯🚀✨🌱🔍]", "", teks)
        # Spasi berlebih
        teks = re.sub(r"\s+", " ", teks).strip()
        return teks


# =========================================================================== #
# STT — Speech to Text                                                         #
# =========================================================================== #

class STTService:
    """Konversi audio → teks menggunakan faster-whisper (offline).

    Pertama kali dipanggil akan download model (~ 75MB untuk model 'tiny').
    Setelah itu jalan offline.

    Contoh::

        stt = STTService()
        teks = await stt.dengar("/path/audio.wav", bahasa="id")
    """

    _model: Any = None  # Lazy-loaded singleton

    def __init__(self, model_size: str = "small") -> None:
        """
        Args:
            model_size: 'tiny' (75MB) | 'base' (140MB) | 'small' (460MB) |
                        'medium' (1.5GB) | 'large' (3GB).
                        'small' direkomendasikan untuk Bahasa Indonesia di M1.
        """
        self.model_size = model_size

    def _get_model(self) -> Any:
        if STTService._model is None:
            try:
                from faster_whisper import WhisperModel  # noqa: PLC0415
            except ImportError as exc:
                raise LayananAudioError("faster-whisper belum terpasang.") from exc

            logger.info("Loading Whisper %s (lazy, satu kali saja)...", self.model_size)
            STTService._model = WhisperModel(
                self.model_size,
                device="cpu",        # M1 jalan baik di CPU
                compute_type="int8",  # Quantized untuk speed di CPU
            )
            logger.info("Whisper %s loaded.", self.model_size)
        return STTService._model

    async def dengar(
        self,
        audio_path: str,
        bahasa: str = "id",
    ) -> dict[str, Any]:
        """Transcribe audio → teks.

        Args:
            audio_path: Path ke file audio (WAV/MP3/M4A/dll.).
            bahasa: Kode bahasa Whisper ('id' = Indonesia).

        Returns:
            Dict dengan kunci:
            - ``teks``     : str — hasil transkripsi
            - ``bahasa``   : str — bahasa yang terdeteksi
            - ``konfidence``: float — confidence rata-rata
        """
        if not os.path.isfile(audio_path):
            raise LayananAudioError(f"File audio tidak ada: {audio_path}")

        # Mapping bahasa daerah ke Whisper
        # Whisper hanya support beberapa bahasa, mayoritas pakai 'id' untuk Indonesia
        whisper_lang = {
            "id": "id", "jw": "jw", "su": "su",
            "min": "id", "bbc": "id",  # fallback ke Indonesia
        }.get(bahasa, "id")

        model = self._get_model()

        def _transcribe() -> dict[str, Any]:
            segments, info = model.transcribe(
                audio_path,
                language=whisper_lang,
                beam_size=5,
                vad_filter=True,  # Voice activity detection — skip silence
            )
            teks_segments = []
            confs = []
            for seg in segments:
                teks_segments.append(seg.text)
                if hasattr(seg, "avg_logprob"):
                    confs.append(seg.avg_logprob)
            return {
                "teks": " ".join(teks_segments).strip(),
                "bahasa": info.language,
                "konfidence": float(sum(confs) / len(confs)) if confs else 0.0,
                "durasi": info.duration,
            }

        # Jalankan di thread agar tidak block event loop
        hasil = await asyncio.to_thread(_transcribe)
        logger.info(
            "STT selesai: bahasa=%s panjang=%ds teks=%d karakter",
            hasil["bahasa"], hasil.get("durasi", 0), len(hasil["teks"]),
        )
        return hasil


# =========================================================================== #
# Singleton                                                                    #
# =========================================================================== #

tts_service = TTSService()
stt_service = STTService(model_size="small")


# =========================================================================== #
# Helper: bicara via Gemma 4 + langsung TTS                                    #
# =========================================================================== #

async def bicara_dari_pertanyaan(
    pertanyaan: str,
    bahasa: str = "id",
    student_level: str = "beginner",
) -> dict[str, Any]:
    """End-to-end: pertanyaan teks → AI generate jawaban → TTS ke MP3.

    Untuk anak SD yang nanya pakai suara, ini adalah satu-shot pipeline.
    """
    from services.llm_service import gemma_service, _get_bahasa_config  # noqa: PLC0415

    bahasa_cfg = _get_bahasa_config(bahasa)
    prompt = (
        f"Kamu adalah tutor coding untuk anak SD di Indonesia. "
        f"Jawab pertanyaan berikut dengan {bahasa_cfg['nama']} yang sangat sederhana, "
        f"cocok untuk anak usia 7-12 tahun. {bahasa_cfg['instruksi']}\n\n"
        f"Pertanyaan: {pertanyaan}\n\n"
        f"Jawab maksimal 3-4 kalimat pendek. Pakai analogi yang akrab untuk anak Indonesia."
    )

    raw = await gemma_service._call_ollama(prompt)
    audio_path = await tts_service.bicara(raw, bahasa=bahasa)

    return {
        "pertanyaan": pertanyaan,
        "jawaban_teks": raw,
        "jawaban_audio": audio_path,
        "bahasa": bahasa,
    }
