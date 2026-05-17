# Cara menjalankan CodeBuddy

Panduan ini menjelaskan cara menjalankan **backend (FastAPI)**, **frontend (Gradio)**, dan **Ollama (Gemma 4)** di mesin lokal kamu.

---

## Ringkasan

| Komponen | Port | Peran |
|----------|------|--------|
| **Ollama** | `11434` | Model `gemma4:e4b` — LLM + vision untuk OCR, tutor, insight guru |
| **Backend** | `8000` | REST API (`/api/...`) |
| **Frontend** | `7860` | Antarmuka Gradio — memanggil backend lewat HTTP |

Urutan yang disarankan: **Ollama jalan dulu** → **backend** → **buka frontend**.

### Satu perintah (Ollama + backend + frontend)

Dari **akar repo** (`CodeBuddy/`), dengan venv sudah ada dan dependensi terpasang:

```bash
./scripts/jalankan_semua.sh
```

- Jika **Ollama sudah jalan** di `:11434`, skrip tidak memanggil `ollama serve` lagi.
- Tanpa men-start Ollama dari skrip (misalnya Ollama di terminal lain):  
  `JALANKAN_OLLAMA=0 ./scripts/jalankan_semua.sh`
- **Ctrl+C** di terminal itu menghentikan backend dan frontend yang di-start skrip (dan `ollama serve` hanya jika skrip yang menjalankannya).

---

## Prasyarat

- **Python 3.10+** (3.12 juga dipakai di banyak setup)
- **Git** (jika clone dari repositori)
- **Ollama** — [ollama.com](https://ollama.com) (misalnya `brew install ollama` di macOS)
- **RAM** cukup untuk model Gemma (lihat README; `gemma4:e4b` butuh memori besar)
- Untuk **Mode Suara (TTS/STT)**:
  - **TTS** (`edge-tts`): butuh akses internet ke layanan Microsoft Edge TTS saat generate suara
  - **STT** (`faster-whisper`): unduhan model besar **saat pertama kali** dipakai (~ ratusan MB, butuh internet sekali)

---

## 1. Siapkan lingkungan Python

Dari **akar folder proyek** (folder yang berisi `backend/` dan `frontend/`):

```bash
cd /path/ke/CodeBuddy

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt
```

**Catatan:** Satu virtual environment di akar repo (`CodeBuddy/.venv`) sudah cukup untuk backend dan frontend, karena `gradio` dan `httpx` ada di `backend/requirements.txt`.

### Dependensi opsional (Mode Suara)

Jika fitur audio error “belum terpasang”, pasang manual:

```bash
pip install edge-tts faster-whisper nest-asyncio
```

`nest-asyncio` membantu Gradio saat event loop sudah berjalan (impor opsional di frontend).

---

## 2. Jalankan Ollama dan tarik model Gemma

Di terminal terpisah (biarkan tetap jalan):

```bash
ollama serve
```

Lalu (sekali saja, atau jika model belum ada):

```bash
ollama pull gemma4:e4b
```

Pastikan backend bisa menjangkau Ollama di **`http://localhost:11434`** (default). Jika Ollama di mesin lain, set variabel lingkungan sebelum menjalankan backend:

```bash
export OLLAMA_BASE_URL=http://alamat-ip:11434
```

---

## 3. Jalankan backend (FastAPI)

```bash
cd backend
source ../.venv/bin/activate       # jika belum aktif
uvicorn main:app --reload --port 8000
```

- Dokumentasi interaktif: [http://localhost:8000/docs](http://localhost:8000/docs)
- Cek sehat: [http://localhost:8000/health](http://localhost:8000/health)

### CORS dan rate limiting (produksi)

- **CORS:** daftar origin yang diizinkan di `backend/utils/config.py` (`allowed_origins`). Untuk deployment HTTPS, tambahkan URL frontend kamu di sana.
- **Rate limit** (per IP, per menit): OCR ~20, jalankan kode ~60, agent/LLM ~10 — angka di `utils/config.py` (`rate_limit_*`). Lewati batas akan dapat respons **429**.

Database SQLite dibuat otomatis di `backend/data/codebuddy.db` saat startup. Data demo siswa diisi saat database masih kosong (lihat `backend/utils/database.py`).

---

## 4. Jalankan frontend (Gradio)

Di terminal **baru** (backend tetap jalan):

```bash
cd frontend
source ../.venv/bin/activate
python app.py
```

Buka browser: **[http://localhost:7860](http://localhost:7860)**  
(Tema terang dipaksa lewat query `__theme=light`.)

### Mengarahkan frontend ke API lain

Secara default frontend memanggil `http://localhost:8000`. Untuk mengubahnya:

```bash
export CODEBUDDY_API=http://127.0.0.1:8000
python app.py
```

---

## 5. Verifikasi cepat

```bash
curl -s http://localhost:8000/health
```

Respons JSON yang diharapkan memuat `"status":"ok"`.

---

## 6. (Opsional) Docker hanya untuk Ollama

Jika kamu lebih suka Ollama di kontainer:

```bash
docker compose up -d ollama
```

Backend tetap dijalankan di host (lihat langkah 3), dengan `OLLAMA_BASE_URL` mengarah ke kontainer jika perlu (misalnya `http://localhost:11434` jika port dipetakan seperti di `docker-compose.yml`).

---

## Pemecahan masalah umum

| Gejala | Yang bisa dicoba |
|--------|-------------------|
| `Connection refused` ke port 8000 | Pastikan `uvicorn` sudah jalan di folder `backend/`. |
| Tutor / OCR / insight lambat atau gagal | Pastikan `ollama serve` jalan dan model `gemma4:e4b` sudah di-`pull`. Respons bisa 15–60 detik. |
| Port 8000 atau 7860 sudah dipakai | Tutup proses lain atau ganti port, misalnya `uvicorn main:app --port 8001` lalu `export CODEBUDDY_API=http://localhost:8001` sebelum `python app.py`. |
| TTS gagal / timeout | Periksa firewall dan koneksi internet (edge-tts memanggil layanan Microsoft). |
| STT pertama kali sangat lama | Normal: unduhan model Whisper; setelah itu lebih cepat dan bisa offline. |
| Frontend tidak menampilkan data | Pastikan backend sudah jalan **sebelum** memakai tab yang memanggil API. |

---

## Menjalankan tes otomatis

Dari folder `backend/` dengan venv aktif:

```bash
cd backend
python -m pytest tests/ -q
```

---

## Ringkasan perintah (copy-paste)

```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Backend
cd CodeBuddy/backend && source ../.venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 3 — Frontend
cd CodeBuddy/frontend && source ../.venv/bin/activate && python app.py
```

Setelah itu buka **http://localhost:7860** dan pastikan Ollama sudah berjalan dengan model yang dipakai proyek.
