import csv
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import init_db, get_session, TimeEntry
from auth import verify_password, create_token, get_current_user, APP_USER
from email_service import send_report_email
from report_generator import build_excel, build_pdf

REPORTS_DIR = Path(__file__).parent.parent / "reportes_mensuales"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != APP_USER or not verify_password(form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    return {"access_token": create_token(form.username), "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def month_from_filename(filename: str) -> str:
    months = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
    }
    stem = Path(filename).stem.lower()
    parts = stem.split("-")
    if len(parts) == 2:
        mes, anio = parts
        return f"{anio}-{months.get(mes, '00')}"
    return stem


def parse_csv_file(filepath: Path, report_month: str) -> list[dict]:
    rows = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            minutes = int(row["Minutes"]) if row.get("Minutes") else 0
            rows.append({
                "report_month": report_month,
                "minutes": minutes,
                "user": row.get("User", ""),
                "user_id": row.get("User Id", ""),
                "work_item_id": str(row.get("Work Item Id", "")),
                "work_item_title": row.get("Work Item Title", ""),
                "date": (row.get("Date", "") or "")[:10],
                "week": row.get("Week", ""),
                "type": row.get("Type", ""),
                "comment": row.get("Comment", ""),
                "project": row.get("Project", ""),
                "parent_id": str(row.get("Parent Id", "")),
                "parent_title": row.get("Parent Title", ""),
            })
    return rows


def build_summary(rows: list[dict]) -> dict:
    total_minutes = sum(r["minutes"] for r in rows)

    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + r["minutes"]

    by_work_item: dict[str, dict] = {}
    for r in rows:
        key = r["work_item_title"]
        if key not in by_work_item:
            by_work_item[key] = {"title": key, "minutes": 0}
        by_work_item[key]["minutes"] += r["minutes"]

    by_week: dict[str, int] = {}
    for r in rows:
        by_week[r["week"]] = by_week.get(r["week"], 0) + r["minutes"]

    return {
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "by_type": [
            {"type": t, "minutes": m}
            for t, m in sorted(by_type.items(), key=lambda x: -x[1])
        ],
        "by_work_item": sorted(by_work_item.values(), key=lambda x: -x["minutes"]),
        "by_week": [
            {"week": w, "minutes": m}
            for w, m in sorted(by_week.items())
        ],
    }


def entry_to_dict(e: TimeEntry) -> dict:
    return {
        "minutes": e.minutes,
        "user": e.user,
        "work_item_id": e.work_item_id,
        "work_item_title": e.work_item_title,
        "date": e.date,
        "week": e.week,
        "type": e.type,
        "comment": e.comment,
        "project": e.project,
        "parent_id": e.parent_id,
        "parent_title": e.parent_title,
    }


# ---------------------------------------------------------------------------
# Endpoints (protected)
# ---------------------------------------------------------------------------

@app.get("/api/reports")
async def list_reports(
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(TimeEntry.report_month).distinct().order_by(TimeEntry.report_month.desc())
    )
    db_months = {row[0] for row in result.all()}

    month_names = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
    }

    reports = []
    seen_months = set()
    for f in sorted(REPORTS_DIR.glob("*.csv"), reverse=True):
        month = month_from_filename(f.name)
        seen_months.add(month)
        anio, mes = (month.split("-") + ["00"])[:2]
        reports.append({
            "filename": f.name,
            "month": month,
            "label": f"{month_names.get(mes, mes)} {anio}",
            "in_db": month in db_months,
        })

    for m in sorted(db_months, reverse=True):
        if m not in seen_months:
            anio, mes = (m.split("-") + ["00"])[:2]
            reports.append({"filename": None, "month": m, "label": f"{month_names.get(mes, mes)} {anio}", "in_db": True})

    return reports


@app.post("/api/reports/{filename}/import")
async def import_report(
    filename: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    if not filename.endswith(".csv") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    report_month = month_from_filename(filename)
    await db.execute(delete(TimeEntry).where(TimeEntry.report_month == report_month))
    rows = parse_csv_file(filepath, report_month)
    db.add_all([TimeEntry(**r) for r in rows])
    await db.commit()

    return {"imported": len(rows), "month": report_month}


@app.get("/api/reports/{month}/data")
async def get_report(
    month: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    query = select(TimeEntry).where(TimeEntry.report_month == month)
    if date_from:
        query = query.where(TimeEntry.date >= date_from)
    if date_to:
        query = query.where(TimeEntry.date <= date_to)
    query = query.order_by(TimeEntry.date)

    result = await db.execute(query)
    entries = result.scalars().all()

    if not entries and not date_from and not date_to:
        raise HTTPException(status_code=404, detail="Reporte no encontrado en base de datos")

    rows = [entry_to_dict(e) for e in entries]
    return {"month": month, "rows": rows, "summary": build_summary(rows)}



@app.post("/api/email/send")
async def send_email(
    payload: dict,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    date_from = payload.get("date_from")
    date_to = payload.get("date_to")
    extra = payload.get("extra_recipients", [])
    subject = payload.get("subject") or f"Reporte Complemento 360 · {date_from} al {date_to}"
    message = payload.get("message", "")

    if not date_from or not date_to:
        raise HTTPException(status_code=400, detail="date_from y date_to son requeridos")

    query = (
        select(TimeEntry)
        .where(TimeEntry.date >= date_from, TimeEntry.date <= date_to)
        .order_by(TimeEntry.date)
    )
    result = await db.execute(query)
    rows = [entry_to_dict(e) for e in result.scalars().all()]

    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")

    summary     = build_summary(rows)
    excel_bytes = build_excel(date_from, date_to, rows, summary)
    pdf_bytes   = build_pdf(date_from, date_to, rows, summary)
    try:
        sent_to = await send_report_email(
            date_from, date_to, summary, rows,
            extra_recipients=extra or None,
            excel_bytes=excel_bytes,
            pdf_bytes=pdf_bytes,
            subject=subject,
            message=message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"sent_to": sent_to, "total_rows": len(rows)}


@app.get("/api/entries")
async def get_entries_by_range(
    date_from: str,
    date_to: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Query entries across any date range (ignores month boundaries)."""
    query = (
        select(TimeEntry)
        .where(TimeEntry.date >= date_from, TimeEntry.date <= date_to)
        .order_by(TimeEntry.date)
    )
    result = await db.execute(query)
    rows = [entry_to_dict(e) for e in result.scalars().all()]
    return {"date_from": date_from, "date_to": date_to, "rows": rows, "summary": build_summary(rows)}
