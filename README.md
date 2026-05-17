<div align="center">

<img src="https://img.shields.io/badge/🤖-CodeBuddy-5B5BD6?style=for-the-badge&labelColor=1E1B4B" alt="CodeBuddy" height="48"/>

# CodeBuddy

### AI Coding Tutor untuk Pelajar Indonesia

*Foto kode tulisan tanganmu → Gemma 4 membaca → menjalankan → menjelaskan dalam bahasa ibumu*

<br/>

[![License](https://img.shields.io/badge/License-Apache_2.0-5B5BD6.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gemma 4](https://img.shields.io/badge/Gemma_4-e4b-F97316.svg?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/gemma)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-black.svg?style=flat-square)](https://ollama.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-139_passed-22C55E.svg?style=flat-square)](backend/tests/)
[![Hackathon](https://img.shields.io/badge/Google_Gemma_4_Good_Hackathon-2026-FF0000.svg?style=flat-square&logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/gemma-4-good-hackathon)

<br/>

> **"Setiap anak Indonesia berhak belajar coding,**
> **tidak peduli di mana mereka tinggal."**

<br/>

[🚀 Quickstart](#-quickstart) · [📖 Cara menjalankan (RUN.md)](RUN.md) · [✨ Fitur](#-fitur) · [🏗️ Arsitektur](#️-arsitektur) · [🌍 Bahasa Daerah](#-bahasa-daerah) · [📡 API](#-api-endpoints) · [🧬 Fine-tuning](#-fine-tuning)

</div>

---

## 🎯 Masalah yang Diselesaikan

Indonesia punya **8,5 juta anak SD** di daerah dengan koneksi internet tidak stabil. Banyak dari mereka:

- 📝 **Menulis kode di buku tulis** — tidak punya laptop atau komputer
- 🗣️ **Berbicara bahasa daerah** — belum fasih Bahasa Indonesia teknis
- 📖 **Belum lancar membaca** — untuk siswa kelas 1–3 SD
- 👨‍🏫 **Gurunya kewalahan** — 1 guru mengajar 30+ siswa dengan level berbeda

**CodeBuddy hadir untuk mereka** — bukan untuk yang sudah punya segalanya.

---

## ✨ Fitur

<table>
<tr>
<td width="50%">

### 📸 Gemma 4 Vision OCR
Upload foto kode tulisan tangan — **Gemma 4 membacanya langsung** tanpa library OCR terpisah. Mendukung foto buram, pencahayaan buruk, dan tulisan tidak rapi.

</td>
<td width="50%">

### 🤖 Agentic Tutoring
Pipeline 4 tahap otomatis: **Validasi Syntax → Eksekusi → Analisis Error → Feedback AI**. Bukan sekadar chatbot — AI mengambil keputusan di setiap tahap.

</td>
</tr>
<tr>
<td width="50%">

### 🎤 Mode Suara
Anak **rekam pertanyaan** dengan suara → AI jawab dengan **suara natural Bahasa Indonesia** via edge-tts. Untuk siswa yang belum lancar membaca atau menulis.

</td>
<td width="50%">

### 🌍 5 Bahasa Daerah
AI menjelaskan dalam **Bahasa Indonesia, Jawa Krama, Sunda, Minang, dan Batak Toba** — memanfaatkan kemampuan 140+ bahasa Gemma 4.

</td>
</tr>
<tr>
<td width="50%">

### 👨‍🏫 Dashboard Guru
Guru SD bisa pantau **progress seluruh kelas** sekaligus. Gemma 4 menganalisis pola error dan memberi **rekomendasi pengajaran konkret**.

</td>
<td width="50%">

### 🔒 100% Offline
Berjalan sepenuhnya via **Ollama** di perangkat lokal. Data siswa tidak pernah keluar dari perangkat — privasi terjaga, cocok untuk daerah tanpa internet.

</td>
</tr>
</table>

---

## 🏗️ Arsitektur

```
┌─────────────────────────────────────────────────┐
│           Frontend  (Gradio · port 7860)         │
│   📸 Foto  │  🎓 Tutor  │  🎤 Suara  │  👨‍🏫 Guru  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────┐
│            Backend  (FastAPI · port 8000)         │
│                                                   │
│  /api/ocr/extract    ──▶  GemmaVisionService      │
│  /api/agent/tutor    ──▶  CodeBuddyAgent          │
│  /api/audio/ask      ──▶  STT + LLM + TTS         │
│  /api/teacher/*      ──▶  Dashboard + AI Insight  │
│  /api/code/execute   ──▶  SafeCodeExecutor        │
│  /api/students/*     ──▶  SQLAlchemy + SQLite     │
└──────────┬──────────────────────┬────────────────┘
           │                      │
┌──────────▼──────────┐  ┌────────▼───────────────┐
│   Ollama            │  │  RestrictedPython       │
│   gemma4:e4b        │  │  Sandbox                │
│   ✅ Vision         │  │  ✅ Timeout 5s           │
│   ✅ Function Call  │  │  ✅ No import/file/net   │
│   ✅ 128K context   │  └────────────────────────┘
│   ✅ 140+ bahasa    │
└─────────────────────┘
```

---

## 🌍 Bahasa Daerah

Gemma 4 mendukung 140+ bahasa. CodeBuddy menggunakannya untuk menjangkau pelajar di seluruh nusantara:

| Kode | Bahasa | Contoh Respons AI |
|------|--------|-------------------|
| `id` | 🇮🇩 Bahasa Indonesia | *"Variabel 'x' belum didefinisikan. Pastikan sudah memberi nilai sebelum dipakai."* |
| `jw` | ☕ Basa Jawa Krama | *"Variabel 'x' dereng dipun-damel. Mangga dipun-damel rumiyin."* |
| `su` | 🌸 Basa Sunda | *"Variabel 'x' tacan didamel. Punten didamel heula sateuacanna dipaké."* |
| `min` | 🏔️ Bahaso Minang | *"Variabel 'x' alun ado. Tolong buek dulu sabalum dipakai."* |
| `bbc` | ⛵ Hata Batak Toba | *"Variabel 'x' ndang adong. Uli hutona jolo paima dipakai."* |

---

## 🚀 Quickstart

Panduan **langkah demi langkah**, variabel lingkungan, troubleshooting, CORS, rate limiting, dan ringkasan perintah ada di **[RUN.md](RUN.md)**. Catatan riset/desain UI ada di folder **[docs/](docs/)**.

### Prasyarat

- Python 3.10+
- [Ollama](https://ollama.com) — `brew install ollama` (macOS)
- RAM 10GB+ untuk `gemma4:e4b` · RAM 6GB+ untuk `gemma4:e2b`

### 1. Clone & Install

```bash
git clone https://github.com/adindamochamad/codebuddy.git
cd codebuddy/backend

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup Gemma 4 via Ollama

```bash
ollama serve                  # jalankan service
ollama pull gemma4:e4b        # ~5GB, sekali saja
```

### 3. Jalankan Backend

```bash
# dari folder backend/
uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

### 4. Jalankan Frontend

```bash
cd ../frontend
python app.py
# Buka: http://localhost:7860
```

### 5. (Opsional) Docker

```bash
docker compose up -d ollama
docker build -t codebuddy-backend .
docker run -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 codebuddy-backend
```

---

## 📁 Struktur Proyek

```
codebuddy/
├── backend/
│   ├── api/
│   │   ├── routes.py          # 16 endpoint utama
│   │   ├── teacher.py         # Mode Guru (dashboard + AI insight)
│   │   └── schemas.py         # Pydantic request/response models
│   ├── services/
│   │   ├── llm_service.py     # GemmaService + GemmaVisionService
│   │   ├── agent_service.py   # CodeBuddyAgent (4-stage workflow)
│   │   ├── audio_service.py   # TTS (edge-tts) + STT (faster-whisper)
│   │   ├── code_executor.py   # SafeCodeExecutor (RestrictedPython)
│   │   └── ocr_service.py     # Gemma4 Vision + PaddleOCR fallback
│   ├── models/
│   │   ├── database.py        # SQLAlchemy ORM (Student, Submission, Progress)
│   │   └── crud.py            # Async CRUD operations
│   ├── data/
│   │   ├── finetune_dataset.json    # 55 contoh fine-tuning Bahasa Indonesia
│   │   ├── finetune_unsloth.ipynb   # Notebook Colab siap pakai
│   │   └── exercises/manifest.json  # 8 latihan Python
│   └── tests/                 # 139 test (pytest)
├── frontend/
│   └── app.py                 # Gradio UI (6 tab)
├── docker-compose.yml
├── Dockerfile
└── STORY.md                   # Narasi & 3 persona pengguna
```

---

## 📡 API Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/ocr/extract` | 📸 Gemma 4 Vision: foto → kode Python |
| `POST` | `/api/agent/tutor` | 🤖 Sesi tutoring 4-stage + bahasa daerah |
| `POST` | `/api/agent/hint` | 💡 Hint bertahap level 1–3 |
| `POST` | `/api/audio/ask` | 🎤 Suara → AI → Suara (end-to-end) |
| `POST` | `/api/audio/tts` | 🔊 Text-to-Speech Bahasa Indonesia |
| `POST` | `/api/audio/stt` | 🎙️ Speech-to-Text (Whisper offline) |
| `POST` | `/api/code/execute` | ⚙️ Eksekusi Python di sandbox aman |
| `POST` | `/api/code/validate` | ✅ Validasi syntax tanpa eksekusi |
| `GET`  | `/api/teacher/dashboard` | 📊 Dashboard kelas guru |
| `GET`  | `/api/teacher/insights` | 🧠 AI insight untuk pengajaran |
| `POST` | `/api/exercises/generate` | 🎲 Generate latihan dengan Gemma 4 |
| `GET`  | `/api/languages/` | 🌍 Daftar bahasa daerah yang didukung |

> Dokumentasi interaktif: `http://localhost:8000/docs`

---

## 🧬 Fine-tuning

Dataset 55 contoh tersedia untuk fine-tuning Gemma 4 khusus tutoring Bahasa Indonesia:

```bash
# Jalankan di Google Colab (GPU T4 gratis)
# File: backend/data/finetune_unsloth.ipynb
```

Dataset mencakup:
- **15** contoh syntax error (typo, indentasi, tanda kutip)
- **15** contoh runtime error (NameError, TypeError, dll.)
- **10** contoh logic error (off-by-one, infinite loop, dll.)
- **10** contoh code quality (penamaan variabel, DRY principle)
- **5** contoh koreksi OCR (0 vs O, l vs 1, dll.)

---

## 👥 Untuk Siapa CodeBuddy Dibuat

<table>
<tr>
<td align="center" width="33%">
<h3>🌅 Andi, 9 tahun</h3>
<em>SD Larantuka, Flores</em>
<p>Internet hanya 2 jam/hari. Menulis kode di buku tulis. Foto pakai HP bekas → CodeBuddy menjelaskan errornya.</p>
</td>
<td align="center" width="33%">
<h3>🌴 Siti, 10 tahun</h3>
<em>SD Pedalaman Sumba</em>
<p>Bahasa ibu Kambera, Bahasa Indonesia masih kaku. Pakai Mode Suara — tanya dengan suara, dapat jawaban dengan suara.</p>
</td>
<td align="center" width="33%">
<h3>👨‍🏫 Pak Wayan, Guru</h3>
<em>MI Karangasem, Bali</em>
<p>Mengajar 4 sekolah seminggu. Dashboard Guru menunjukkan siapa yang stuck dan AI memberi saran pengajaran konkret.</p>
</td>
</tr>
</table>

---

## 🧪 Testing

```bash
cd backend
python -m pytest tests/ -v                                    # 139 passed, 3 skipped
python -m pytest tests/ --cov=. --cov-report=term-missing    # dengan coverage
```

---

## 🛠️ Tech Stack

| Layer | Teknologi |
|-------|-----------|
| **LLM** | Gemma 4 `e4b` via Ollama (Vision + Function Calling) |
| **Backend** | FastAPI, SQLAlchemy async, aiosqlite, Pydantic v2 |
| **Sandbox** | RestrictedPython, timeout via daemon thread |
| **Audio** | edge-tts (TTS), faster-whisper (STT offline) |
| **Frontend** | Gradio 6 |
| **Database** | SQLite (async) |
| **Testing** | pytest, pytest-asyncio, pytest-cov |
| **Deployment** | Docker, docker-compose |

---

## 📄 Lisensi

[Apache License 2.0](LICENSE) — bebas digunakan, dimodifikasi, dan didistribusikan.

---

## 🏆 Hackathon

Dibuat untuk **[Google Gemma 4 Good Hackathon 2026](https://www.kaggle.com/competitions/gemma-4-good-hackathon)**

- **Kategori utama:** Future of Education
- **Kategori kedua:** Digital Equity & Inclusivity
- **Special Track:** Ollama Prize · Unsloth Prize

---

<div align="center">

**CodeBuddy** · Dibuat dengan ❤️ untuk Pelajar Indonesia

*Powered by [Gemma 4](https://ai.google.dev/gemma) · Deployed with [Ollama](https://ollama.com)*

</div>
