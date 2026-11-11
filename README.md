# CodeBuddy

CodeBuddy is a coding tutor for Indonesian students. It runs Gemma 4 locally through Ollama, executes the student's Python, and explains the result in Indonesian.

A student may only have the program written on paper. CodeBuddy accepts a photograph or pasted source, runs it in a restricted interpreter, and asks the local model for an explanation. After the weights are on disk, that text and vision path does not call a paid model API and does not need a network connection. Prompt text for Indonesian, Javanese Krama, Sundanese, Minangkabau, and Batak Toba is in `backend/services/llm_service.py`.

It was built for the Google Gemma 4 Good Hackathon 2026. Google's results post names it the Future of Education Prize: https://blog.google/innovation-and-ai/technology/developers-tools/winning-entries-gemma-4-good-challenge/

## Install and run

On 11 November 2026 this install was run with Python 3.11. `pip install -r backend/requirements.txt` completed. From `backend/`, `uvicorn main:app --port 8000` answered http://127.0.0.1:8000/health with `{"status":"ok","layanan":"CodeBuddy API"}`. From `frontend/`, `python app.py` served the page at http://127.0.0.1:7860. `ollama serve` and `ollama pull gemma4:e4b` were not run, so a tutoring call was not exercised. The commands match `RUN.md`, `backend/requirements.txt`, and `backend/utils/config.py`.

Requirements: Python 3.10 or newer, and [Ollama](https://ollama.com). The configured model is `gemma4:e4b`. The pull is several gigabytes and needs a network connection once.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

ollama serve
ollama pull gemma4:e4b
```

On Windows, activate `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

From the repository root, with that environment still active, start the API:

```bash
cd backend
uvicorn main:app --port 8000
```

In another terminal, from the repository root:

```bash
source .venv/bin/activate
cd frontend
python app.py
```

Uvicorn listens on http://127.0.0.1:8000. The Gradio page listens on http://127.0.0.1:7860. `docker compose up -d ollama` starts only the Ollama container. The backend service in `docker-compose.yml` is commented out.

## What this does not do

- Spoken replies use `edge-tts`, which is not in `backend/requirements.txt` and which calls Microsoft over the network. Speech-to-text uses `faster-whisper`, also optional, and downloads a model the first time it runs.
- The Hugging Face Space under `spaces/` does not run Gemma, Whisper, or speech synthesis. It is a scripted demo.
- This repository does not report handwriting accuracy.
- This is a hackathon project. It is not a deployed school system.

## License

Apache License 2.0. See `LICENSE`.
