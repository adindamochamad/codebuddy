"""Model ORM SQLAlchemy untuk CodeBuddy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Basis(DeclarativeBase):
    """Basis deklaratif SQLAlchemy 2.x — semua model mewarisi kelas ini."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =========================================================================== #
# Student                                                                      #
# =========================================================================== #

class Student(Basis):
    """Peserta didik yang menggunakan CodeBuddy."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(64), nullable=False, default="beginner")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    submissions: Mapped[list["CodeSubmission"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="select",
    )
    progress_records: Mapped[list["Progress"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="select",
    )


# =========================================================================== #
# CodeSubmission                                                               #
# =========================================================================== #

class CodeSubmission(Basis):
    """Satu pengiriman kode oleh siswa (teks langsung atau hasil OCR)."""

    __tablename__ = "code_submissions"

    __table_args__ = (
        # Index untuk query cepat per siswa
        Index("ix_submissions_student_id", "student_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    # errors disimpan sebagai JSON array: [{type, message, line}, ...]
    errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    fixed_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="submissions")


# =========================================================================== #
# Progress                                                                     #
# =========================================================================== #

class Progress(Basis):
    """Kemajuan per latihan untuk satu siswa."""

    __tablename__ = "progress"

    __table_args__ = (
        # Index composite untuk upsert cepat (student_id + exercise_id)
        Index("ix_progress_student_exercise", "student_id", "exercise_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(String(128), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_attempt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    student: Mapped["Student"] = relationship(back_populates="progress_records")
