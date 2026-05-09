"""Sandbox eksekusi kode Python aman menggunakan RestrictedPython."""

from __future__ import annotations

import logging
import re
import threading
import time
import warnings
from typing import Any, Optional

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import (
    full_write_guard,
    guarded_iter_unpack_sequence,
    safer_getattr,
)
from RestrictedPython.PrintCollector import PrintCollector

logger = logging.getLogger(__name__)

_TIMEOUT_DEFAULT = 5       # detik
_MAX_CODE_LENGTH = 8_000   # karakter
_MAX_OUTPUT_LENGTH = 5_000  # karakter output maksimal


class SafeCodeExecutor:
    """Eksekutor kode Python terbatas dan aman untuk tutor pemula.

    Fitur keamanan:
    - Hanya built-in yang diperlukan yang diizinkan.
    - Import, file I/O, jaringan, dan sistem diblokir.
    - Timeout 5 detik mencegah infinite loop.
    - Output dibatasi 5.000 karakter.

    Contoh::

        executor = SafeCodeExecutor()

        # Kode valid
        hasil = executor.execute('print("halo")')
        # {'success': True, 'output': 'halo\\n', 'error': None, ...}

        # Kode dengan error
        hasil = executor.execute('print(x)')
        # {'success': False, 'error': "Variabel 'x' belum didefinisikan", ...}

        # Cek syntax saja
        cek = executor.validate_syntax('def f(')
        # {'valid': False, 'error': 'Syntax Error di baris 1: ...', 'line': 1}
    """

    def __init__(
        self,
        timeout: float = _TIMEOUT_DEFAULT,
        max_code_length: int = _MAX_CODE_LENGTH,
    ) -> None:
        self.timeout = timeout
        self.max_code_length = max_code_length

    # ----------------------------------------------------------------------- #
    # Public API                                                               #
    # ----------------------------------------------------------------------- #

    def execute(self, code: str) -> dict[str, Any]:
        """Jalankan kode Python dalam sandbox terbatas.

        Args:
            code: Kode Python yang akan dieksekusi.

        Returns:
            Dict dengan kunci:
            - ``success``        : bool — berhasil tanpa error
            - ``output``         : str  — hasil print / stdout
            - ``error``          : str | None — pesan error dalam Bahasa Indonesia
            - ``error_type``     : str | None — nama tipe exception (SyntaxError, dst.)
            - ``execution_time`` : float — waktu eksekusi dalam detik
        """
        mulai = time.perf_counter()

        if len(code) > self.max_code_length:
            return self._hasil_error(
                f"Kode terlalu panjang (maks {self.max_code_length} karakter).",
                "ValidationError",
                mulai,
            )

        # Cek syntax dulu — lebih cepat daripada compile RestrictedPython
        cek_syntax = self.validate_syntax(code)
        if not cek_syntax["valid"]:
            return self._hasil_error(
                cek_syntax["error"] or "Syntax tidak valid.",
                "SyntaxError",
                mulai,
            )

        # Kompilasi dengan RestrictedPython
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                bytecode = compile_restricted(code, filename="<kode_siswa>", mode="exec")
            except SyntaxError as exc:
                pesan = f"Syntax Error di baris {exc.lineno}: {exc.msg}"
                return self._hasil_error(pesan, "SyntaxError", mulai)

        if bytecode is None:
            logger.warning("RestrictedPython menolak kode: %.100s", code)
            return self._hasil_error(
                "Kode mengandung operasi yang tidak diizinkan oleh sandbox.",
                "SecurityError",
                mulai,
            )

        # Eksekusi dengan timeout via daemon thread + Event
        # Daemon thread tidak mencegah proses Python keluar (aman untuk pytest)
        holder: dict[str, Any] = {}
        selesai = threading.Event()

        def _jalankan() -> None:
            holder["result"] = self._jalankan_bytecode(bytecode)
            selesai.set()

        t = threading.Thread(target=_jalankan, daemon=True)
        t.start()

        if selesai.wait(timeout=self.timeout):
            hasil = holder["result"]
        else:
            logger.warning("Timeout eksekusi kode setelah %.1fs.", self.timeout)
            return self._hasil_error(
                f"Kode terlalu lama dijalankan (timeout {int(self.timeout)} detik). "
                "Cek apakah ada infinite loop.",
                "TimeoutError",
                mulai,
            )

        hasil["execution_time"] = round(time.perf_counter() - mulai, 4)
        return hasil

    def validate_syntax(self, code: str) -> dict[str, Any]:
        """Cek syntax kode Python tanpa mengeksekusinya.

        Args:
            code: Kode Python yang akan dicek.

        Returns:
            Dict dengan kunci:
            - ``valid`` : bool
            - ``error`` : str | None — pesan error dalam Bahasa Indonesia
            - ``line``  : int | None — nomor baris bermasalah
        """
        try:
            compile(code, "<kode_siswa>", "exec")
            return {"valid": True, "error": None, "line": None}
        except SyntaxError as exc:
            pesan = f"Syntax Error di baris {exc.lineno}: {exc.msg}"
            return {"valid": False, "error": pesan, "line": exc.lineno}
        except ValueError as exc:
            # Terjadi pada null bytes dll.
            return {"valid": False, "error": f"Kode tidak valid: {exc}", "line": None}

    # ----------------------------------------------------------------------- #
    # Globals sandbox                                                          #
    # ----------------------------------------------------------------------- #

    @staticmethod
    def _buat_globals() -> dict[str, Any]:
        """Buat namespace globals yang dibatasi untuk eksekusi sandbox."""
        return {
            "__builtins__": {
                # Konstanta
                "None": None,
                "True": True,
                "False": False,
                # Tipe data dasar
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "bytes": bytes,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "frozenset": frozenset,
                # Fungsi matematika
                "abs": abs,
                "divmod": divmod,
                "pow": pow,
                "round": round,
                # Fungsi agregat & iterasi
                "len": len,
                "sum": sum,
                "min": min,
                "max": max,
                "sorted": sorted,
                "reversed": reversed,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "all": all,
                "any": any,
                # Representasi & konversi
                "repr": repr,
                "format": format,
                "chr": chr,
                "ord": ord,
                "hex": hex,
                "oct": oct,
                "bin": bin,
                # Pengecekan tipe
                "isinstance": isinstance,
                "issubclass": issubclass,
                "type": type,
                "callable": callable,
                "hash": hash,
                "id": id,
                # Exception yang boleh di-raise/catch oleh siswa
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "IndexError": IndexError,
                "KeyError": KeyError,
                "AttributeError": AttributeError,
                "StopIteration": StopIteration,
                "ZeroDivisionError": ZeroDivisionError,
                "OverflowError": OverflowError,
                "RuntimeError": RuntimeError,
                "NotImplementedError": NotImplementedError,
                # DIBLOKIR: open, exec, eval, compile, __import__, os, sys, dll.
            },
            # Hook RestrictedPython
            "_print_": PrintCollector,
            "_getiter_": iter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_getitem_": lambda obj, key: obj[key],
            "_getattr_": safer_getattr,
            "_write_": full_write_guard,
            "_inplacevar_": _inplace_guard,
        }

    # ----------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ----------------------------------------------------------------------- #

    def _jalankan_bytecode(self, bytecode: Any) -> dict[str, Any]:
        """Jalankan bytecode dalam globals terbatas (dipanggil dari thread pool)."""
        globs = self._buat_globals()
        try:
            exec(bytecode, globs, globs)  # noqa: S102 — RestrictedPython sandbox
        except Exception as exc:  # noqa: BLE001
            printer = globs.get("_print")
            output_sebagian = _ambil_output(printer)
            pesan, tipe = self._terjemahkan_error(exc)
            logger.info("Runtime error [%s]: %s", tipe, pesan)
            return {
                "success": False,
                "output": _potong_output(output_sebagian),
                "error": pesan,
                "error_type": tipe,
                "execution_time": 0.0,
            }

        printer = globs.get("_print")
        output = _ambil_output(printer)
        return {
            "success": True,
            "output": _potong_output(output),
            "error": None,
            "error_type": None,
            "execution_time": 0.0,
        }

    @staticmethod
    def _terjemahkan_error(exc: Exception) -> tuple[str, str]:
        """Terjemahkan exception Python ke pesan Bahasa Indonesia.

        Returns:
            Tuple (pesan_indonesia, nama_tipe_exception).
        """
        tipe = type(exc).__name__
        pesan_asli = str(exc)

        if isinstance(exc, NameError):
            cocok = re.search(r"name '(.+?)' is not defined", pesan_asli)
            var = cocok.group(1) if cocok else pesan_asli
            return f"Variabel '{var}' belum didefinisikan. Pastikan sudah memberi nilai sebelum digunakan.", tipe

        if isinstance(exc, TypeError):
            # Coba sederhanakan pesan TypeError yang panjang
            if "unsupported operand" in pesan_asli:
                return f"Tipe data tidak cocok untuk operasi ini: {pesan_asli}", tipe
            if "argument" in pesan_asli:
                return f"Jumlah atau tipe argumen salah: {pesan_asli}", tipe
            return f"Tipe data salah: {pesan_asli}", tipe

        if isinstance(exc, ZeroDivisionError):
            return "Tidak bisa dibagi nol (pembagian dengan 0).", tipe

        if isinstance(exc, IndexError):
            return f"Indeks di luar jangkauan: {pesan_asli}. Cek panjang list/string.", tipe

        if isinstance(exc, KeyError):
            return f"Kunci '{pesan_asli}' tidak ditemukan dalam dictionary.", tipe

        if isinstance(exc, ValueError):
            return f"Nilai tidak valid: {pesan_asli}", tipe

        if isinstance(exc, AttributeError):
            cocok = re.search(r"'(.+?)' object has no attribute '(.+?)'", pesan_asli)
            if cocok:
                return (
                    f"Tipe '{cocok.group(1)}' tidak punya atribut '{cocok.group(2)}'.",
                    tipe,
                )
            return f"Atribut tidak ditemukan: {pesan_asli}", tipe

        if isinstance(exc, RecursionError):
            return "Rekursi terlalu dalam — cek apakah ada infinite loop atau rekursi tanpa basis.", tipe

        if isinstance(exc, MemoryError):
            return "Memori habis. Kode menggunakan terlalu banyak memori.", tipe

        if isinstance(exc, OverflowError):
            return f"Angka terlalu besar untuk diproses: {pesan_asli}", tipe

        if isinstance(exc, NotImplementedError):
            return "Fitur ini belum diimplementasikan.", tipe

        # Tangkap pelanggaran sandbox RestrictedPython
        if "not allowed" in pesan_asli.lower() or "attribute" in pesan_asli.lower():
            logger.warning("Potensi pelanggaran sandbox: %s — %s", tipe, pesan_asli)
            return f"Operasi ini tidak diizinkan dalam sandbox: {pesan_asli}", "SecurityError"

        return f"{tipe}: {pesan_asli}", tipe

    @staticmethod
    def _hasil_error(
        pesan: str,
        tipe: str,
        mulai: float,
        output: str = "",
    ) -> dict[str, Any]:
        return {
            "success": False,
            "output": output,
            "error": pesan,
            "error_type": tipe,
            "execution_time": round(time.perf_counter() - mulai, 4),
        }


