"""Jawaban kurasi untuk demo Hugging Face Space.

Aktif hanya saat CODEBUDDY_SPACE_DEMO=1. Tidak memanggil Ollama, Whisper,
edge-tts, atau model lain. Saat flag mati, modul ini tidak dipakai.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Optional

from utils.config import pengaturan

# Sampel yang sama dengan DEMO_TUTOR["code_with_error"] di frontend/demo_data.py.
KODE_RATA_RATA_TANPA_TITIK_DUA = """# Program hitung rata-rata
nilai = [85, 90, 75, 88]
total = 0

for n in nilai
    total = total + n

rata = total / len(nilai)
print("Rata-rata:", rata)
"""

KODE_RATA_RATA_DIPERBAIKI = """# Program hitung rata-rata
nilai = [85, 90, 75, 88]
total = 0

for n in nilai:
    total = total + n

rata = total / len(nilai)
print("Rata-rata:", rata)
"""

PERTANYAAN_SUARA = "Kenapa program rata-rata saya error di baris for n in nilai?"
JAWABAN_SUARA = (
    "Baris for n in nilai belum punya titik dua. "
    "Ubah menjadi for n in nilai: lalu baris total = total + n tetap menjorok ke dalam. "
    "Setelah itu Python bisa menghitung rata-ratanya."
)
CATATAN_TTS = (
    "Di demo Space ini file suara bukan bacaan sungguhan. "
    "Yang ditampilkan adalah transkrip Bahasa Indonesia. "
    "Suara edge-tts dan tutor Gemma 4 berjalan di komputer lokal lewat Ollama."
)

# Satu frame MPEG-1 Layer III senyap (64 kbps, 44.1 kHz, mono, 208 byte).
# Cukup agar pemutar Gradio menerima berkas; isi sesinya ada di teks.
_FRAME_MP3_SENYAP = bytes.fromhex(
    "fffb50c4"
    + "00" * 204
)

_path_mp3: Optional[str] = None


def aktif() -> bool:
    """True hanya jika CODEBUDDY_SPACE_DEMO=1 (atau true/yes/on)."""
    mentah = os.getenv("CODEBUDDY_SPACE_DEMO")
    if mentah is not None:
        return mentah.strip().lower() in {"1", "true", "yes", "on"}
    return bool(pengaturan.space_demo)


def header_ascii(teks: str, maks: int = 200) -> str:
    """Header HTTP hanya boleh ASCII printable."""
    return "".join(karakter for karakter in teks[:maks] if 0x20 <= ord(karakter) <= 0x7E)


def kode_ocr_demo() -> str:
    return KODE_RATA_RATA_TANPA_TITIK_DUA


def _baris_for_tanpa_titik_dua(code: str) -> Optional[tuple[int, str]]:
    for nomor, baris in enumerate(code.splitlines(), start=1):
        potong = baris.strip()
        if potong.startswith("for ") and not potong.endswith(":"):
            return nomor, potong
    return None


def _sampel_rata_rata(code: str) -> bool:
    return "for n in nilai" in code and "rata" in code.lower()


def umpan_balik_tutor(code: str, error: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Feedback tutor Bahasa Indonesia. Tidak memanggil model."""
    ketemu = _baris_for_tanpa_titik_dua(code)
    if ketemu is not None:
        nomor, potong = ketemu
        if _sampel_rata_rata(code):
            diperbaiki = KODE_RATA_RATA_DIPERBAIKI
            pemahaman = (
                "Kamu sedang menjumlahkan daftar nilai, lalu membaginya dengan "
                "banyaknya angka. Pola itu tepat untuk menghitung rata-rata."
            )
            saran = [
                "Setiap for, if, dan def diakhiri titik dua.",
                "Baris di dalam perulangan harus menjorok (indentasi) dengan spasi yang sama.",
                "Setelah titik dua ditambah, jalankan lagi dan cek apakah rata-ratanya tercetak.",
            ]
            dorongan = (
                "Kamu sudah dekat. Program rata-ratanya tinggal satu tanda baca lagi."
            )
        else:
            diperbaiki = f"{potong}:\n    # isi perulangan menjorok ke dalam"
            pemahaman = (
                "Perulangan for sudah hampir benar. Python hanya menolaknya "
                "karena baris pembukanya belum selesai."
            )
            saran = [
                "Setiap for, if, dan def diakhiri titik dua.",
                "Baris di dalam perulangan harus menjorok (indentasi) dengan spasi yang sama.",
                "Setelah titik dua ditambah, jalankan lagi dan cek apakah perulangannya jalan.",
            ]
            dorongan = (
                "Kamu sudah dekat. Perulangan for-nya tinggal satu tanda baca lagi."
            )
        return {
            "understanding": pemahaman,
            "errors": [
                {
                    "line": nomor,
                    "explanation": (
                        f"Baris `{potong}` belum diakhiri titik dua. "
                        "Di Python, awal perulangan for wajib memakai tanda `:` "
                        "sebelum isi bloknya."
                    ),
                    "fix": (
                        f"Ubah menjadi `{potong}:` lalu biarkan baris di bawahnya "
                        "menjorok ke dalam dengan spasi yang sama."
                    ),
                }
            ],
            "suggestions": saran,
            "corrected_code": diperbaiki,
            "encouragement": dorongan,
        }

    if error:
        jenis = str(error.get("type") or "Error")
        pesan = str(error.get("message") or error.get("message_id") or "").strip()
        baris = error.get("line")
        penjelasan = f"Python melaporkan {jenis}."
        if pesan:
            penjelasan = f"{penjelasan} Pesannya: {pesan}"
        return {
            "understanding": (
                "Kode ini sudah masuk ke pemeriksa syntax dan sandbox. "
                "Umpan balik di bawah mengikuti hasil itu, dalam Bahasa Indonesia."
            ),
            "errors": [
                {
                    "line": baris,
                    "explanation": penjelasan,
                    "fix": (
                        "Perbaiki satu hal yang disebut pesan itu, lalu jalankan ulang. "
                        "Jangan mengubah banyak baris sekaligus."
                    ),
                }
            ],
            "suggestions": [
                "Baca nama error dan nomor barisnya sebelum mengubah kode.",
                "Kalau ini SyntaxError, cek titik dua, tanda kutip, dan indentasi di baris itu.",
                "Kalau ini error saat jalan, cek apakah variabelnya sudah diberi nilai.",
            ],
            "corrected_code": "",
            "encouragement": (
                "Kamu sudah berani mencoba. Setiap pesan error menunjuk tepat "
                "satu hal yang bisa diperbaiki."
            ),
        }

    return {
        "understanding": (
            "Kode ini lolos pemeriksaan syntax dan berhasil dijalankan di sandbox. "
            "Tidak ada error yang perlu diperbaiki pada percobaan ini."
        ),
        "errors": [],
        "suggestions": [
            "Beri nama variabel yang menjelaskan isinya, misalnya nilai dan total.",
            "Tambahkan satu kalimat print supaya hasilnya mudah dibaca temanmu.",
        ],
        "corrected_code": code,
        "encouragement": "Kerja yang rapi. Kode kamu jalan dengan benar.",
    }


