"""Uji sandbox RestrictedPython — executor_service wrapper."""

from services.executor_service import jalankan_kode_terbatas


async def test_executor_print_stdout() -> None:
    hasil = await jalankan_kode_terbatas('print("halo")', panjang_maks=500)
    assert hasil["sukses"] is True
    assert "halo" in hasil["stdout"]


async def test_executor_syntax_error() -> None:
    hasil = await jalankan_kode_terbatas("!!!", panjang_maks=500)
    assert hasil["sukses"] is False
    assert hasil["error_kind"] == "SyntaxError"   # nama exception, bukan kategori


async def test_executor_panjang_maks() -> None:
    hasil = await jalankan_kode_terbatas("x = 1", panjang_maks=3)
    assert hasil["sukses"] is False
