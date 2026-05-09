# CodeBuddy 🤖

**AI Coding Tutor untuk Pelajar Indonesia** — Powered by Gemma 4

> *Belajar Python jadi mudah! Foto kode tulisan tanganmu, dan CodeBuddy akan membaca, menjalankan, lalu menjelaskan errornya dalam Bahasa Indonesia — sepenuhnya offline.*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Gemma 4](https://img.shields.io/badge/Powered%20by-Gemma%204-orange.svg)](https://ai.google.dev/gemma)
[![Hackathon](https://img.shields.io/badge/Google%20Gemma%204-Good%20Hackathon%202026-red.svg)](https://www.kaggle.com/competitions/gemma-4-good-hackathon)

---

## Demo

```
Siswa SMP di daerah terpencil
        ↓ foto kode tulisan tangan di buku tulis
Gemma 4 Vision (offline)
        ↓ membaca kode dari foto
        ↓ menjalankan di sandbox aman
        ↓ mendeteksi & menganalisis error
        ↓
"Hei! Kamu menulis 'prin' tapi yang benar adalah 'print'.
 Seperti memanggil teman tapi salah sebut namanya 😊
 Kode yang benar: print('Halo Dunia'). Semangat ya!"
```

**100% offline — tidak butuh internet, tidak butuh cloud, data tidak keluar dari perangkat.**

---

## Fitur Utama

| Fitur | Teknologi | Keterangan |
|-------|-----------|------------|
| 📸 **OCR Tulisan Tangan** | Gemma 4 Vision (multimodal) | Foto kode → Python, tanpa library OCR terpisah |
| 🤖 **Analisis Kode AI** | Gemma 4 + Function Calling | Structured JSON output yang dijamin valid |
| 🏃 **Sandbox Aman** | RestrictedPython | Eksekusi Python tanpa risiko keamanan |
| 🎓 **Tutor Agentik** | 4-stage workflow | Syntax → Eksekusi → Error Analysis → Feedback |
| 💡 **Hint Bertahap** | Gemma 4 | Level 1–3, tidak langsung kasih jawaban |
| 📚 **Generate Latihan** | Gemma 4 | Soal latihan Python dalam Bahasa Indonesia |
| 🌐 **140+ Bahasa** | Gemma 4 | Termasuk bahasa daerah Indonesia |
| 🔒 **Offline-first** | Ollama | Cocok untuk daerah tanpa internet stabil |

---

## Arsitektur

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Gradio — localhost:7860)      │
│   📸 OCR  │  🎓 Tutor  │  📚 Latihan  │  👤 Siswa  │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────┐
│              Backend (FastAPI — localhost:8000)       │
│                                                      │
│  /api/ocr/extract  →  GemmaVisionService             │
│  /api/code/*       →  SafeCodeExecutor               │
│  /api/agent/*      →  CodeBuddyAgent                 │
│  /api/students/*   →  SQLAlchemy + SQLite            │
│  /api/exercises/*  →  GemmaService + manifest.json   │
└──────────┬──────────────────────────────────────────┘
           │
┌──────────▼──────────────────┐
│   Ollama (gemma4:e4b)        │
│   ✅ Vision (OCR gambar)     │
│   ✅ Function Calling        │
│   ✅ 128K context window     │
│   ✅ Berjalan lokal          │
└─────────────────────────────┘
```

---

## Quickstart

### Prasyarat
- Python 3.10+
- [Ollama](https://ollama.com) — `brew install ollama`
- 10GB+ RAM (M1/M2 Mac sangat cocok)

### Setup

```bash
# 1. Clone repo
git clone https://github.com/username/codebuddy.git
cd codebuddy

# 2. Install dependensi
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Pull Gemma 4
ollama serve &
ollama pull gemma4:e4b      # 10GB+ RAM
# atau: ollama pull gemma4:e2b  # 6GB+ RAM

# 4. Jalankan backend
uvicorn main:app --reload --port 8000

# 5. Jalankan frontend (terminal baru)
cd ../frontend
python app.py
```

Buka: **http://localhost:7860**

---

## Cara Penggunaan Gemma 4

### Vision — Baca Tulisan Tangan
```python
from services.llm_service import GemmaVisionService

svc = GemmaVisionService()
hasil = await svc.ekstrak_kode(image_bytes)
# Gemma 4 membaca foto kode tulisan tangan LANGSUNG
# {'code': 'print("halo")', 'confidence': 0.95}
```

### Function Calling — JSON Terstruktur
```python
from services.llm_service import GemmaService

svc = GemmaService()
hasil = await svc.analyze_code('prin("halo")', student_level='beginner')
# Output DIJAMIN valid JSON via Ollama format parameter
# {'understanding': '...', 'errors': [...], 'encouragement': '...'}
```

---

## Testing

```bash
cd backend
pytest tests/ -v          # 139 passed, 3 skipped
pytest tests/ --cov=.     # coverage report
```

---

## Fine-tuning (Bonus $10K Unsloth)

Dataset 55 contoh tersedia di `backend/data/finetune_dataset.json`.
Notebook siap pakai: `backend/data/finetune_unsloth.ipynb` — jalankan di Google Colab T4 gratis.

---

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| `POST` | `/api/ocr/extract` | Gemma 4 Vision: foto → kode |
| `POST` | `/api/code/execute` | Sandbox execution |
| `POST` | `/api/code/validate` | Syntax check |
| `POST` | `/api/agent/tutor` | Full tutoring session |
| `POST` | `/api/agent/hint` | Progressive hint (level 1–3) |
| `POST` | `/api/students/` | Register siswa |
| `GET`  | `/api/students/{id}/progress` | Student progress |
| `GET`  | `/api/exercises/` | Exercise list |
| `POST` | `/api/exercises/generate` | AI-generated exercise |

Docs interaktif: http://localhost:8000/docs

---

## Lisensi

[Apache License 2.0](LICENSE)

---

**Google Gemma 4 Good Hackathon 2026**
Kategori: *Future of Education* + *Digital Equity & Inclusivity*

*"Setiap anak Indonesia berhak belajar coding, tidak peduli di mana mereka tinggal."*
