"""Demo data untuk one-click demo mode di CodeBuddy.

File ini berisi contoh-contoh data yang sudah diisi sebelumnya untuk setiap tab,
sehingga judge atau user baru bisa langsung mencoba fitur tanpa harus setup manual.
"""

import shutil
import tempfile
from pathlib import Path

# Path ke gambar demo
_DEMO_IMAGE_SOURCE = Path(__file__).parent.parent / "Test Pic OCR" / "Pic1.jpeg"

def get_demo_image_path():
    """Copy demo image ke temp directory untuk Gradio security."""
    if not _DEMO_IMAGE_SOURCE.exists():
        return None
    
    # Copy ke temp directory
    temp_dir = Path(tempfile.gettempdir()) / "codebuddy_demo"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file = temp_dir / "demo_handwriting.jpg"
    shutil.copy2(_DEMO_IMAGE_SOURCE, temp_file)
    
    return str(temp_file)

# ============================================================================ #
# Demo Data untuk setiap Tab
# ============================================================================ #

# Tab 1: OCR Demo
DEMO_OCR = {
    "expected_code": """# Contoh kode yang akan diekstrak
for i in range(5):
    print("Halo", i)
"""
}
# Note: Image path di-generate dynamically via get_demo_image_path()

# Tab 2: AI Tutor Demo - Contoh kode dengan error umum
DEMO_TUTOR = {
    "code_with_error": """# Program hitung rata-rata
nilai = [85, 90, 75, 88]
total = 0

for n in nilai
    total = total + n

rata = total / len(nilai)
print("Rata-rata:", rata)
""",
    "code_success": """# Program sapa nama
nama = input("Siapa namamu? ")
umur = int(input("Berapa umurmu? "))

print(f"Halo {nama}!")
print(f"Kamu berumur {umur} tahun")

if umur < 12:
    print("Kamu masih anak-anak")
else:
    print("Kamu sudah remaja")
""",
    "student_id": "1",
    "level": "beginner",
    "exercise_id": "",
}

# Tab 3: Voice Mode - Contoh teks untuk TTS
DEMO_VOICE = {
    "tts_text": """Halo! Saya CodeBot, teman belajar coding kamu. 
    
Aku bisa membantu kamu memahami error di kode Python, menjelaskan konsep programming dengan cara yang mudah dipahami, dan memberikan petunjuk step-by-step tanpa langsung memberikan jawaban.

Mari belajar coding bersama!""",
    "gender": "female",
}

# Tab 4: Exercise - Contoh topik untuk generate exercise
DEMO_EXERCISE = {
    "topic": "membuat kalkulator sederhana",
    "difficulty": "Beginner",
    "browse_difficulty": "Beginner",
}

# Tab 5: Student - Contoh data siswa
DEMO_STUDENT = {
    "register": {
        "name": "Andi Pratama",
        "age": "10",
        "level": "beginner",
    },
    "progress_student_id": "1",
}

# ============================================================================ #
# Contoh Code Snippets untuk Quick Examples
# ============================================================================ #

CODE_EXAMPLES = {
    "hello_world": """# Program Hello World pertamaku
print("Halo Dunia!")
print("Nama saya Andi")
print("Saya belajar Python")
""",
    
    "loop_basic": """# Menghitung 1 sampai 10
for angka in range(1, 11):
    print("Angka:", angka)
""",
    
    "loop_error": """# Error: lupa titik dua
for i in range(5)
    print(i)
""",
    
    "input_output": """# Program tanya jawab
nama = input("Siapa namamu? ")
umur = input("Berapa umurmu? ")

print("Halo", nama)
print("Umur kamu", umur, "tahun")
""",
    
    "conditional": """# Cek bilangan genap atau ganjil
angka = 7

if angka % 2 == 0:
    print("Genap")
else:
    print("Ganjil")
""",
    
    "list_basic": """# Bermain dengan list
buah = ["apel", "jeruk", "mangga"]

print("Buah pertama:", buah[0])
print("Semua buah:", buah)
print("Jumlah buah:", len(buah))
""",
    
    "function_basic": """# Membuat fungsi sederhana
def sapa(nama):
    print(f"Halo {nama}!")
    print("Selamat belajar Python!")

sapa("Andi")
sapa("Siti")
""",
}

# ============================================================================ #
# Onboarding Messages
# ============================================================================ #

ONBOARDING_MESSAGES = {
    "welcome": {
        "title": "Selamat Datang di CodeBuddy! 🤖",
        "content": """
        <p>Hai! Saya <strong>CodeBot</strong>, asisten AI yang siap membantu kamu belajar Python.</p>
        
        <div style="margin: 16px 0; padding: 12px; background: var(--c-indigo-pale); border-radius: 8px;">
            <strong>✨ Apa yang bisa saya bantu?</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                <li>📸 Membaca kode dari tulisan tanganmu</li>
                <li>🎓 Menjelaskan error dan memberikan petunjuk</li>
                <li>🎤 Menjawab pertanyaan dengan suara</li>
                <li>📚 Membuat latihan sesuai levelmu</li>
                <li>🌍 Berbicara dalam 5 bahasa daerah</li>
            </ul>
        </div>
        
        <p style="margin-top: 12px;">
            <strong>💡 Tips:</strong> Di setiap tab, klik tombol <strong>"📺 Try Demo"</strong> 
            untuk melihat contoh dan mencoba fitur dengan data yang sudah disiapkan.
        </p>
        """,
    },
    
    "ocr_tab": {
        "title": "📸 Photo Scan - OCR Tulisan Tangan",
        "content": """
        <p>Fitur ini memungkinkan kamu untuk:</p>
        <ul style="margin: 8px 0; padding-left: 20px;">
            <li>📸 Foto kode Python yang ditulis di buku</li>
            <li>🤖 AI Gemma 4 Vision akan membaca tulisan tangan</li>
            <li>✨ Kode langsung bisa di-copy atau dikirim ke AI Tutor</li>
        </ul>
        <p><strong>Klik "Try Demo"</strong> untuk melihat contoh ekstraksi!</p>
        """,
    },
    
    "tutor_tab": {
        "title": "🎓 AI Tutor - Bimbingan Step-by-Step",
        "content": """
        <p>AI Tutor akan:</p>
        <ul style="margin: 8px 0; padding-left: 20px;">
            <li>✅ Mengecek syntax kode kamu</li>
            <li>▶️ Menjalankan kode di sandbox aman</li>
            <li>🔍 Menganalisis error yang terjadi</li>
            <li>💡 Memberikan feedback yang membantu kamu berpikir sendiri</li>
        </ul>
        <p><strong>Klik "Try Demo"</strong> untuk melihat analisis kode!</p>
        """,
    },
    
    "voice_tab": {
        "title": "🎤 Mode Suara - Belajar Tanpa Mengetik",
        "content": """
        <p>Mode suara cocok untuk:</p>
        <ul style="margin: 8px 0; padding-left: 20px;">
            <li>🗣️ Bertanya langsung dengan suara</li>
            <li>👂 Mendengarkan penjelasan AI</li>
            <li>📖 Siswa yang belum lancar baca tulis</li>
        </ul>
        <p><strong>Klik "Try Demo"</strong> untuk dengar suara CodeBot!</p>
        """,
    },
}

# ============================================================================ #
# UI Messages & Labels
# ============================================================================ #

DEMO_BUTTON_LABEL = "📺 Try Demo"
DEMO_INFO_MESSAGE = "Demo mode aktif - data sudah diisi otomatis. Kamu bisa edit atau langsung klik tombol!"
