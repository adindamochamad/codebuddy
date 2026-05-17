"""Seeder data demo untuk rekaman video Scene 7 — Teacher Dashboard.

Jalankan dari folder backend:
    python scripts/seed_demo_teacher.py

Script ini:
1. Menghapus semua data siswa/submission/progress yang ada
2. Mengisi ulang dengan 12 siswa bergaya Indonesia dari berbagai daerah
3. 75 submission dengan skor bervariasi
4. Progress records — ada yang stuck, ada yang sudah selesai
5. Error pattern yang jelas untuk AI Insight

Hasilnya di dashboard:
- 12 siswa terdaftar
- ~75 total submission
- Success rate ~62%
- 4 siswa stuck (butuh bantuan)
- Top error: SyntaxError (loop), IndentationError, NameError
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Pastikan bisa import dari root backend
sys.path.insert(0, str(Path(__file__).parent.parent))


async def hapus_semua_data(sesi) -> None:
    """Hapus semua data lama agar seeder bisa berjalan bersih."""
    from sqlalchemy import text  # noqa: PLC0415
    await sesi.execute(text("DELETE FROM progress"))
    await sesi.execute(text("DELETE FROM code_submissions"))
    await sesi.execute(text("DELETE FROM students"))
    await sesi.commit()
    print("  [✓] Data lama dihapus.")


async def buat_siswa(sesi) -> list[int]:
    """Buat 12 siswa dari berbagai daerah Indonesia."""
    from models.database import Student  # noqa: PLC0415

    # Representasi siswa nyata: nama dari Flores, Sumba, Bali, Jawa, Sumatra, Kalimantan
    daftar_data_siswa = [
        # Beginner — siswa kelas 4–5 SD dari daerah terpencil
        {"name": "Andi Pratama",       "age": 10, "level": "beginner"},   # Flores, NTT
        {"name": "Siti Wahyuni",       "age": 11, "level": "beginner"},   # Sumba, NTT
        {"name": "Budi Santoso",       "age": 9,  "level": "beginner"},   # Jawa Tengah
        {"name": "Dewi Lestari",       "age": 10, "level": "beginner"},   # Jawa Barat
        {"name": "Rizky Maulana",      "age": 10, "level": "beginner"},   # Kalimantan Barat
        {"name": "Nur Aini",           "age": 11, "level": "beginner"},   # Sumatra Selatan
        {"name": "Wahyu Trianto",      "age": 9,  "level": "beginner"},   # DIY Yogyakarta
        # Intermediate — siswa kelas 6 SD atau SMP awal
        {"name": "Ayu Permatasari",    "age": 12, "level": "intermediate"},  # Bali
        {"name": "Fajar Nugroho",      "age": 12, "level": "intermediate"},  # Jawa Timur
        {"name": "Indira Sari",        "age": 13, "level": "intermediate"},  # Sulawesi Selatan
        # Advanced — guru / siswa berbakat
        {"name": "Pak Wayan Darma",    "age": 38, "level": "advanced"},   # Bali, guru SD
        {"name": "Rafi Ramadhan",      "age": 14, "level": "advanced"},   # Bandung, juara olimpiade
    ]

    daftar_siswa_orm = []
    for data in daftar_data_siswa:
        siswa_baru = Student(**data)
        sesi.add(siswa_baru)
        daftar_siswa_orm.append(siswa_baru)

    await sesi.commit()
    # Refresh untuk dapatkan ID yang di-assign DB
    from sqlalchemy import select  # noqa: PLC0415
    semua_siswa = (await sesi.scalars(select(Student).order_by(Student.id))).all()
    daftar_id = [s.id for s in semua_siswa]
    print(f"  [✓] {len(daftar_id)} siswa dibuat.")
    return daftar_id


async def buat_submissions(sesi, daftar_id: list[int]) -> None:
    """Buat 75 submission dengan pola realistis untuk tiap siswa."""
    from models.database import CodeSubmission  # noqa: PLC0415

    sekarang = datetime.now(timezone.utc)

    def waktu_lalu(hari: int, jam: int = 0) -> datetime:
        return sekarang - timedelta(days=hari, hours=jam)

    # Kode contoh per topik
    kode_hello_benar     = 'print("Halo Dunia!")'
    kode_hello_salah     = 'print "Halo Dunia!"'     # Python 2 style — SyntaxError
    kode_loop_benar      = 'for i in range(5):\n    print("*" * i)'
    kode_loop_salah1     = 'for i in range(5)\n    print("*" * i)'  # Titik dua hilang
    kode_loop_salah2     = 'for i in range(5):\nprint("*" * i)'     # IndentationError
    kode_variabel_benar  = 'nama = "Andi"\numur = 10\nprint(nama + " berumur " + str(umur))'
    kode_variabel_salah  = 'nama = "Andi"\nprint(nama + " berumur " + umur)'  # TypeError
    kode_if_benar        = 'n = 7\nif n % 2 == 0:\n    print("genap")\nelse:\n    print("ganjil")'
    kode_if_salah        = 'n = 7\nif n % 2 = 0:\n    print("genap")'  # SyntaxError (= bukan ==)
    kode_fungsi_benar    = 'def sapa(nama):\n    return "Halo, " + nama\nprint(sapa("Budi"))'
    kode_fungsi_salah    = 'def sapa(nama)\n    return "Halo, " + nama\nprint(sapa("Budi"))'
    kode_rekursi_benar   = 'def faktorial(n):\n    if n == 0:\n        return 1\n    return n * faktorial(n - 1)\nprint(faktorial(6))'

    # Template error — tipe error yang sering muncul di kelas
    err_syntax_titik_dua  = [{"type": "SyntaxError",      "message": "expected ':'",          "line": 1}]
    err_syntax_tanda_sama = [{"type": "SyntaxError",      "message": "invalid syntax, '='",   "line": 2}]
    err_syntax_print      = [{"type": "SyntaxError",      "message": "Missing parentheses",   "line": 1}]
    err_indent            = [{"type": "IndentationError", "message": "expected an indented block", "line": 2}]
    err_nameerror         = [{"type": "NameError",        "message": "name 'umur' is not defined", "line": 3}]
    err_typeerror         = [{"type": "TypeError",        "message": "can only concatenate str (not 'int')", "line": 2}]
    err_zerodiv           = [{"type": "ZeroDivisionError","message": "division by zero",       "line": 1}]

    # id[0]  = Andi (beginner, Flores) — belajar bertahap, akhirnya berhasil di loop
    # id[1]  = Siti (beginner, Sumba) — stuck di loop sejak hari 1, butuh bantuan khusus
    # id[2]  = Budi (beginner, Jawa Tengah) — lumayan, error TypeError berulang
    # id[3]  = Dewi (beginner, Jawa Barat) — mulai bagus lalu stuck di fungsi
    # id[4]  = Rizky (beginner, Kalimantan) — stuck IndentationError 6 kali
    # id[5]  = Nur Aini (beginner, Sumatra) — konsisten bagus untuk beginner
    # id[6]  = Wahyu (beginner, Yogya) — baru mulai, sedikit submission
    # id[7]  = Ayu (intermediate, Bali) — bagus, rata-rata tinggi
    # id[8]  = Fajar (intermediate, Jatim) — lumayan stabil
    # id[9]  = Indira (intermediate, Sulsel) — beberapa error tapi recovery cepat
    # id[10] = Pak Wayan (advanced, guru) — semua benar
    # id[11] = Rafi (advanced, Bandung) — eksplorasi rekursi

    semua_sub = [
        # ── Andi (id[0]) — beginner, belajar step by step ──────────────────
        {"student_id": daftar_id[0], "code": kode_hello_salah,    "errors": err_syntax_print,      "score": 10.0,  "timestamp": waktu_lalu(14)},
        {"student_id": daftar_id[0], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(13)},
        {"student_id": daftar_id[0], "code": kode_variabel_salah, "errors": err_typeerror,          "score": 30.0,  "timestamp": waktu_lalu(10)},
        {"student_id": daftar_id[0], "code": kode_variabel_salah, "errors": err_typeerror,          "score": 30.0,  "timestamp": waktu_lalu(9)},
        {"student_id": daftar_id[0], "code": kode_variabel_benar, "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[0], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[0], "code": kode_loop_salah2,    "errors": err_indent,            "score": 20.0,  "timestamp": waktu_lalu(4)},
        {"student_id": daftar_id[0], "code": kode_loop_benar,     "errors": None,                  "score": 85.0,  "timestamp": waktu_lalu(3)},
        {"student_id": daftar_id[0], "code": kode_if_salah,       "errors": err_syntax_tanda_sama, "score": 20.0,  "timestamp": waktu_lalu(1)},

        # ── Siti (id[1]) — beginner, stuck di loop ─────────────────────────
        {"student_id": daftar_id[1], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(14)},
        {"student_id": daftar_id[1], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(10)},
        {"student_id": daftar_id[1], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(9)},
        {"student_id": daftar_id[1], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[1], "code": kode_loop_salah2,    "errors": err_indent,            "score": 20.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[1], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(6)},
        {"student_id": daftar_id[1], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[1], "code": kode_loop_salah2,    "errors": err_indent,            "score": 20.0,  "timestamp": waktu_lalu(2)},

        # ── Budi (id[2]) — beginner, TypeError berulang ──────────────────
        {"student_id": daftar_id[2], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(12)},
        {"student_id": daftar_id[2], "code": kode_variabel_salah, "errors": err_typeerror,          "score": 25.0,  "timestamp": waktu_lalu(9)},
        {"student_id": daftar_id[2], "code": kode_variabel_salah, "errors": err_typeerror,          "score": 25.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[2], "code": kode_variabel_salah, "errors": err_typeerror,          "score": 25.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[2], "code": kode_variabel_benar, "errors": None,                  "score": 80.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[2], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(2)},
        {"student_id": daftar_id[2], "code": kode_loop_benar,     "errors": None,                  "score": 75.0,  "timestamp": waktu_lalu(1)},

        # ── Dewi (id[3]) — beginner, mulai bagus lalu stuck di fungsi ──────
        {"student_id": daftar_id[3], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(13)},
        {"student_id": daftar_id[3], "code": kode_variabel_benar, "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(10)},
        {"student_id": daftar_id[3], "code": kode_loop_benar,     "errors": None,                  "score": 80.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[3], "code": kode_fungsi_salah,   "errors": err_syntax_titik_dua,  "score": 15.0,  "timestamp": waktu_lalu(4)},
        {"student_id": daftar_id[3], "code": kode_fungsi_salah,   "errors": err_syntax_titik_dua,  "score": 15.0,  "timestamp": waktu_lalu(3)},
        {"student_id": daftar_id[3], "code": kode_fungsi_salah,   "errors": err_syntax_titik_dua,  "score": 15.0,  "timestamp": waktu_lalu(2)},

        # ── Rizky (id[4]) — beginner, stuck IndentationError ──────────────
        {"student_id": daftar_id[4], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(11)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(6)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(4)},
        {"student_id": daftar_id[4], "code": kode_loop_salah2,    "errors": err_indent,            "score": 15.0,  "timestamp": waktu_lalu(3)},

        # ── Nur Aini (id[5]) — beginner konsisten bagus ─────────────────
        {"student_id": daftar_id[5], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(10)},
        {"student_id": daftar_id[5], "code": kode_variabel_benar, "errors": None,                  "score": 95.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[5], "code": kode_loop_salah1,    "errors": err_syntax_titik_dua,  "score": 10.0,  "timestamp": waktu_lalu(4)},
        {"student_id": daftar_id[5], "code": kode_loop_benar,     "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(3)},
        {"student_id": daftar_id[5], "code": kode_if_benar,       "errors": None,                  "score": 85.0,  "timestamp": waktu_lalu(1)},

        # ── Wahyu (id[6]) — baru mulai ─────────────────────────────────
        {"student_id": daftar_id[6], "code": kode_hello_salah,    "errors": err_syntax_print,      "score": 10.0,  "timestamp": waktu_lalu(3)},
        {"student_id": daftar_id[6], "code": kode_hello_benar,    "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(2)},

        # ── Ayu (id[7]) — intermediate, stabil tinggi ─────────────────────
        {"student_id": daftar_id[7], "code": kode_fungsi_benar,   "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(12)},
        {"student_id": daftar_id[7], "code": kode_if_benar,       "errors": None,                  "score": 95.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[7], "code": kode_loop_benar,     "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[7], "code": kode_variabel_benar, "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(2)},

        # ── Fajar (id[8]) — intermediate, stabil ─────────────────────────
        {"student_id": daftar_id[8], "code": kode_fungsi_benar,   "errors": None,                  "score": 85.0,  "timestamp": waktu_lalu(11)},
        {"student_id": daftar_id[8], "code": kode_if_salah,       "errors": err_syntax_tanda_sama, "score": 20.0,  "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[8], "code": kode_if_benar,       "errors": None,                  "score": 80.0,  "timestamp": waktu_lalu(6)},
        {"student_id": daftar_id[8], "code": kode_loop_benar,     "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(3)},

        # ── Indira (id[9]) — intermediate, recovery cepat ────────────────
        {"student_id": daftar_id[9], "code": kode_fungsi_salah,   "errors": err_syntax_titik_dua,  "score": 20.0,  "timestamp": waktu_lalu(9)},
        {"student_id": daftar_id[9], "code": kode_fungsi_benar,   "errors": None,                  "score": 95.0,  "timestamp": waktu_lalu(8)},
        {"student_id": daftar_id[9], "code": kode_if_benar,       "errors": None,                  "score": 90.0,  "timestamp": waktu_lalu(5)},
        {"student_id": daftar_id[9], "code": 'x = 10\nprint(x / 0)', "errors": err_zerodiv,        "score": 30.0,  "timestamp": waktu_lalu(2)},
        {"student_id": daftar_id[9], "code": 'x = 10\nif x != 0:\n    print(x / 2)', "errors": None, "score": 85.0, "timestamp": waktu_lalu(1)},

        # ── Pak Wayan (id[10]) — advanced guru, semua benar ───────────────
        {"student_id": daftar_id[10], "code": kode_rekursi_benar, "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(7)},
        {"student_id": daftar_id[10], "code": kode_fungsi_benar,  "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(4)},
        {"student_id": daftar_id[10], "code": 'class Siswa:\n    def __init__(self, nama):\n        self.nama = nama\n    def sapa(self):\n        return f"Halo, {self.nama}"\ns = Siswa("Andi")\nprint(s.sapa())',
         "errors": None, "score": 100.0, "timestamp": waktu_lalu(1)},

        # ── Rafi (id[11]) — advanced, eksplorasi rekursi ─────────────────
        {"student_id": daftar_id[11], "code": kode_rekursi_benar, "errors": None,                  "score": 100.0, "timestamp": waktu_lalu(6)},
        {"student_id": daftar_id[11], "code": 'def fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)\nfor i in range(10):\n    print(fib(i))',
         "errors": None, "score": 100.0, "timestamp": waktu_lalu(3)},
        {"student_id": daftar_id[11], "code": 'def pangkat(basis, eks):\n    if eks == 0:\n        return 1\n    return basis * pangkat(basis, eks - 1)\nprint(pangkat(2, 8))',
         "errors": None, "score": 100.0, "timestamp": waktu_lalu(1)},
    ]

    for data_sub in semua_sub:
        sub = CodeSubmission(
            student_id=data_sub["student_id"],
            code=data_sub["code"],
            errors=data_sub.get("errors"),
            score=data_sub["score"],
            timestamp=data_sub["timestamp"],
        )
        sesi.add(sub)

    await sesi.commit()
    print(f"  [✓] {len(semua_sub)} submissions dibuat.")


async def buat_progress(sesi, daftar_id: list[int]) -> None:
    """Buat progress record per siswa per exercise."""
    from models.database import Progress  # noqa: PLC0415

    sekarang = datetime.now(timezone.utc)

    def waktu_lalu(hari: int) -> datetime:
        return sekarang - timedelta(days=hari)

    semua_progress = [
        # Andi (id[0]) — hampir semua selesai, if/else belum
        {"student_id": daftar_id[0], "exercise_id": "hello_print",    "completed": True,  "attempts": 2,  "avg_score": 55.0,  "last_attempt": waktu_lalu(13)},
        {"student_id": daftar_id[0], "exercise_id": "variabel_nama",  "completed": True,  "attempts": 3,  "avg_score": 50.0,  "last_attempt": waktu_lalu(8)},
        {"student_id": daftar_id[0], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 3,  "avg_score": 38.3,  "last_attempt": waktu_lalu(3)},
        {"student_id": daftar_id[0], "exercise_id": "kondisi_if",     "completed": False, "attempts": 1,  "avg_score": 20.0,  "last_attempt": waktu_lalu(1)},

        # Siti (id[1]) — STUCK di loop (6 attempts, belum selesai!)
        {"student_id": daftar_id[1], "exercise_id": "hello_print",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(14)},
        {"student_id": daftar_id[1], "exercise_id": "loop_bintang",   "completed": False, "attempts": 7,  "avg_score": 12.9,  "last_attempt": waktu_lalu(2)},

        # Budi (id[2]) — TypeError berulang di variabel, loop sudah selesai
        {"student_id": daftar_id[2], "exercise_id": "hello_print",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(12)},
        {"student_id": daftar_id[2], "exercise_id": "variabel_nama",  "completed": True,  "attempts": 4,  "avg_score": 38.75, "last_attempt": waktu_lalu(5)},
        {"student_id": daftar_id[2], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 2,  "avg_score": 42.5,  "last_attempt": waktu_lalu(1)},

        # Dewi (id[3]) — STUCK di fungsi (3 attempts, belum selesai)
        {"student_id": daftar_id[3], "exercise_id": "hello_print",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(13)},
        {"student_id": daftar_id[3], "exercise_id": "variabel_nama",  "completed": True,  "attempts": 1,  "avg_score": 90.0,  "last_attempt": waktu_lalu(10)},
        {"student_id": daftar_id[3], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 1,  "avg_score": 80.0,  "last_attempt": waktu_lalu(7)},
        {"student_id": daftar_id[3], "exercise_id": "fungsi_sapa",    "completed": False, "attempts": 3,  "avg_score": 15.0,  "last_attempt": waktu_lalu(2)},

        # Rizky (id[4]) — STUCK di loop karena IndentationError (6 attempts!)
        {"student_id": daftar_id[4], "exercise_id": "hello_print",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(11)},
        {"student_id": daftar_id[4], "exercise_id": "loop_bintang",   "completed": False, "attempts": 6,  "avg_score": 15.0,  "last_attempt": waktu_lalu(3)},

        # Nur Aini (id[5]) — konsisten, nyaris semua selesai
        {"student_id": daftar_id[5], "exercise_id": "hello_print",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(10)},
        {"student_id": daftar_id[5], "exercise_id": "variabel_nama",  "completed": True,  "attempts": 1,  "avg_score": 95.0,  "last_attempt": waktu_lalu(7)},
        {"student_id": daftar_id[5], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 2,  "avg_score": 50.0,  "last_attempt": waktu_lalu(3)},
        {"student_id": daftar_id[5], "exercise_id": "kondisi_if",     "completed": True,  "attempts": 1,  "avg_score": 85.0,  "last_attempt": waktu_lalu(1)},

        # Wahyu (id[6]) — baru mulai
        {"student_id": daftar_id[6], "exercise_id": "hello_print",    "completed": True,  "attempts": 2,  "avg_score": 55.0,  "last_attempt": waktu_lalu(2)},

        # Ayu (id[7]) — intermediate, progress bagus
        {"student_id": daftar_id[7], "exercise_id": "fungsi_sapa",    "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(12)},
        {"student_id": daftar_id[7], "exercise_id": "kondisi_if",     "completed": True,  "attempts": 1,  "avg_score": 95.0,  "last_attempt": waktu_lalu(8)},
        {"student_id": daftar_id[7], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 1,  "avg_score": 90.0,  "last_attempt": waktu_lalu(5)},
        {"student_id": daftar_id[7], "exercise_id": "variabel_nama",  "completed": True,  "attempts": 1,  "avg_score": 100.0, "last_attempt": waktu_lalu(2)},

        # Fajar (id[8]) — intermediate stabil
        {"student_id": daftar_id[8], "exercise_id": "fungsi_sapa",    "completed": True,  "attempts": 1,  "avg_score": 85.0,  "last_attempt": waktu_lalu(11)},
        {"student_id": daftar_id[8], "exercise_id": "kondisi_if",     "completed": True,  "attempts": 2,  "avg_score": 50.0,  "last_attempt": waktu_lalu(6)},
        {"student_id": daftar_id[8], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 1,  "avg_score": 90.0,  "last_attempt": waktu_lalu(3)},

        # Indira (id[9]) — intermediate, recovery cepat
        {"student_id": daftar_id[9], "exercise_id": "fungsi_sapa",    "completed": True,  "attempts": 2,  "avg_score": 57.5,  "last_attempt": waktu_lalu(8)},
        {"student_id": daftar_id[9], "exercise_id": "kondisi_if",     "completed": True,  "attempts": 1,  "avg_score": 90.0,  "last_attempt": waktu_lalu(5)},
        {"student_id": daftar_id[9], "exercise_id": "loop_bintang",   "completed": True,  "attempts": 2,  "avg_score": 57.5,  "last_attempt": waktu_lalu(1)},

        # Pak Wayan (id[10]) — advanced, semua selesai
        {"student_id": daftar_id[10], "exercise_id": "rekursi_faktorial", "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(7)},
        {"student_id": daftar_id[10], "exercise_id": "fungsi_sapa",       "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(4)},
        {"student_id": daftar_id[10], "exercise_id": "oop_dasar",         "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(1)},

        # Rafi (id[11]) — advanced, eksplorasi mandiri
        {"student_id": daftar_id[11], "exercise_id": "rekursi_faktorial", "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(6)},
        {"student_id": daftar_id[11], "exercise_id": "rekursi_fibonacci", "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(3)},
        {"student_id": daftar_id[11], "exercise_id": "rekursi_pangkat",   "completed": True, "attempts": 1, "avg_score": 100.0, "last_attempt": waktu_lalu(1)},
    ]

    for data_prog in semua_progress:
        prog = Progress(
            student_id=data_prog["student_id"],
            exercise_id=data_prog["exercise_id"],
            completed=data_prog["completed"],
            attempts=data_prog["attempts"],
            avg_score=data_prog["avg_score"],
            last_attempt=data_prog["last_attempt"],
        )
        sesi.add(prog)

    await sesi.commit()
    print(f"  [✓] {len(semua_progress)} progress records dibuat.")


async def jalankan_seeder() -> None:
    """Entrypoint utama: hapus data lama → isi ulang → tampilkan ringkasan."""
    # Inisialisasi DB dan tabel terlebih dahulu
    from utils.database import init_db, pembuat_sesi_async  # noqa: PLC0415

    print("\nCodeBuddy — Seeder Data Demo Teacher Dashboard")
    print("=" * 50)

    print("\n[1] Inisialisasi tabel database...")
    await init_db()

    print("\n[2] Menghapus data lama...")
    async with pembuat_sesi_async() as sesi:
        await hapus_semua_data(sesi)

    print("\n[3] Membuat siswa demo...")
    async with pembuat_sesi_async() as sesi:
        daftar_id = await buat_siswa(sesi)

    print("\n[4] Membuat submissions...")
    async with pembuat_sesi_async() as sesi:
        await buat_submissions(sesi, daftar_id)

    print("\n[5] Membuat progress records...")
    async with pembuat_sesi_async() as sesi:
        await buat_progress(sesi, daftar_id)

    print("\n" + "=" * 50)
    print("SELESAI! Ringkasan data demo:")
    print(f"  Jumlah siswa       : {len(daftar_id)}")
    print("  Total submissions  : 75")
    print("  Siswa stuck (≥5x)  : 3 (Siti loop, Rizky indent, Siti loop)")
    print("  Error terbanyak    : SyntaxError (titik dua loop), IndentationError")
    print("  Success rate est.  : ~62%")
    print("\nJalankan backend dan buka tab Teacher → Refresh Dashboard")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(jalankan_seeder())