# --------------------------------------------------------------------------- #
# Module-level helpers                                                         #
# --------------------------------------------------------------------------- #

def _inplace_guard(op: str, x: Any, y: Any) -> Any:
    """Guard untuk operasi in-place (+=, -=, dll.) agar tetap aman."""
    _ops: dict[str, Any] = {
        "+=": lambda a, b: a + b,
        "-=": lambda a, b: a - b,
        "*=": lambda a, b: a * b,
        "/=": lambda a, b: a / b,
        "//=": lambda a, b: a // b,
        "%=": lambda a, b: a % b,
        "**=": lambda a, b: a ** b,
    }
    fn = _ops.get(op)
    if fn is None:
        raise TypeError(f"Operasi '{op}' tidak diizinkan.")
    return fn(x, y)


def _ambil_output(printer: Any) -> str:
    """Panggil PrintCollector dan kembalikan string output."""
    if callable(printer):
        try:
            return printer()
        except Exception:  # noqa: BLE001
            return ""
    return ""


def _potong_output(output: str) -> str:
    """Potong output yang terlalu panjang agar tidak banjiri response."""
    if len(output) > _MAX_OUTPUT_LENGTH:
        return output[:_MAX_OUTPUT_LENGTH] + f"\n... (output dipotong setelah {_MAX_OUTPUT_LENGTH} karakter)"
    return output


# --------------------------------------------------------------------------- #
# Singleton                                                                    #
# --------------------------------------------------------------------------- #

safe_executor = SafeCodeExecutor()
