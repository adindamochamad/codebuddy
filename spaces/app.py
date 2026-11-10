"""Hugging Face Gradio Space entrypoint.

Copied to the Space repo root as app.py. Starts FastAPI on 127.0.0.1:8000,
then launches the existing Gradio Blocks. Demo results come from
CODEBUDDY_SPACE_DEMO=1 — this file does not load Gemma, Whisper, or TTS.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import spaces


def _repo_root() -> Path:
    """GitHub: spaces/app.py. Space: /app.py next to backend/."""
    here = Path(__file__).resolve().parent
    if (here / "backend").is_dir():
        return here
    parent = here.parent
    if (parent / "backend").is_dir():
        return parent
    raise RuntimeError(
        "Tidak menemukan folder backend/ di samping atau di atas app.py. "
        "Salin spaces/app.py ke akar Space bersama pohon backend/ dan frontend/."
    )


_ROOT = _repo_root()
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT / "frontend"))

os.environ.setdefault("CODEBUDDY_SPACE_DEMO", "1")
os.environ.setdefault("CODEBUDDY_API", "http://127.0.0.1:8000")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:////tmp/codebuddy-data/codebuddy.db",
)

_HEALTH = "http://127.0.0.1:8000/health"
_HEALTH_TRIES = 60
_API_LOG = Path("/tmp/codebuddy-api.log")


@spaces.GPU(duration=15)
def _zero_gpu_placeholder() -> None:
    """Unused. Present so this Gradio Space can be created on ZeroGPU hardware."""
    return None


def _wait_backend() -> None:
    last_error = "tidak ada respons"
    for _ in range(_HEALTH_TRIES):
        try:
            with urllib.request.urlopen(_HEALTH, timeout=2) as resp:
                if resp.status == 200:
                    return
                last_error = f"HTTP {resp.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc) or type(exc).__name__
        time.sleep(1)
    raise RuntimeError(
        f"Backend FastAPI tidak siap di {_HEALTH} setelah {_HEALTH_TRIES} detik "
        f"({last_error}). Cek {_API_LOG}."
    )


def _start_backend() -> None:
    Path("/tmp/codebuddy-data").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    backend = str(_ROOT / "backend")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = backend if not existing else backend + os.pathsep + existing
    log = open(_API_LOG, "ab", buffering=0)
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(_ROOT),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def _load_frontend_demo():
    path = _ROOT / "frontend" / "app.py"
    spec = importlib.util.spec_from_file_location("codebuddy_frontend", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Tidak bisa memuat Gradio Blocks dari {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["codebuddy_frontend"] = module
    spec.loader.exec_module(module)
    blok = getattr(module, "demo", None)
    if blok is None:
        raise RuntimeError("frontend/app.py tidak mengekspor objek demo")
    return blok, module


_start_backend()
_wait_backend()
demo, _frontend = _load_frontend_demo()

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    show_error=True,
    theme=_frontend.gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="violet",
        neutral_hue="slate",
    ),
    css=_frontend.dapatkan_css_gradi(),
    head=_frontend.FORCE_LIGHT_JS,
    allowed_paths=[
        str(_ROOT / "frontend" / "assets"),
        str(Path(tempfile.gettempdir()) / "codebuddy_demo"),
    ],
)
