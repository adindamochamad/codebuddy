#!/usr/bin/env bash
# Menjalankan Ollama + backend FastAPI + frontend Gradio dalam satu proses induk.
# Penghentian: Ctrl+C — skrip memberhentikan proses anak yang sempat di-start di sini.

set -euo pipefail

akar_proyek="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$akar_proyek"

if [[ ! -f .venv/bin/activate ]]; then
  echo "⚠️  Virtual env belum ada. Buat dulu dari akar repo:"
  echo "   python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
  exit 1
fi

# shellcheck source=/dev/null
source .venv/bin/activate

opsi_ollama="${JALANKAN_OLLAMA:-1}"
# Lewati Ollama: JALANKAN_OLLAMA=0 ./scripts/jalankan_semua.sh
daftar_pid=()

membersihkan() {
  echo ""
  echo "[CodeBuddy] Menghentikan proses yang dimulai skrip ini..."
  for pid in "${daftar_pid[@]:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap membersihkan EXIT INT TERM

ollama_sudah_jalan() {
  curl -sS -m 2 "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1
}

if [[ "$opsi_ollama" != "0" ]]; then
  if command -v ollama >/dev/null 2>&1; then
    if ollama_sudah_jalan; then
      echo "[CodeBuddy] Ollama sudah merespons di :11434 — lewati 'ollama serve'."
    else
      echo "[CodeBuddy] Menjalankan ollama serve..."
      ollama serve &
      daftar_pid+=("$!")
      sleep 2
    fi
  else
    echo "[CodeBuddy] Perintah 'ollama' tidak di PATH — lewati (jika pakai Ollama di mesin lain, jalankan manual)."
  fi
else
  echo "[CodeBuddy] JALANKAN_OLLAMA=0 — melewati Ollama."
fi

echo "[CodeBuddy] Menjalankan backend (uvicorn :8000)..."
(
  cd "$akar_proyek/backend"
  exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &
daftar_pid+=("$!")

sleep 1

echo "[CodeBuddy] Menjalankan frontend (Gradio :7860)..."
(
  cd "$akar_proyek/frontend"
  exec python app.py
) &
daftar_pid+=("$!")

echo ""
echo "[CodeBuddy] Semua layanan dimulai. Buka http://127.0.0.1:7860"
echo "[CodeBuddy] Tekan Ctrl+C di terminal ini untuk menghentikan proses di atas."
echo ""
wait
