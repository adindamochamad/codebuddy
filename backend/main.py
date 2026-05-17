"""Entry point FastAPI CodeBuddy."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import router as router_utama
from api.schemas import ResponsKesehatan
from api.teacher import router as router_guru
from utils.config import pengaturan
from utils.database import init_db
from utils.pembatas_kueri import pembatas_per_ip


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Inisialisasi DB saat startup."""
    await init_db()
    yield


app = FastAPI(
    title=pengaturan.nama_aplikasi,
    description=(
        "API tutor pemrograman Python dengan OCR tulisan tangan, "
        "sandbox eksekusi, dan LLM lokal via Ollama."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting state dan error handler
app.state.limiter = pembatas_per_ip
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS dengan daftar origin spesifik
app.add_middleware(
    CORSMiddleware,
    allow_origins=pengaturan.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_utama, prefix="/api")
app.include_router(router_guru, prefix="/api")


@app.get("/health", response_model=ResponsKesehatan, tags=["health"])
async def cek_kesehatan() -> ResponsKesehatan:
    """Probe kesehatan untuk load balancer dan demo hackathon."""
    return ResponsKesehatan()


@app.get("/", tags=["root"])
async def akar() -> dict[str, str]:
    return {"docs": "/docs", "health": "/health"}
