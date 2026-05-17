#!/usr/bin/env python3
"""Verifikasi otomatis checklist Task 1.1 (API + Gradio ringan).

Jalankan dari folder backend dengan venv aktif:

  cd backend
  python scripts/verifikasi_task_1_1.py

Opsi:

  --audio-ask PATH   File WAV/MP3 berisi pertanyaan bahasa Indonesia (untuk /api/audio/ask).
                     Tanpa ini, tes voice full loop dilewati (bukan gagal).

Contoh buat audio uji di macOS (Terminal):

  say -o /tmp/pertanyaan.aiff "Mengapa loop saya tidak berhenti"
  afconvert -f WAVE -c 1 -d LEI16 /tmp/pertanyaan.aiff /tmp/pertanyaan.wav
  python scripts/verifikasi_task_1_1.py --audio-ask /tmp/pertanyaan.wav

Butuh: backend (uvicorn) jalan, untuk OCR+tutor+insight: Ollama. TTS: internet (edge-tts).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

import httpx

# Gambar PNG 1x1 valid — cukup untuk memicu pipeline OCR (Vision / fallback).
PNG_MINI_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


async def panggil(
    klien: httpx.AsyncClient,
    nama_tes: str,
    metode: str,
    url: str,
    kode_sukses: int | set[int] = 200,
    **kwargs: object,
) -> tuple[str, int, str]:
    """Satu request HTTP; kembalikan (nama, status_http, ringkasan)."""
    try:
        respons = await klien.request(metode, url, **kwargs)
    except Exception as exc:  # noqa: BLE001 — ingin tangkap semua error jaringan
        return nama_tes, 0, f"ERROR: {exc}"

    oke = kode_sukses if isinstance(kode_sukses, set) else {kode_sukses}
    if respons.status_code not in oke:
        badan = (respons.text or "")[:500]
        return nama_tes, respons.status_code, badan

    if "audio_tts" in nama_tes or ("audio_ask" in nama_tes and nama_tes.endswith("_file")):
        isi = respons.content or b""
        return nama_tes, respons.status_code, f"OK (biner {len(isi)} byte)"

    teks = respons.text or ""
    if len(teks) > 450:
        teks = teks[:450] + "..."
    return nama_tes, respons.status_code, teks


async def utama(args: argparse.Namespace) -> int:
    basis_api = args.url.rstrip("/")
    basis_gradio = args.gradio.rstrip("/")
    hasil_baris: list[tuple[str, str, int, str]] = []

    async with httpx.AsyncClient(timeout=args.timeout) as klien:
        # --- health (juga cek apakah API benar-benar hidup) ---
        nama, kode, ringkas = await panggil(klien, "health", "GET", f"{basis_api}/health")
        if kode == 0:
            print(
                f"\nTidak dapat menyambung ke {basis_api}\n"
                "Pastikan backend berjalan, contoh:\n"
                "  cd backend && uvicorn main:app --reload --port 8000\n"
            )
            return 1
        hasil_baris.append(("health", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- siswa untuk tutor (lewat panggil agar ConnectError tidak crash) ---
        nama, kode, ringkas = await panggil(
            klien,
            "buat_siswa",
            "POST",
            f"{basis_api}/api/students/",
            json={"name": "Verifikasi 1.1", "age": 10, "level": "beginner"},
            kode_sukses=201,
        )
        if kode == 201:
            try:
                id_siswa = int(json.loads(ringkas)["id"])
            except (json.JSONDecodeError, KeyError, TypeError):
                id_siswa = 1
                hasil_baris.append(("buat_siswa", "FAIL", kode, "Respons JSON siswa tidak valid"))
            else:
                hasil_baris.append(("buat_siswa", "PASS", 201, f"id={id_siswa}"))
        else:
            hasil_baris.append(("buat_siswa", "FAIL", kode, ringkas[:300]))
            id_siswa = 1

        # --- code ---
        for nama_tes, badan in [
            ("code_execute", {"kode": "print(2+2)"}),
            ("code_validate_ok", {"kode": "x = 1\nprint(x)"}),
            ("code_validate_bad", {"kode": "if True\n    pass"}),
        ]:
            nama, kode, ringkas = await panggil(
                klien, nama_tes, "POST", f"{basis_api}/api/code/execute" if "execute" in nama_tes else f"{basis_api}/api/code/validate",
                json=badan,
            )
            hasil_baris.append((nama_tes, "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- hint 1–3 ---
        for lv in (1, 2, 3):
            nama_tes = f"agent_hint_{lv}"
            nama, kode, ringkas = await panggil(
                klien,
                nama_tes,
                "POST",
                f"{basis_api}/api/agent/hint",
                json={
                    "code": "for i in range(3):\nprint(i)",
                    "error": "IndentationError: expected an indented block",
                    "hint_level": lv,
                    "student_level": "beginner",
                },
                timeout=args.timeout_llm,
            )
            hasil_baris.append((nama_tes, "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- tutor ---
        nama, kode, ringkas = await panggil(
            klien,
            "agent_tutor",
            "POST",
            f"{basis_api}/api/agent/tutor",
            json={
                "code": "print(1/0)",
                "student_id": id_siswa,
                "exercise_id": None,
                "student_level": "beginner",
                "bahasa": "id",
            },
            timeout=args.timeout_llm,
        )
        hasil_baris.append(("agent_tutor", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- OCR ---
        png_bytes = base64.b64decode(PNG_MINI_B64)
        nama, kode, ringkas = await panggil(
            klien,
            "ocr_extract",
            "POST",
            f"{basis_api}/api/ocr/extract",
            files={"berkas": ("mini.png", png_bytes, "image/png")},
            timeout=args.timeout_llm,
        )
        hasil_baris.append(("ocr_extract", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- teacher ---
        nama, kode, ringkas = await panggil(
            klien, "teacher_dashboard", "GET", f"{basis_api}/api/teacher/dashboard"
        )
        hasil_baris.append(("teacher_dashboard", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        nama, kode, ringkas = await panggil(
            klien,
            "teacher_insights",
            "GET",
            f"{basis_api}/api/teacher/insights",
            timeout=args.timeout_llm,
        )
        hasil_baris.append(("teacher_insights", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- audio TTS ---
        nama, kode, ringkas = await panggil(
            klien,
            "audio_tts",
            "POST",
            f"{basis_api}/api/audio/tts",
            json={"teks": "Halo, ini uji TTS.", "bahasa": "id", "gender": "female"},
            timeout=args.timeout_llm,
        )
        hasil_baris.append(("audio_tts", "PASS" if kode == 200 else "FAIL", kode, ringkas))

        # --- audio STT: opsional; jika --audio-ask ada, pakai file yang sama ---
        path_stt = args.audio_stt or args.audio_ask
        if path_stt and Path(path_stt).is_file():
            isi_audio = Path(path_stt).read_bytes()
            sufiks = Path(path_stt).suffix or ".wav"
            ct = "audio/wav" if sufiks.lower() == ".wav" else "audio/mpeg"
            nama, kode, ringkas = await panggil(
                klien,
                "audio_stt_file",
                "POST",
                f"{basis_api}/api/audio/stt",
                files={"berkas": (Path(path_stt).name, isi_audio, ct)},
                params={"bahasa": "id"},
                timeout=args.timeout_llm,
            )
            hasil_baris.append(("audio_stt_file", "PASS" if kode == 200 else "FAIL", kode, ringkas))
        else:
            hasil_baris.append(
                ("audio_stt_file", "SKIP", 0, "beri --audio-stt atau --audio-ask (WAV berisi bicara)"),
            )

        # --- audio ask (wajib ada ucapan di audio) ---
        if args.audio_ask and Path(args.audio_ask).is_file():
            isi_rekam = Path(args.audio_ask).read_bytes()
            nama_file = Path(args.audio_ask).name
            sufiks = Path(args.audio_ask).suffix.lower()
            ct = "audio/wav" if sufiks == ".wav" else "audio/mpeg"
            nama, kode, ringkas = await panggil(
                klien,
                "audio_ask_file",
                "POST",
                f"{basis_api}/api/audio/ask",
                files={"berkas": (nama_file, isi_rekam, ct)},
                params={"bahasa": "id", "student_level": "beginner"},
                timeout=args.timeout_llm,
            )
            hasil_baris.append(("audio_ask_file", "PASS" if kode == 200 else "FAIL", kode, ringkas))
        else:
            hasil_baris.append(
                (
                    "audio_ask_file",
                    "SKIP",
                    0,
                    "tambah --audio-ask berkas.wav berisi pertanyaan (lihat docstring skrip)",
                ),
            )

        # --- Gradio: satu halaman, cek 6 label tab ---
        label_tab = [
            "Photo Scan",
            "AI Tutor",
            "Voice Mode",
            "Exercises",
            "Students",
            "Teacher",
        ]
        try:
            r = await klien.get(f"{basis_gradio}/", timeout=20.0)
            teks_html = r.text or ""
            for label in label_tab:
                oke = r.status_code == 200 and label in teks_html
                hasil_baris.append(
                    (f"gradio_tab_{label}", "PASS" if oke else "FAIL", r.status_code, label if oke else teks_html[:80]),
                )
        except Exception as exc:  # noqa: BLE001
            for label in label_tab:
                hasil_baris.append((f"gradio_tab_{label}", "ERROR", 0, str(exc)[:120]))

    # --- cetak ---
    print("\n=== Verifikasi Task 1.1 ===\n")
    jumlah_gagal = 0
    for nama_tes, status, kode, ringkas in hasil_baris:
        satu_baris = ringkas.replace("\n", " ")[:180]
        print(f"{status:5} | HTTP {kode:3} | {nama_tes:24} | {satu_baris}")
        if status == "FAIL" or status == "ERROR":
            jumlah_gagal += 1

    print(f"\nRingkas: SKIP tidak dihitung gagal. FAIL/ERROR: {jumlah_gagal}")
    if jumlah_gagal:
        print("\nTips OCR: pastikan Ollama jalan + model vision; OpenCV untuk fallback preprocess.")
        print("Tips audio_ask: STT harus menghasilkan teks non-kosong (rekaman bicara jelas).")
        return 1
    return 0


def buat_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifikasi Task 1.1 CodeBuddy")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL API")
    parser.add_argument("--gradio", default="http://127.0.0.1:7860", help="URL Gradio")
    parser.add_argument(
        "--audio-ask",
        default="",
        help="Path ke WAV/MP3 berisi pertanyaan (untuk tes /api/audio/ask)",
    )
    parser.add_argument(
        "--audio-stt",
        default="",
        help="Path audio untuk STT (opsional; default SKIP jika kosong)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout default HTTP (detik)")
    parser.add_argument("--timeout-llm", type=float, default=180.0, help="Timeout OCR/tutor/insight/audio (detik)")
    return parser


def main() -> None:
    parser = buat_parser()
    args = parser.parse_args()
    kode_keluar = asyncio.run(utama(args))
    sys.exit(kode_keluar)


if __name__ == "__main__":
    main()
