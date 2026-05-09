"""Fixture pytest bersama — DB test, HTTP client, dan mock helpers."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Harus dijalankan sebelum `main` diimpor agar engine pakai DB test (file)
_folder_uji = Path(__file__).resolve().parent
_jalur_db_uji = _folder_uji / "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_jalur_db_uji}"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from models.database import Basis


# --------------------------------------------------------------------------- #
# HTTP Client                                                                  #
# --------------------------------------------------------------------------- #

@pytest.fixture
def klien_http() -> Generator[TestClient, None, None]:
    """Klien HTTP sinkron Starlette/httpx untuk endpoint API."""
    with TestClient(app) as klien:
        yield klien


# --------------------------------------------------------------------------- #
# In-memory DB (terisolasi per fungsi test)                                   #
# --------------------------------------------------------------------------- #

@pytest.fixture
async def mem_db() -> AsyncGenerator[AsyncSession, None]:
    """Sesi SQLAlchemy async dengan SQLite in-memory, fresh per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Basis.metadata.create_all)

    async with factory() as sesi:
        yield sesi

    await engine.dispose()


# --------------------------------------------------------------------------- #
# Data fixtures                                                                #
# --------------------------------------------------------------------------- #

@pytest.fixture
def kode_python_valid() -> str:
    return "x = 10\nprint(x * 2)"


@pytest.fixture
def kode_python_syntax_error() -> str:
    return "def f("


@pytest.fixture
def kode_python_runtime_error() -> str:
    return "print(variabel_belum_ada)"


# --------------------------------------------------------------------------- #
# Mock LLM helpers                                                             #
# --------------------------------------------------------------------------- #

@pytest.fixture
def ai_feedback_sukses() -> dict[str, Any]:
    return {
        "understanding": "Kode mencetak hasil perkalian",
        "errors": [],
        "suggestions": ["Gunakan f-string untuk output yang lebih rapi"],
        "corrected_code": "x = 10\nprint(f'Hasil: {x * 2}')",
        "encouragement": "Bagus sekali! Terus semangat belajar!",
    }


@pytest.fixture
def ai_feedback_error() -> dict[str, Any]:
    return {
        "understanding": "Kode mencoba mencetak variabel yang belum ada",
        "errors": [{"line": 1, "explanation": "Variabel belum didefinisikan", "fix": "x = 10"}],
        "suggestions": ["Pastikan variabel sudah diberi nilai sebelum dipakai"],
        "corrected_code": "x = 10\nprint(x)",
        "encouragement": "Jangan menyerah, ini kesalahan yang umum!",
    }


def buat_mock_llm(feedback: dict[str, Any]) -> MagicMock:
    """Buat GemmaService mock yang mengembalikan feedback tertentu."""
    mock = MagicMock()
    mock.analyze_code = AsyncMock(return_value=feedback)
    mock.generate_exercise = AsyncMock(return_value={
        "title": "Latihan Loop",
        "instructions": "Cetak angka 1 sampai 5",
        "starter_code": "for i in range(5):\n    pass",
        "solution": "for i in range(1, 6):\n    print(i)",
        "test_cases": [{"input": None, "expected_output": "1\n2\n3\n4\n5", "description": "Berurutan"}],
    })
    return mock
