"""Endpoint OCR ekstraksi dari gambar."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from api.schemas import ResponsOCR
from services.ocr_service import LayananOCRError, ekstrak_teks_dari_gambar

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post(
    "/extract",
    response_model=ResponsOCR,
    summary="Ekstrak teks kode dari gambar (PaddleOCR)",
)
async def ekstrak_gambar(
    berkas: UploadFile = File(..., description="Gambar tulisan tangan / screenshot kode"),
    bahasa: str = "en",
) -> ResponsOCR:
    """Membaca bytes gambar dan mengembalikan teks yang dikenali."""
    if not berkas.content_type or not berkas.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unggah berkas bertipe image/*.",
        )

    try:
        isi = await berkas.read()
        hasil = await ekstrak_teks_dari_gambar(isi, bahasa=bahasa)
    except LayananOCRError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 — lapisan HTTP membungkus error OCR tak terduga
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses OCR: {exc}",
        ) from exc

    return ResponsOCR(**hasil)