def petunjuk(code: str, error: str, hint_level: int) -> str:
    """Tiga tingkat petunjuk Bahasa Indonesia, tanpa memanggil model."""
    tingkat = max(1, min(3, hint_level))
    ketemu = _baris_for_tanpa_titik_dua(code)
    if ketemu is not None:
        nomor, potong = ketemu
        if _sampel_rata_rata(code):
            petunjuk_penuh = (
                f"Tambahkan titik dua sehingga menjadi `{potong}:`. "
                "Baris di dalamnya tetap menjorok ke dalam. "
                "Pada contoh rata-rata, itu satu-satunya yang kurang."
            )
        else:
            petunjuk_penuh = (
                f"Tambahkan titik dua sehingga menjadi `{potong}:`. "
                "Baris di dalamnya tetap menjorok ke dalam."
            )
        tingkat_teks = {
            1: (
                "Coba lihat baris perulangan for. Tanda apa yang harus ada "
                "di ujung baris itu sebelum isi perulangannya dimulai?"
            ),
            2: (
                f"Lokasinya di baris {nomor}: `{potong}`. "
                "Baris itu belum diakhiri titik dua, jadi Python belum tahu "
                "di mana blok perulangan dimulai."
            ),
            3: petunjuk_penuh,
        }
        return tingkat_teks[tingkat]

    pesan = (error or "").strip() or "tidak ada pesan error tambahan"
    tingkat_umum = {
        1: "Apa yang sebenarnya ingin dilakukan baris yang disebut pesan error itu?",
        2: (
            f"Baca pesan ini pelan-pelan: {pesan}. "
            "Nama atau nomor baris yang disebut di situ adalah tempat yang perlu kamu periksa."
        ),
        3: (
            f"Perbaiki satu hal yang disebut pesan error, lalu jalankan lagi. Pesannya: {pesan}"
        ),
    }
    return tingkat_umum[tingkat]


