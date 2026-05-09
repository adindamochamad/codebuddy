"""Wrapper async untuk SafeCodeExecutor — dipakai oleh api/code_exec.py."""

from __future__ import annotations

import asyncio
from typing import Any

from services.code_executor import safe_executor


async def jalankan_kode_terbatas(kode_sumber: str, panjang_maks: int) -> dict[str, Any]:
    """Jalankan kode di sandbox dan kembalikan hasil dengan field nama Indonesia.

    Memanggil SafeCodeExecutor.execute() di thread pool agar tidak blok event loop.

    Returns:
        Dict dengan kunci: sukses, stdout, stderr, error_kind.
    """
    if len(kode_sumber) > panjang_maks:
        return {
            "sukses": False,
            "stdout": "",
            "stderr": f"Kode melebihi batas {panjang_maks} karakter.",
            "error_kind": "ValidationError",
        }
    hasil = await asyncio.to_thread(safe_executor.execute, kode_sumber)

    return {
        "sukses": hasil["success"],
        "stdout": hasil["output"],
        "stderr": hasil["error"] or "",
        "error_kind": hasil["error_type"],
    }
