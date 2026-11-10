---
title: CodeBuddy
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.15.1
python_version: "3.12"
app_file: app.py
pinned: true
short_description: AI coding tutor for Indonesian students — interactive demo
license: apache-2.0
tags:
  - education
  - indonesia
  - gradio
  - gemma
  - coding-tutor
---

# CodeBuddy

Interactive demo of an AI coding tutor for Indonesian students.

Create this public Space as a **Gradio Space with ZeroGPU hardware** (flavor `zero-a10g`). Do not use CPU Basic and do not use Docker: new Gradio and Docker Spaces on cpu-basic now require a Hugging Face PRO plan. ZeroGPU is only how the Space is hosted; this demo does not run Gemma, Whisper, or TTS on the GPU.

This Space is the hosted interactive demo on free ZeroGPU hardware. It shows a curated Bahasa Indonesia tutoring session: a handwritten-code sample, feedback for the missing colon after `for n in nilai`, a simple exercise, teacher insight, and a voice transcript. Code execution and the student database stay live.

The full Gemma 4 Vision tutor, including offline OCR and voice, runs on your own computer with Ollama. Follow [RUN.md](https://github.com/adindamochamad/codebuddy/blob/main/RUN.md) in the GitHub repo. This Space is not a 100% offline deployment.

- Source: https://github.com/adindamochamad/codebuddy
- Demo video: https://youtu.be/cryfk0U81hk

Photo Scan "Try Demo" loads `frontend/assets/demo_handwriting.jpg`.

## Later deploy (do not run from this README)

Copy these into the Space repo:

- `spaces/README.md` → Space `README.md`
- `spaces/app.py` → Space `app.py`
- `spaces/requirements.txt` → Space `requirements.txt`
- the `backend/` and `frontend/` trees

Do not copy the GitHub root `Dockerfile` or `spaces/Dockerfile`. The public Space is Gradio + ZeroGPU, not the Docker path (that Dockerfile remains for optional self-host or a future PRO Docker deploy).

`spaces/app.py` sets `CODEBUDDY_SPACE_DEMO=1` itself. A Space variable with the same name is optional, not a secret. Do not add tokens, `.env` files, or model credentials.
