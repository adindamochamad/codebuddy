"""Dependency bersama untuk route."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import dapatkan_sesi_db

SesiDatabase = Annotated[AsyncSession, Depends(dapatkan_sesi_db)]
