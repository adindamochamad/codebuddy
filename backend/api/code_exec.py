"""Endpoint eksekusi kode aman."""

from fastapi import APIRouter

from api.schemas import PermintaanEksekusiKode, ResponsEksekusiKode
from services.executor_service import jalankan_kode_terbatas
from utils.config import pengaturan

router = APIRouter(prefix="/code", tags=["code"])


@router.post(
    "/execute",
    response_model=ResponsEksekusiKode,
    summary="Jalankan Python dengan RestrictedPython",
)
async def eksekusi_kode(payload: PermintaanEksekusiKode) -> ResponsEksekusiKode:
    """Menjalankan kode pengguna dalam sandbox terbatas."""
    hasil = await jalankan_kode_terbatas(
        payload.kode,
        panjang_maks=pengaturan.kode_maksimal_panjang,
    )
    return ResponsEksekusiKode(**hasil)
