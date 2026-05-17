"""Ekstraksi kode Python dari gambar tulisan tangan via PaddleOCR."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LayananOCRError(RuntimeError):
    """OCR tidak tersedia atau gagal memproses gambar."""


# --------------------------------------------------------------------------- #
# Lazy importers — backend tetap jalan tanpa Paddle / OpenCV terpasang        #
# --------------------------------------------------------------------------- #

def _import_cv2() -> Any:
    try:
        import cv2  # noqa: PLC0415
        return cv2
    except ImportError as exc:
        raise LayananOCRError(
            "opencv-python-headless belum terpasang. Jalankan: pip install opencv-python-headless"
        ) from exc


def _import_numpy() -> Any:
    try:
        import numpy as np  # noqa: PLC0415
        return np
    except ImportError as exc:
        raise LayananOCRError("numpy belum terpasang.") from exc


def _import_paddleocr() -> Any:
    try:
        from paddleocr import PaddleOCR  # noqa: PLC0415
        return PaddleOCR
    except ImportError as exc:
        raise LayananOCRError(
            "PaddleOCR belum terpasang. Jalankan: pip install -r requirements-ocr.txt"
        ) from exc


# --------------------------------------------------------------------------- #
# CodeOCRService                                                               #
# --------------------------------------------------------------------------- #

class CodeOCRService:
    """Layanan OCR yang dioptimalkan untuk kode Python tulisan tangan.

    Contoh penggunaan::

        svc = CodeOCRService()
        hasil = await asyncio.to_thread(svc.extract_code, "/path/ke/gambar.jpg")
        print(hasil["code"])
    """

    def __init__(self, lang: str = "en", debug: bool = False) -> None:
        """Inisialisasi service.

        Args:
            lang: Kode bahasa PaddleOCR (default 'en').
            debug: Jika True, simpan gambar hasil preprocess ke /tmp.
        """
        self._lang = lang
        self._debug = debug
        self._ocr: Any = None  # dibuat saat pertama kali dipakai (lazy)

    def _get_ocr(self) -> Any:
        if self._ocr is None:
            PaddleOCR = _import_paddleocr()
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                show_log=False,
            )
        return self._ocr

    # ----------------------------------------------------------------------- #
    # Public API                                                               #
    # ----------------------------------------------------------------------- #

    def extract_code(self, image_path: str) -> dict[str, Any]:
        """Ekstrak kode Python dari gambar dan kembalikan hasil terstruktur.

        Args:
            image_path: Path absolut ke file gambar.

        Returns:
            Dict dengan kunci:
            - ``code``       : string kode hasil rekonstruksi
            - ``confidence`` : float rata-rata kepercayaan (0–1)
            - ``raw_lines``  : list dict mentah dari PaddleOCR

        Raises:
            LayananOCRError: Jika gambar tidak bisa dibaca atau OCR gagal.

        Contoh::

            hasil = svc.extract_code("/tmp/kode.jpg")
            # {'code': 'print("hello")', 'confidence': 0.97, 'raw_lines': [...]}
        """
        if not os.path.isfile(image_path):
            raise LayananOCRError(f"File tidak ditemukan: {image_path}")

        preprocessed = self.preprocess_image(image_path)

        ocr = self._get_ocr()
        try:
            hasil_ocr = ocr.ocr(preprocessed, cls=True)
        except Exception as exc:
            raise LayananOCRError(f"OCR gagal: {exc}") from exc

        if not hasil_ocr or hasil_ocr[0] is None:
            logger.warning("OCR tidak mendeteksi teks pada: %s", image_path)
            return {"code": "", "confidence": 0.0, "raw_lines": []}

        raw_lines: list[dict[str, Any]] = []
        for entri in hasil_ocr[0]:
            if not entri or len(entri) < 2:
                continue
            kotak, (teks, skor) = entri[0], entri[1]
            raw_lines.append({
                "text": teks,
                "confidence": float(skor),
                "box": kotak,
            })

        code = self.reconstruct_code(raw_lines)
        confidence = self.calculate_confidence(raw_lines)

        logger.info(
            "OCR selesai: %d baris, confidence=%.3f, path=%s",
            len(raw_lines), confidence, image_path,
        )
        return {"code": code, "confidence": confidence, "raw_lines": raw_lines}

    def preprocess_image(self, image_path: str) -> Any:
        """Terapkan pipeline preprocess agar OCR lebih akurat pada kode.

        Pipeline:
        1. Grayscale
        2. Denoising (fastNlMeansDenoising)
        3. Peningkatan kontras (equalizeHist)
        4. Binarisasi adaptif (Otsu)

        Args:
            image_path: Path ke file gambar.

        Returns:
            numpy.ndarray gambar yang sudah diproses (grayscale biner).
        """
        cv2 = _import_cv2()

        gambar = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if gambar is None:
            raise LayananOCRError(
                f"Format gambar tidak dikenali atau file rusak: {image_path}"
            )

        # 1. Grayscale
        abu = cv2.cvtColor(gambar, cv2.COLOR_BGR2GRAY)

        # 2. Denoising
        bersih = cv2.fastNlMeansDenoising(abu, h=10, templateWindowSize=7, searchWindowSize=21)

        # 3. Kontras dengan equalizeHist
        kontras = cv2.equalizeHist(bersih)

        # 4. Binarisasi Otsu — teks hitam di latar putih
        _, biner = cv2.threshold(kontras, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Pastikan teks hitam = 0, latar putih = 255 (Paddle lebih suka ini)
        if biner.mean() < 127:
            biner = cv2.bitwise_not(biner)

        if self._debug:
            nama_debug = os.path.join(
                tempfile.gettempdir(),
                f"codebuddy_preproc_{os.path.basename(image_path)}",
            )
            cv2.imwrite(nama_debug, biner)
            logger.debug("Gambar preprocess disimpan ke: %s", nama_debug)

        return biner

    def reconstruct_code(self, ocr_lines: list[dict[str, Any]]) -> str:
        """Rekonstruksi kode Python dari baris-baris OCR dengan indentasi yang benar.

        Strategi indentasi:
        - Koordinat x kiri dari bounding box menentukan level indentasi.
        - x_min global = kolom 0 (tidak ada indentasi).
        - Setiap 20px ke kanan ≈ satu level indentasi (4 spasi).

        Args:
            ocr_lines: List dict dari PaddleOCR dengan kunci 'text' dan 'box'.

        Returns:
            String kode Python dengan indentasi yang telah direkonstruksi.
        """
        if not ocr_lines:
            return ""

        # Urutkan baris berdasarkan posisi vertikal (y tengah dari box)
        def _y_tengah(baris: dict[str, Any]) -> float:
            box = baris.get("box", [])
            if not box:
                return 0.0
            ys = [titik[1] for titik in box]
            return sum(ys) / len(ys)

        def _x_kiri(baris: dict[str, Any]) -> float:
            box = baris.get("box", [])
            if not box:
                return 0.0
            return min(titik[0] for titik in box)

        terurut = sorted(ocr_lines, key=_y_tengah)

        # Tentukan x minimum sebagai baseline kolom 0
        semua_x = [_x_kiri(b) for b in terurut]
        x_baseline = min(semua_x) if semua_x else 0.0
        lebar_per_indent = 20.0  # piksel per satu level indent (4 spasi)

        baris_kode: list[str] = []
        for baris in terurut:
            teks_asli = baris.get("text", "").rstrip()
            if not teks_asli:
                continue

            # Hitung level indentasi dari posisi x
            x = _x_kiri(baris)
            level = max(0, round((x - x_baseline) / lebar_per_indent))
            spasi = "    " * level  # 4 spasi per level

            teks_bersih = self._bersihkan_teks(teks_asli)
            teks_bersih = self.fix_common_ocr_errors(teks_bersih)

            baris_kode.append(spasi + teks_bersih)

        return "\n".join(baris_kode)

    def calculate_confidence(self, lines: list[dict[str, Any]]) -> float:
        """Hitung rata-rata confidence tertimbang berdasarkan panjang teks.

        Baris yang lebih panjang diberi bobot lebih tinggi karena lebih
        representatif dibanding baris pendek yang mungkin noise.

        Args:
            lines: List dict dengan kunci 'text' dan 'confidence'.

        Returns:
            Float antara 0.0 dan 1.0.
        """
        if not lines:
            return 0.0

        total_bobot = 0.0
        total_skor = 0.0
        for baris in lines:
            panjang = len(baris.get("text", ""))
            bobot = max(1, panjang)  # minimal bobot 1 agar tidak hilang
            total_skor += baris.get("confidence", 0.0) * bobot
            total_bobot += bobot

        return round(total_skor / total_bobot, 4) if total_bobot > 0 else 0.0

    # ----------------------------------------------------------------------- #
    # Helpers                                                                  #
    # ----------------------------------------------------------------------- #

    @staticmethod
    def fix_common_ocr_errors(text: str) -> str:
        """Perbaiki kesalahan OCR umum pada kode Python.

        Koreksi yang diterapkan:
        - Fungsi builtin yang sering salah dibaca (``prin(`` → ``print(``)
        - Pemisah blok (``;`` → ``:`` di akhir statement blok)
        - Karakter ambigu pada konteks keyword (``l`` vs ``1``, ``O`` vs ``0``)
        - Normalisasi indentasi tab → 4 spasi

        Args:
            text: Satu baris teks hasil OCR.

        Returns:
            Teks yang sudah dikoreksi.
        """
        # Tab → 4 spasi
        text = text.replace("\t", "    ")

        # Fungsi builtin yang sering salah baca
        text = re.sub(r"\bprin\(", "print(", text)
        text = re.sub(r"\bprintt?\(", "print(", text)
        text = re.sub(r"\binput\s*\(", "input(", text)
        text = re.sub(r"\brange\s*\(", "range(", text)
        text = re.sub(r"\blen\s*\(", "len(", text)

        # Keyword: 'def', 'class', 'return', 'import' yang sering terpotong
        text = re.sub(r"\bde f\b", "def", text)
        text = re.sub(r"\bclas s\b", "class", text)
        text = re.sub(r"\bretur n\b", "return", text)

        # Akhir baris blok: ; → : (for/if/def/else/elif/while/class/try/except/with)
        _blok_pattern = r"^(\s*(?:def|class|if|elif|else|for|while|try|except|finally|with)\b.+);$"
        text = re.sub(_blok_pattern, r"\1:", text)

        # Angka ambigu dalam konteks identifier (bukan dalam string/angka):
        # 'l' → '1' dan '1' → 'l' sangat konteks-spesifik, hindari over-koreksi.
        # Hanya koreksi yang sangat aman:
        text = re.sub(r"\bO\b(?=\s*[+\-*/=<>])", "0", text)  # O sendirian di ekspresi
        text = re.sub(r"(?<=[=(,\[{+\-*/ ])\bI\b", "1", text)  # I setelah operator

        # Tanda baca umum: smart/curly quotes → straight (U+2018/19/1C/1D → U+0027/0022)
        text = text.replace("‘", "'").replace("’", "'")  # ' ' → '
        text = text.replace("“", '"').replace("”", '"')  # " " → "

        return text

    @staticmethod
    def _bersihkan_teks(text: str) -> str:
        """Hapus karakter noise yang tidak mungkin ada dalam kode Python."""
        # Hapus karakter kontrol kecuali newline/tab
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Hapus karakter yang tidak mungkin di kode Python (beberapa simbol dekorasi)
        text = re.sub(r"[^\x20-\x7e ]", "", text)
        return text.strip()


# --------------------------------------------------------------------------- #
# Singleton                                                                    #
# --------------------------------------------------------------------------- #

code_ocr_service = CodeOCRService()


# --------------------------------------------------------------------------- #
# Backward-compatible function (dipakai api/ocr.py)                           #
# --------------------------------------------------------------------------- #

async def ekstrak_teks_dari_gambar(
    isi_gambar: bytes,
    bahasa: str = "en",
) -> dict[str, Any]:
    """Ekstrak kode Python dari bytes gambar.

    Strategi (prioritas):
    1. Gemma 4 Vision — primary, tidak butuh dependensi tambahan
    2. PaddleOCR — fallback jika Ollama tidak berjalan

    Args:
        isi_gambar: Konten file gambar dalam bytes.
        bahasa: Kode bahasa (untuk fallback PaddleOCR).

    Returns:
        Dict dengan kunci ``text``, ``lines``, ``engine``, ``confidence``.
    """
    if not isi_gambar:
        raise LayananOCRError("Berkas gambar kosong.")

    # Simpan alasan vision gagal — dipakai jika fallback Paddle juga tidak jalan
    alasan_vision: Optional[str] = None

    # ── Primary: Gemma 4 Vision ───────────────────────────────────────── #
    try:
        from services.llm_service import gemma_vision_service  # noqa: PLC0415
        hasil_vision = await gemma_vision_service.ekstrak_kode(isi_gambar)
        logger.info("Gemma 4 Vision berhasil: confidence=%.2f", hasil_vision["confidence"])
        return {
            "text": hasil_vision["code"],
            "lines": [],
            "engine": "gemma4-vision",
            "confidence": hasil_vision["confidence"],
        }
    except Exception as exc:  # noqa: BLE001
        alasan_vision = str(exc)[:400]
        logger.warning("Gemma 4 Vision gagal (%s) — fallback ke PaddleOCR", exc)

    # ── Fallback: PaddleOCR ──────────────────────────────────────────── #
    sufiks = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=sufiks, delete=False) as tmp:
        tmp.write(isi_gambar)
        tmp_path = tmp.name

    try:
        svc = CodeOCRService(lang=bahasa)
        try:
            hasil = await asyncio.to_thread(svc.extract_code, tmp_path)
        except LayananOCRError as exc_paddle:
            # Gabungkan konteks agar 503 tidak hanya menyalahkan Paddle
            vis = alasan_vision or "alasan tidak tercatat"
            raise LayananOCRError(
                f"Gemma Vision gagal ({vis}). "
                f"Paddle fallback tidak tersedia: {exc_paddle} "
                "— pastikan Ollama jalan + model vision (mis. gemma4:e4b), "
                "atau pasang Paddle: pip install -r requirements-ocr.txt "
                "(biasanya Python 3.10–3.12; lihat komentar di file tersebut)."
            ) from exc_paddle
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return {
        "text": hasil["code"],
        "lines": hasil["raw_lines"],
        "engine": "paddleocr-fallback",
        "confidence": hasil["confidence"],
    }
