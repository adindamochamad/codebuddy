"""Endpoint sesi tutor berbasis LLM (Ollama)."""

from fastapi import APIRouter, HTTPException, status

from api.schemas import PermintaanTutor, ResponsTutor
from services.llm_service import LayananLLMError, kirim_chat_tutor

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/tutor",
    response_model=ResponsTutor,
    summary="Sesi tutor agentik (Ollama)",
)
async def sesi_tutor(payload: PermintaanTutor) -> ResponsTutor:
    """
    Mengirim pesan ke model Ollama (mis. Gemma) untuk penjelasan,
    petunjuk langkah demi langkah, atau koreksi konsep.
    """
    riwayat_dict = None
    if payload.riwayat:
        riwayat_dict = [{"role": m.role, "content": m.content} for m in payload.riwayat]

    try:
        hasil = await kirim_chat_tutor(
            payload.pesan,
            konteks_sistem=payload.konteks_sistem,
            riwayat=riwayat_dict,
        )
    except LayananLLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ResponsTutor(reply=hasil["reply"], model=str(hasil["model"]))
