from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://c360:c360pass@localhost:5432/complemento360")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_month: Mapped[str] = mapped_column(String(20), index=True)   # e.g. "2026-03"
    minutes: Mapped[int] = mapped_column(Integer)
    user: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[str] = mapped_column(String(100))
    work_item_id: Mapped[str] = mapped_column(String(50))
    work_item_title: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(String(10))
    week: Mapped[str] = mapped_column(String(10))
    type: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str] = mapped_column(Text)
    project: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[str] = mapped_column(String(50))
    parent_title: Mapped[str] = mapped_column(Text)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    date_from: Mapped[str] = mapped_column(String(10))
    date_to: Mapped[str] = mapped_column(String(10))
    recipients: Mapped[str] = mapped_column(Text)        # JSON array as string
    subject: Mapped[str] = mapped_column(Text)
    total_rows: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))      # "success" | "error"
    error: Mapped[str] = mapped_column(Text, default="")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