def latihan(topik: str, tingkat: str) -> dict[str, Any]:
    """Soal latihan siap pakai. Topik kalkulator memakai contoh yang sudah disiapkan."""
    nama = (topik or "perulangan").strip()
    tingkat_bersih = (tingkat or "beginner").strip() or "beginner"
    if "kalkulator" in nama.lower():
        return {
            "title": "Kalkulator sederhana",
            "instructions": (
                "Buat program Python untuk pemula yang menjumlahkan dua bilangan, "
                "a = 7 dan b = 5. Simpan jumlahnya di variabel hasil, lalu cetak "
                "teks Hasil: 12. Gunakan nama variabel yang jelas."
            ),
            "starter_code": (
                "a = 7\n"
                "b = 5\n"
                "# jumlahkan a dan b, lalu cetak Hasil: 12\n"
            ),
            "solution": (
                "a = 7\n"
                "b = 5\n"
                "hasil = a + b\n"
                "print(\"Hasil:\", hasil)\n"
            ),
            "test_cases": [
                {
                    "input": None,
                    "expected_output": "Hasil: 12",
                    "description": "7 ditambah 5 menghasilkan 12",
                },
                {
                    "input": None,
                    "expected_output": "Hasil: 12",
                    "description": "Teks Hasil harus ada sebelum angkanya",
                },
            ],
        }

    return {
        "title": f"Latihan {tingkat_bersih}: {nama}",
        "instructions": (
            f"Buat program Python tingkat {tingkat_bersih} tentang {nama}. "
            f"Simpan kata {nama!r} di variabel topik, lalu cetak kalimat "
            f"Hari ini kita belajar: diikuti kata itu. Jangan panggil input(); "
            "program harus langsung bisa dijalankan."
        ),
        "starter_code": (
            f"# Latihan tentang {nama}\n"
            "topik = \"\"  # isi dengan topik hari ini\n"
            "print(\"Hari ini kita belajar:\", topik)\n"
        ),
        "solution": (
            f"topik = {nama!r}\n"
            "print(\"Hari ini kita belajar:\", topik)\n"
        ),
        "test_cases": [
            {
                "input": None,
                "expected_output": f"Hari ini kita belajar: {nama}",
                "description": f"Program menyebut topik {nama}",
            },
            {
                "input": None,
                "expected_output": "Hari ini kita belajar:",
                "description": "Kalimat pembukanya tetap sama untuk topik apa pun",
            },
        ],
    }


def wawasan_guru(data: dict[str, Any]) -> dict[str, Any]:
    """Insight guru Bahasa Indonesia yang memakai angka dashboard yang masih hidup."""
    ringkas = data.get("ringkasan") or {}
    total = ringkas.get("total_siswa", 0)
    submission = ringkas.get("total_submission", 0)
    sukses = ringkas.get("success_rate_persen", 0)
    stuck = len(data.get("siswa_stuck") or [])
    if stuck:
        siswa = (
            f"Ada {stuck} siswa yang mencoba berkali-kali tetapi belum lulus. "
            "Dampingi mereka di contoh rata-rata nilai: tunjukkan beda "
            "`for n in nilai` dan `for n in nilai:`."
        )
    else:
        siswa = (
            "Belum ada siswa yang terdeteksi macet di data ini. Tetap ulangi "
            "titik dua pada perulangan for, karena itu kesalahan yang paling "
            "sering muncul saat siswa menyalin kode dari buku."
        )
    return {
        "kondisi_kelas": (
            f"Kelas ini punya {total} siswa dan {submission} pengumpulan kode, "
            f"dengan tingkat berhasil {sukses}%. Sebagian latihan masih berhenti "
            "di kesalahan sintaks yang kecil, terutama tanda baca pada perulangan."
        ),
        "topik_perhatian": (
            "Titik dua di akhir baris for, if, dan def. Contoh yang sering muncul: "
            "`for n in nilai` tanpa titik dua, sehingga Python menolak program rata-rata."
        ),
        "saran_pengajaran": [
            "Besok mulai dengan satu baris di papan: tulis `for n in nilai`, lalu minta siswa menambahkan titik dua sebelum mengisi blok.",
            "Minta siswa menjalankan kode di sandbox dulu, membaca pesan SyntaxError, lalu memperbaiki satu baris saja.",
            "Pasangkan siswa yang masih tertukar indentasi dengan siswa yang sudah lancar, supaya mereka saling cek titik dua dan spasi.",
        ],
        "siswa_butuh_bantuan": siswa,
    }


def hasil_stt(bahasa: str = "id") -> dict[str, Any]:
    return {
        "teks": PERTANYAAN_SUARA,
        "bahasa": bahasa or "id",
        "konfidence": 0.95,
        "durasi": 0,
    }


def path_mp3() -> str:
    """Tulis MP3 senyap sekali, lalu pakai ulang path-nya."""
    global _path_mp3
    if _path_mp3 and os.path.isfile(_path_mp3):
        return _path_mp3
    fd, path = tempfile.mkstemp(prefix="codebuddy-demo-", suffix=".mp3")
    try:
        os.write(fd, _FRAME_MP3_SENYAP)
    finally:
        os.close(fd)
    _path_mp3 = path
    return path
