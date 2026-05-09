"""CodeBuddy — Gradio Frontend untuk Pelajar SD Indonesia.

Fitur utama:
- 🎨 Mode Anak SD: visual besar, suara, mascot
- 🌍 5 Bahasa Daerah: Indonesia, Jawa, Sunda, Minang, Batak
- 🎤 Mode Suara: rekam pertanyaan, AI jawab dengan suara
- 📸 Foto Kode: Gemma 4 Vision baca tulisan tangan
- 🎓 Mode Tutor: analisis kode + feedback bertahap
- 👨‍🏫 Mode Guru: dashboard kelas + AI insight

Jalankan:
    cd frontend
    /Users/mac/Development/CodeBuddy/.venv/bin/python app.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import gradio as gr
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

_API = os.getenv("CODEBUDDY_API", "http://localhost:8000")
_TIMEOUT = 180.0  # 3 menit untuk audio + LLM

# Bahasa daerah yang didukung
BAHASA_OPSI = {
    "🇮🇩 Bahasa Indonesia": "id",
    "ꦗ Basa Jawa Krama": "jw",
    "ᮞ Basa Sunda": "su",
    "𑌐 Bahaso Minang": "min",
    "ᯅ Hata Batak Toba": "bbc",
}

# =========================================================================== #
# Custom CSS — Ramah anak, warna ceria, font besar                            #
# =========================================================================== #

CUSTOM_CSS = """
/* Background ceria untuk anak SD */
.gradio-container {
    background: linear-gradient(135deg, #FFF6E5 0%, #FFE5EC 50%, #E5F4FF 100%) !important;
    font-family: 'Comic Sans MS', 'Inter', system-ui, sans-serif !important;
}

/* Hero anak SD */
.kid-hero {
    background: linear-gradient(135deg, #FFD93D 0%, #FF8C42 50%, #FF6B9D 100%);
    color: white;
    padding: 40px 32px;
    border-radius: 28px;
    text-align: center;
    box-shadow: 0 12px 40px rgba(255, 107, 157, 0.35);
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}

.kid-hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -10%;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
    border-radius: 50%;
}

.kid-hero::after {
    content: '';
    position: absolute;
    bottom: -30%; right: -10%;
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
    border-radius: 50%;
}

.mascot {
    font-size: 6rem !important;
    margin-bottom: 8px;
    display: inline-block;
    animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.kid-title {
    font-size: 4rem !important;
    font-weight: 900 !important;
    margin: 0 !important;
    text-shadow: 3px 3px 0 rgba(0,0,0,0.15);
    letter-spacing: -0.02em;
}

.kid-tagline {
    font-size: 1.4rem !important;
    margin-top: 12px !important;
    font-weight: 600;
    text-shadow: 2px 2px 0 rgba(0,0,0,0.1);
}

.lang-badges {
    display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
    margin-top: 24px;
}

.lang-badge {
    background: rgba(255,255,255,0.95);
    color: #FF6B9D;
    padding: 10px 20px;
    border-radius: 100px;
    font-size: 1rem;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Tombol besar untuk anak SD */
button.primary {
    background: linear-gradient(135deg, #FF8C42 0%, #FF6B9D 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 18px 36px !important;
    font-weight: 800 !important;
    font-size: 1.2rem !important;
    box-shadow: 0 6px 20px rgba(255,107,157,0.4) !important;
    transition: all 0.2s ease !important;
}

button.primary:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 30px rgba(255,107,157,0.5) !important;
}

button.primary:active {
    transform: translateY(0) !important;
}

/* Tabs ramah anak */
.tab-nav {
    background: white !important;
    border-radius: 20px !important;
    padding: 8px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
    margin-bottom: 24px !important;
}

.tab-nav button {
    border-radius: 14px !important;
    font-weight: 700 !important;
    padding: 14px 24px !important;
    font-size: 1.05rem !important;
    transition: all 0.2s ease !important;
    border: none !important;
}

.tab-nav button.selected {
    background: linear-gradient(135deg, #FFD93D 0%, #FF8C42 100%) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(255,140,66,0.4) !important;
    transform: scale(1.05);
}

/* Card untuk anak */
.kid-card {
    background: white;
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    border: 3px solid transparent;
    transition: all 0.3s ease;
}

.kid-card:hover {
    border-color: #FFD93D;
    transform: translateY(-2px);
}

/* Status emojis besar */
.status-success-kid {
    background: linear-gradient(135deg, #5BFFA1 0%, #00D67D 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 16px;
    font-weight: 800;
    font-size: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 14px rgba(0,214,125,0.3);
}

.status-error-kid {
    background: linear-gradient(135deg, #FF8B8B 0%, #FF5757 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 16px;
    font-weight: 800;
    font-size: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 14px rgba(255,87,87,0.3);
}

.status-warning-kid {
    background: linear-gradient(135deg, #FFD93D 0%, #FFA500 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 16px;
    font-weight: 800;
    font-size: 1.2rem;
    text-align: center;
}

/* Info boxes */
.info-box-kid {
    background: linear-gradient(135deg, #B5DEFF 0%, #BFDBFE 100%);
    border-left: 6px solid #3B82F6;
    padding: 18px 22px;
    border-radius: 14px;
    margin: 16px 0;
    font-size: 1.05rem;
    font-weight: 500;
}

.success-box-kid {
    background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
    border-left: 6px solid #10B981;
    padding: 18px 22px;
    border-radius: 14px;
    margin: 16px 0;
    font-size: 1.05rem;
}

/* Stat cards lebih ceria */
.stat-card {
    background: linear-gradient(135deg, #FFD93D 0%, #FF8C42 100%);
    color: white;
    padding: 24px;
    border-radius: 20px;
    text-align: center;
    box-shadow: 0 6px 20px rgba(255,140,66,0.3);
}

.stat-number {
    font-size: 3rem;
    font-weight: 900;
    line-height: 1;
}

.stat-label {
    font-size: 0.95rem;
    opacity: 0.95;
    margin-top: 6px;
    font-weight: 700;
    text-transform: uppercase;
}

/* Mascot speech bubble */
.speech-bubble {
    background: white;
    padding: 20px 24px;
    border-radius: 20px;
    border: 3px solid #FFD93D;
    position: relative;
    margin-top: 20px;
    font-size: 1.1rem;
    line-height: 1.5;
}

.speech-bubble::before {
    content: '';
    position: absolute;
    top: -16px;
    left: 40px;
    width: 30px;
    height: 30px;
    background: white;
    border-top: 3px solid #FFD93D;
    border-left: 3px solid #FFD93D;
    transform: rotate(45deg);
}

/* Footer */
.kid-footer {
    text-align: center;
    padding: 32px;
    color: #6B7280;
    margin-top: 40px;
    font-size: 1rem;
}

/* Audio player */
audio {
    width: 100%;
    border-radius: 12px;
}

/* Code blocks lebih jelas */
.code-input {
    border-radius: 16px !important;
    border: 3px solid #FFD93D !important;
    font-size: 1.05rem !important;
}

.code-input:focus-within {
    border-color: #FF6B9D !important;
}

/* Heading */
h2, h3 {
    color: #1F2937;
    font-weight: 800;
}

h2 {
    border-bottom: 4px solid #FFD93D;
    padding-bottom: 8px;
    display: inline-block;
}

/* Larger inputs for kid mode */
input[type="text"], textarea, select {
    border-radius: 14px !important;
    border: 2px solid #FFD93D !important;
    padding: 12px 16px !important;
    font-size: 1.05rem !important;
}

/* Image input lebih ramah */
.image-container {
    border-radius: 20px !important;
    border: 4px dashed #FFD93D !important;
    background: rgba(255,217,61,0.05) !important;
}
"""


# =========================================================================== #
# API helpers                                                                  #
# =========================================================================== #

async def _post(endpoint: str, **kwargs) -> dict:
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as client:
        resp = await client.post(endpoint, **kwargs)
        resp.raise_for_status()
        return resp.json()


async def _post_raw(endpoint: str, **kwargs):
    """Untuk endpoint yang return file (audio MP3)."""
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as client:
        resp = await client.post(endpoint, **kwargs)
        resp.raise_for_status()
        return resp.content, dict(resp.headers)


async def _get(endpoint: str, **kwargs) -> dict:
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as client:
        resp = await client.get(endpoint, **kwargs)
        resp.raise_for_status()
        return resp.json()


def run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# =========================================================================== #
# Tab handlers                                                                 #
# =========================================================================== #

def tab_ocr_kirim(gambar_path):
    if gambar_path is None:
        return "", '<div class="status-warning-kid">⚠️ Yuk upload foto kodenya dulu!</div>'

    with open(gambar_path, "rb") as f:
        isi = f.read()

    try:
        data = run(_post(
            "/api/ocr/extract",
            files={"berkas": ("foto.jpg", isi, "image/jpeg")},
        ))
        kode = data.get("text", "")
        engine = data.get("engine", "?")
        conf = data.get("confidence", 0.0)
        return kode, f'<div class="status-success-kid">🎉 Berhasil baca kodenya!<br><small>🤖 {engine} • Tingkat yakin: {conf:.0%}</small></div>'
    except Exception as e:
        return "", f'<div class="status-error-kid">😅 Gagal: {str(e)[:200]}</div>'


def tab_tutor_kirim(kode, student_id_str, level, exercise_id, bahasa_label):
    if not kode.strip():
        return "", "", "", '<div class="status-warning-kid">📝 Yuk tulis kode dulu di sebelah kiri!</div>'

    bahasa_kode = BAHASA_OPSI.get(bahasa_label, "id")

    try:
        sid = int(student_id_str) if student_id_str.strip().isdigit() else 1
    except ValueError:
        sid = 1

    try:
        data = run(_post("/api/agent/tutor", json={
            "code": kode,
            "student_id": sid,
            "student_level": level,
            "exercise_id": exercise_id or None,
            "bahasa": bahasa_kode,
        }))

        final = data.get("final_result", "?")
        attempts = data.get("attempts", [])

        output_exec = ""
        for a in attempts:
            if a.get("stage") == "execution":
                output_exec = a.get("output", "") or ""

        feedback = {}
        for a in reversed(attempts):
            if a.get("ai_feedback"):
                feedback = a["ai_feedback"]
                break

        understanding = feedback.get("understanding", "")
        encouragement = feedback.get("encouragement", "")
        errors = feedback.get("errors", [])
        suggestions = feedback.get("suggestions", [])

        # Status dengan emoji besar
        status_html = {
            "success": '<div class="status-success-kid">🎉 HEBAT! Kodemu jalan dengan baik!</div>',
            "syntax_error": '<div class="status-error-kid">📝 Ada salah ketik nih, ayo perbaiki bareng!</div>',
            "runtime_error": '<div class="status-warning-kid">⚠️ Ada masalah saat dijalankan, mari kita cek!</div>',
            "timeout": '<div class="status-warning-kid">⏱️ Kodenya lambat banget, mungkin ada loop forever!</div>',
        }.get(final, f'<div class="status-warning-kid">{final}</div>')

        # Speech bubble dari mascot
        ai_md = ""
        if encouragement:
            ai_md += f'<div class="speech-bubble">🤖 <b>CodeBuddy bilang:</b><br><br>{encouragement}</div>\n\n'
        if understanding:
            ai_md += f"### 🧠 Tentang kodemu\n{understanding}\n\n"
        if errors:
            ai_md += "### 🔍 Yang perlu diperbaiki\n"
            for e in errors:
                line = f"Baris {e['line']}: " if e.get("line") else ""
                ai_md += f"- 🔴 {line}{e.get('explanation', '')}\n"
                if e.get("fix"):
                    ai_md += f"  - 💡 *{e['fix']}*\n"
            ai_md += "\n"
        if suggestions:
            ai_md += "### ✨ Tips dari Tutor\n"
            for s in suggestions:
                ai_md += f"- {s}\n"

        return (
            output_exec or "(belum ada output)",
            ai_md or "_Loading..._",
            feedback.get("corrected_code", "") or "# Kodemu sudah benar! 🎉",
            status_html,
        )

    except Exception as e:
        return "", "", "", f'<div class="status-error-kid">😅 Gagal: {str(e)[:300]}</div>'


def tab_audio_tanya(audio_path, bahasa_label, level):
    """Pipeline: rekam suara → STT → AI → TTS → MP3."""
    if audio_path is None:
        return None, '<div class="status-warning-kid">🎤 Yuk rekam pertanyaanmu dulu!</div>'

    bahasa_kode = BAHASA_OPSI.get(bahasa_label, "id")

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        # Endpoint /audio/ask returns MP3 langsung
        content, headers = run(_post_raw(
            "/api/audio/ask",
            files={"berkas": ("rekaman.wav", audio_bytes, "audio/wav")},
            params={"bahasa": bahasa_kode, "student_level": level},
        ))

        # Simpan MP3 hasil ke temp file
        import tempfile
        out_path = tempfile.mktemp(suffix=".mp3")
        with open(out_path, "wb") as f:
            f.write(content)

        # Header punya transkrip
        pertanyaan = headers.get("x-pertanyaan", "(tidak terdeteksi)")
        jawaban = headers.get("x-jawaban", "(no response)")

        info_html = f'''
        <div class="success-box-kid">
        🎤 <b>Pertanyaanmu:</b> {pertanyaan}<br><br>
        🤖 <b>Jawaban CodeBuddy:</b> {jawaban}<br><br>
        🔊 <i>Klik tombol play di bawah untuk dengar jawabannya!</i>
        </div>
        '''
        return out_path, info_html

    except Exception as e:
        return None, f'<div class="status-error-kid">😅 Gagal: {str(e)[:300]}</div>'


def tab_tts_baca(teks, bahasa_label, gender):
    """Generate suara dari teks."""
    if not teks.strip():
        return None, '<div class="status-warning-kid">📝 Tulis teks yang mau dibaca dulu!</div>'

    bahasa_kode = BAHASA_OPSI.get(bahasa_label, "id")

    try:
        content, _ = run(_post_raw(
            "/api/audio/tts",
            json={"teks": teks, "bahasa": bahasa_kode, "gender": gender},
        ))

        import tempfile
        out_path = tempfile.mktemp(suffix=".mp3")
        with open(out_path, "wb") as f:
            f.write(content)

        return out_path, '<div class="status-success-kid">🔊 Suara siap! Klik play untuk dengar.</div>'
    except Exception as e:
        return None, f'<div class="status-error-kid">😅 Gagal: {str(e)[:200]}</div>'


def tab_latihan_list(difficulty):
    try:
        params = {"difficulty": difficulty} if difficulty != "semua" else {}
        data = run(_get("/api/exercises/", params=params))
        items = data.get("latihan", [])
        if not items:
            return '<div class="info-box-kid">📭 Belum ada latihan untuk filter ini.</div>'

        diff_emoji = {"beginner": "🌱", "intermediate": "🌿", "advanced": "🌳"}
        diff_color = {"beginner": "#10B981", "intermediate": "#F59E0B", "advanced": "#EF4444"}

        out = '<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:16px;">'
        for item in items:
            color = diff_color.get(item['difficulty'], '#6B7280')
            emoji = diff_emoji.get(item['difficulty'], '📚')
            out += f'''
<div class="kid-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="margin:0;">{emoji} {item['judul']}</h3>
        <span style="background:{color}; color:white; padding:4px 12px; border-radius:100px; font-size:0.85rem; font-weight:700;">{item['difficulty'].upper()}</span>
    </div>
    <p style="color:#6B7280; margin:12px 0;">{item['ringkas']}</p>
    <pre style="background:#1F2937; color:#F3F4F6; padding:12px; border-radius:10px; overflow-x:auto; margin:0; font-size:0.9rem;"><code>{item['starter_code']}</code></pre>
</div>
            '''
        out += '</div>'
        return out
    except Exception as e:
        return f'<div class="status-error-kid">😅 Gagal: {e}</div>'


def tab_generate_latihan(topik, difficulty, bahasa_label):
    if not topik.strip():
        return "", "", "", '<div class="status-warning-kid">📝 Tulis topiknya dulu (contoh: warung, sepak bola)!</div>'

    bahasa_kode = BAHASA_OPSI.get(bahasa_label, "id")

    try:
        data = run(_post("/api/exercises/generate", json={
            "topic": topik,
            "difficulty": difficulty,
            "bahasa": bahasa_kode,
        }))
        if "error" in data:
            return "", "", "", '<div class="status-error-kid">😅 AI gagal generate. Coba lagi ya!</div>'

        return (
            data.get("title", ""),
            data.get("instructions", ""),
            data.get("starter_code", ""),
            '<div class="status-success-kid">✨ Latihan baru siap dimainkan!</div>',
        )
    except Exception as e:
        return "", "", "", f'<div class="status-error-kid">😅 Gagal: {e}</div>'


def tab_daftar_siswa(nama, usia_str, level):
    if not nama.strip():
        return '<div class="status-warning-kid">📝 Tulis nama dulu ya!</div>'
    try:
        usia = int(usia_str) if usia_str.strip().isdigit() else None
        data = run(_post("/api/students/", json={"name": nama, "age": usia, "level": level}))
        return f'''
<div class="success-box-kid">
    <b>🎉 Yay! {data['name']} sudah terdaftar!</b><br><br>
    🆔 ID kamu: <b style="font-size:1.5rem;">{data['id']}</b><br>
    📊 Level: <b>{data['level']}</b><br><br>
    Catat ID-mu untuk lihat progress nanti!
</div>
        '''
    except Exception as e:
        return f'<div class="status-error-kid">😅 Gagal: {e}</div>'


def tab_progres_siswa(student_id_str):
    if not student_id_str.strip().isdigit():
        return '<div class="status-warning-kid">⚠️ Masukkan ID siswa (angka)!</div>'
    try:
        sid = int(student_id_str)
        data = run(_get(f"/api/students/{sid}/progress"))
        nama = data.get("nama", "?")
        level = data.get("level", "?")
        selesai = data.get("total_selesai", 0)
        rata = data.get("rata_rata_skor")
        latihan = data.get("latihan", [])
        rata_str = f"{rata:.0f}" if rata else "—"

        html = f'''
<div class="kid-card">
    <h2 style="text-align:center;">🌟 {nama} 🌟</h2>
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin:24px 0;">
        <div class="stat-card">
            <div class="stat-number">{selesai}</div>
            <div class="stat-label">Latihan ✅</div>
        </div>
        <div class="stat-card" style="background:linear-gradient(135deg,#5BFFA1 0%,#00D67D 100%);">
            <div class="stat-number">{rata_str}</div>
            <div class="stat-label">Skor Rata2</div>
        </div>
        <div class="stat-card" style="background:linear-gradient(135deg,#A78BFA 0%,#7C3AED 100%);">
            <div class="stat-number" style="font-size:1.6rem; padding-top:8px;">{level}</div>
            <div class="stat-label">Level</div>
        </div>
    </div>
    <h3>📚 Latihan yang Sudah Dicoba</h3>
        '''

        if latihan:
            for l in latihan:
                emoji = "🎉" if l["completed"] else "🔄"
                color = "#10B981" if l["completed"] else "#F59E0B"
                avg = f"{l['avg_score']:.0f}" if l["avg_score"] else "—"
                html += f'''
<div style="background:#F9FAFB; padding:14px 18px; border-radius:12px; margin-bottom:10px; border-left:5px solid {color}; display:flex; justify-content:space-between; align-items:center;">
    <div>
        <b>{emoji} {l['exercise_id']}</b><br>
        <small>Sudah dicoba {l['attempts']}× — Skor: {avg}</small>
    </div>
</div>
                '''
        else:
            html += '<div class="info-box-kid">📭 Belum ada latihan yang dicoba. Yuk mulai!</div>'

        html += '</div>'
        return html

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return '<div class="status-error-kid">😅 ID-nya gak ada nih, coba cek lagi!</div>'
        return f'<div class="status-error-kid">😅 {e}</div>'
    except Exception as e:
        return f'<div class="status-error-kid">😅 Gagal: {e}</div>'


def tab_guru_dashboard():
    """Mode guru — dashboard kelas."""
    try:
        data = run(_get("/api/teacher/dashboard"))
        ringkasan = data.get("ringkasan", {})
        distribusi = data.get("distribusi_level", {})
        latihan_pop = data.get("latihan_populer", [])
        siswa_stuck = data.get("siswa_stuck", [])
        top_errors = data.get("top_errors", [])

        html = f'''
<div class="kid-card">
    <h2>📊 Dashboard Kelas</h2>
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:14px; margin:20px 0;">
        <div class="stat-card">
            <div class="stat-number">{ringkasan.get("total_siswa", 0)}</div>
            <div class="stat-label">Siswa</div>
        </div>
        <div class="stat-card" style="background:linear-gradient(135deg,#5BFFA1 0%,#00D67D 100%);">
            <div class="stat-number">{ringkasan.get("total_submission", 0)}</div>
            <div class="stat-label">Submission</div>
        </div>
        <div class="stat-card" style="background:linear-gradient(135deg,#A78BFA 0%,#7C3AED 100%);">
            <div class="stat-number">{ringkasan.get("submission_sukses", 0)}</div>
            <div class="stat-label">Sukses</div>
        </div>
        <div class="stat-card" style="background:linear-gradient(135deg,#3B82F6 0%,#1E40AF 100%);">
            <div class="stat-number">{ringkasan.get("success_rate_persen", 0):.0f}%</div>
            <div class="stat-label">Success Rate</div>
        </div>
    </div>

    <h3>👥 Distribusi Level Siswa</h3>
    <div style="display:flex; gap:16px; margin:16px 0;">
        '''
        for lvl, jml in distribusi.items():
            html += f'<div style="flex:1; background:#F3F4F6; padding:14px; border-radius:12px; text-align:center;"><b>{lvl}</b><br><span style="font-size:1.8rem; font-weight:800;">{jml}</span></div>'
        html += '</div>'

        if latihan_pop:
            html += '<h3>🔥 Latihan Paling Populer</h3>'
            for l in latihan_pop[:5]:
                html += f'<div style="background:#FEF3C7; padding:10px 14px; border-radius:8px; margin-bottom:6px; display:flex; justify-content:space-between;"><b>{l["exercise_id"]}</b><span>{l["total_attempts"]} attempts</span></div>'

        if siswa_stuck:
            html += '<h3 style="margin-top:20px;">⚠️ Siswa Butuh Bantuan</h3>'
            for s in siswa_stuck:
                html += f'<div style="background:#FEE2E2; padding:12px 16px; border-radius:10px; margin-bottom:8px;"><b>{s["nama"]}</b> stuck di <code>{s["exercise_id"]}</code> — sudah {s["attempts"]} attempts</div>'

        if top_errors:
            html += '<h3 style="margin-top:20px;">🔴 Error Paling Sering</h3>'
            for e in top_errors:
                html += f'<div style="background:#F3F4F6; padding:8px 12px; border-radius:8px; margin-bottom:4px;"><code>{e["type"]}</code> — {e["count"]} kali</div>'

        html += '</div>'
        return html

    except Exception as e:
        return f'<div class="status-error-kid">😅 Gagal load dashboard: {e}</div>'


def tab_guru_insight():
    """Mode guru — AI insight dari Gemma 4."""
    try:
        data = run(_get("/api/teacher/insights"))
        ai = data.get("ai_insight", {})

        html = f'''
<div class="kid-card">
    <h2>🤖 AI Insight dari Gemma 4</h2>

    <div class="info-box-kid">
        <b>📋 Kondisi Kelas:</b><br>
        {ai.get("kondisi_kelas", "—")}
    </div>

    <div style="background:#FEF3C7; border-left:6px solid #F59E0B; padding:18px 22px; border-radius:14px; margin:16px 0;">
        <b>🎯 Topik yang Perlu Perhatian:</b><br>
        {ai.get("topik_perhatian", "—")}
    </div>

    <h3>💡 Saran untuk Pelajaran Berikutnya</h3>
        '''
        for i, saran in enumerate(ai.get("saran_pengajaran", []), 1):
            html += f'<div class="success-box-kid"><b>{i}.</b> {saran}</div>'

        html += f'''
    <div style="background:#FEE2E2; border-left:6px solid #EF4444; padding:18px 22px; border-radius:14px; margin:16px 0;">
        <b>🆘 Siswa yang Butuh Perhatian Khusus:</b><br>
        {ai.get("siswa_butuh_bantuan", "—")}
    </div>
</div>
        '''
        return html

    except Exception as e:
        return f'<div class="status-error-kid">😅 Gagal: {e}</div>'


# =========================================================================== #
# Build UI                                                                     #
# =========================================================================== #

# Force theme light — sistem dark mode bug di Gradio 6
HEAD_FORCE_LIGHT = """
<script>
(function() {
    const url = new URL(window.location.href);
    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.replace(url.toString());
    }
})();
</script>
"""

with gr.Blocks(
    title="CodeBuddy 🤖 — Tutor Coding untuk Pelajar Indonesia",
) as demo:

    # ── HERO ──────────────────────────────────────────────────────────── #
    gr.HTML("""
    <div class="kid-hero">
        <div class="mascot">🤖</div>
        <h1 class="kid-title">CodeBuddy</h1>
        <p class="kid-tagline">
            Tutor Coding untuk Anak Indonesia ⭐<br>
            <span style="font-size:1rem; opacity:0.95;">Powered by Gemma 4 — Tanpa Internet</span>
        </p>
        <div class="lang-badges">
            <span class="lang-badge">🇮🇩 Indonesia</span>
            <span class="lang-badge">ꦗ Jawa</span>
            <span class="lang-badge">ᮞ Sunda</span>
            <span class="lang-badge">𑌐 Minang</span>
            <span class="lang-badge">ᯅ Batak</span>
        </div>
    </div>
    """)

    # Bahasa selector global
    bahasa_global = gr.Dropdown(
        list(BAHASA_OPSI.keys()),
        value="🇮🇩 Bahasa Indonesia",
        label="🌍 Pilih Bahasa Tutor",
        info="AI akan menjawab dalam bahasa yang kamu pilih",
    )

    with gr.Tabs():

        # ═══ TAB 1: FOTO KODE ═══════════════════════════════════════════ #
        with gr.Tab("📸 Foto Kode"):
            gr.HTML('<div class="info-box-kid">📷 <b>Foto kodemu yang ada di buku tulis!</b> Gemma 4 akan baca tulisan tanganmu dan ubah jadi kode komputer.</div>')

            with gr.Row():
                with gr.Column():
                    inp_gambar = gr.Image(
                        label="📷 Foto Kode Tulisan Tangan Kamu",
                        type="filepath",
                        sources=["upload", "webcam", "clipboard"],
                        height=380,
                        elem_classes="image-container",
                    )
                    btn_ocr = gr.Button("✨ Yuk Baca Kodenya!", variant="primary", size="lg")

                with gr.Column():
                    out_info_ocr = gr.HTML()
                    out_kode_ocr = gr.Code(
                        label="📝 Kode yang Berhasil Dibaca",
                        language="python",
                        lines=16,
                        elem_classes="code-input",
                    )

            btn_ocr.click(tab_ocr_kirim, [inp_gambar], [out_kode_ocr, out_info_ocr])

        # ═══ TAB 2: TUTOR ═══════════════════════════════════════════════ #
        with gr.Tab("🎓 Tutor AI"):
            gr.HTML('<div class="info-box-kid">🎯 <b>Mau dapat feedback?</b> Tulis kodemu, AI akan menjalankan dan menjelaskan dengan ramah.</div>')

            with gr.Row():
                with gr.Column():
                    inp_kode = gr.Code(
                        label="✍️ Tulis Kode Python",
                        language="python",
                        lines=12,
                        value='# Contoh kode dengan error - coba klik tombol di bawah!\nnama = "Adik"\numur = 10\nprint("Halo " + nama + ", umur " + umur)\n',
                        elem_classes="code-input",
                    )
                    with gr.Row():
                        inp_sid = gr.Textbox(label="🆔 ID Siswa", value="1", scale=1)
                        inp_level = gr.Dropdown(
                            ["beginner", "intermediate", "advanced"],
                            value="beginner", label="📊 Level", scale=2,
                        )
                    inp_exercise = gr.Textbox(label="🎯 ID Latihan (opsional)", placeholder="hello_print")
                    btn_tutor = gr.Button("🚀 Cek Kode dengan AI!", variant="primary", size="lg")

                with gr.Column():
                    out_status = gr.HTML()
                    with gr.Tabs():
                        with gr.Tab("💬 Feedback"):
                            out_feedback = gr.Markdown()
                        with gr.Tab("⚙️ Output"):
                            out_exec = gr.Textbox(label="Hasil Run", lines=8)
                        with gr.Tab("✅ Diperbaiki"):
                            out_fix = gr.Code(language="python", lines=10)

            btn_tutor.click(
                tab_tutor_kirim,
                [inp_kode, inp_sid, inp_level, inp_exercise, bahasa_global],
                [out_exec, out_feedback, out_fix, out_status],
            )

        # ═══ TAB 3: MODE SUARA ════════════════════════════════════════ #
        with gr.Tab("🎤 Mode Suara"):
            gr.HTML('''
            <div class="info-box-kid">
                <b>🎤 Belum lancar baca-tulis? Tidak apa-apa!</b><br>
                Rekam pertanyaanmu pakai suara, AI akan menjawab dengan suara juga — dalam bahasa yang kamu pilih di atas.
            </div>
            ''')

            gr.Markdown("## 🗣️ Tanya CodeBuddy Pakai Suara")

            with gr.Row():
                with gr.Column():
                    inp_audio = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        label="🎤 Tekan tombol untuk rekam pertanyaanmu",
                    )
                    inp_level_audio = gr.Dropdown(
                        ["beginner", "intermediate", "advanced"],
                        value="beginner",
                        label="📊 Level Kamu",
                    )
                    btn_audio = gr.Button("🚀 Tanya AI!", variant="primary", size="lg")

                with gr.Column():
                    out_audio_info = gr.HTML()
                    out_audio = gr.Audio(label="🔊 Jawaban CodeBuddy", autoplay=True)

            btn_audio.click(
                tab_audio_tanya,
                [inp_audio, bahasa_global, inp_level_audio],
                [out_audio, out_audio_info],
            )

            gr.HTML("<hr style='margin:32px 0; border:none; border-top:3px dashed #FFD93D;'>")
            gr.Markdown("## 🔊 Baca Teks Apapun (TTS)")
            gr.HTML('<div class="info-box-kid">Tulis kalimat apa saja, AI akan membacanya dengan suara natural Bahasa Indonesia.</div>')

            with gr.Row():
                with gr.Column():
                    inp_tts_teks = gr.Textbox(
                        label="📝 Tulis teks yang mau dibacakan",
                        placeholder="Contoh: Halo, nama saya Budi. Saya senang belajar coding!",
                        lines=4,
                    )
                    inp_tts_gender = gr.Radio(
                        ["female", "male"],
                        value="female",
                        label="👤 Jenis Suara",
                    )
                    btn_tts = gr.Button("🔊 Baca!", variant="primary", size="lg")
                with gr.Column():
                    out_tts_info = gr.HTML()
                    out_tts = gr.Audio(label="🎵 Suara")

            btn_tts.click(tab_tts_baca, [inp_tts_teks, bahasa_global, inp_tts_gender], [out_tts, out_tts_info])

        # ═══ TAB 4: LATIHAN ═════════════════════════════════════════════ #
        with gr.Tab("📚 Latihan"):
            gr.HTML('<div class="info-box-kid">📖 <b>Yuk latihan coding!</b> Pilih dari latihan yang ada, atau biar AI buat latihan baru sesuai topik favoritmu.</div>')

            gr.Markdown("## 📋 Pilih Latihan")
            with gr.Row():
                inp_diff_list = gr.Dropdown(
                    ["semua", "beginner", "intermediate", "advanced"],
                    value="beginner", label="🌱 Tingkat", scale=3,
                )
                btn_list = gr.Button("🔍 Tampilkan", variant="primary", scale=1)

            out_list = gr.HTML('<div class="info-box-kid">👆 Klik tombol "Tampilkan" untuk lihat daftar latihan</div>')
            btn_list.click(tab_latihan_list, [inp_diff_list], [out_list])

            gr.HTML("<hr style='margin:32px 0; border:none; border-top:3px dashed #FFD93D;'>")
            gr.Markdown("## ✨ Buat Latihan Baru dengan AI")

            with gr.Row():
                inp_topik = gr.Textbox(
                    label="🎯 Topik (apa saja!)",
                    placeholder="warung, sepak bola, layangan, hewan, makanan...",
                    scale=3,
                )
                inp_diff_gen = gr.Dropdown(
                    ["beginner", "intermediate", "advanced"],
                    value="beginner", label="Tingkat", scale=1,
                )

            btn_gen = gr.Button("🎲 Generate Latihan!", variant="primary", size="lg")

            out_gen_status = gr.HTML()
            with gr.Row():
                with gr.Column():
                    out_title = gr.Textbox(label="📌 Judul")
                    out_instr = gr.Textbox(label="📝 Instruksi", lines=5)
                with gr.Column():
                    out_starter = gr.Code(label="🐍 Kode Awal", language="python", lines=10)

            btn_gen.click(
                tab_generate_latihan,
                [inp_topik, inp_diff_gen, bahasa_global],
                [out_title, out_instr, out_starter, out_gen_status],
            )

        # ═══ TAB 5: SISWA ═══════════════════════════════════════════════ #
        with gr.Tab("👤 Siswa"):
            gr.HTML('<div class="info-box-kid">👤 <b>Daftar dulu yuk!</b> Biar progressmu tersimpan dan bisa lihat perkembangan belajarmu.</div>')

            with gr.Row():
                with gr.Column():
                    gr.Markdown("## ➕ Daftar Siswa Baru")
                    inp_nama = gr.Textbox(label="👤 Nama Lengkap", placeholder="Budi Santoso")
                    with gr.Row():
                        inp_usia = gr.Textbox(label="🎂 Usia", placeholder="10", scale=1)
                        inp_level_reg = gr.Dropdown(
                            ["beginner", "intermediate", "advanced"],
                            value="beginner", label="Level", scale=2,
                        )
                    btn_daftar = gr.Button("✅ Daftar!", variant="primary", size="lg")
                    out_daftar = gr.HTML()
                    btn_daftar.click(tab_daftar_siswa, [inp_nama, inp_usia, inp_level_reg], [out_daftar])

                with gr.Column():
                    gr.Markdown("## 📊 Lihat Progressku")
                    inp_sid_prog = gr.Textbox(label="🆔 ID-mu", placeholder="1")
                    btn_prog = gr.Button("📈 Lihat", variant="primary", size="lg")
                    out_prog = gr.HTML()
                    btn_prog.click(tab_progres_siswa, [inp_sid_prog], [out_prog])

        # ═══ TAB 6: GURU ════════════════════════════════════════════════ #
        with gr.Tab("👨‍🏫 Mode Guru"):
            gr.HTML('''
            <div class="info-box-kid">
                <b>👨‍🏫 Untuk Bapak/Ibu Guru</b><br>
                Pantau seluruh siswa dalam satu pandangan. Gemma 4 menganalisis pola kelas dan memberi saran pengajaran.
            </div>
            ''')

            with gr.Tabs():
                with gr.Tab("📊 Dashboard"):
                    btn_dashboard = gr.Button("🔄 Refresh Dashboard", variant="primary", size="lg")
                    out_dashboard = gr.HTML()
                    btn_dashboard.click(tab_guru_dashboard, [], [out_dashboard])

                with gr.Tab("🤖 AI Insight"):
                    gr.HTML('<div class="info-box-kid">Gemma 4 menganalisis kelas dan memberi <b>saran konkret</b> untuk pelajaran berikutnya.</div>')
                    btn_insight = gr.Button("🧠 Generate AI Insight", variant="primary", size="lg")
                    out_insight = gr.HTML()
                    btn_insight.click(tab_guru_insight, [], [out_insight])

    # ── FOOTER ──────────────────────────────────────────────────────── #
    gr.HTML("""
    <div class="kid-footer">
        <div style="font-size:1.4rem; font-weight:800; color:#FF6B9D; margin-bottom:12px;">
            🇮🇩 Untuk Setiap Anak Indonesia 🇮🇩
        </div>
        <div style="font-size:1rem;">
            <b>Google Gemma 4 Good Hackathon 2026</b><br>
            <i>"Setiap anak Indonesia berhak belajar coding, tidak peduli di mana mereka tinggal."</i>
        </div>
    </div>
    """)


if __name__ == "__main__":
    # Theme dan CSS pindah ke launch() di Gradio 6.0
    theme = gr.themes.Soft(
        primary_hue="orange",
        secondary_hue="pink",
        neutral_hue="slate",
    )
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=theme,
        css=CUSTOM_CSS,
        head=HEAD_FORCE_LIGHT,
    )
