import calendar
import csv
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import init_db, get_session, TimeEntry, EmailLog, HiddenContact
from auth import verify_password, create_token, get_current_user, APP_USER
from email_service import send_report_email, month_label, default_message, EMAIL_CONTACTS, EMAIL_CC, SMTP_FROM, SMTP_USER
from report_generator import build_excel, build_pdf, build_cuenta_cobro_pdf, build_documento_soporte

REPORTS_DIR  = Path(__file__).parent.parent / "reportes_mensuales"
ENVIADOS_DIR = Path(__file__).parent.parent / "reportes_enviados"


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


def month_range(month: str) -> tuple[str, str]:
    """'2026-11' -> ('2026-11-01', '2026-11-30'): mes calendario completo."""
    y, m = (int(x) for x in month.split("-"))
    return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


def cycle_range(month: str) -> tuple[str, str]:
    """Ciclo de cuenta de cobro: '2026-11' -> ('2026-10-25', '2026-11-24')."""
    y, m = (int(x) for x in month.split("-"))
    py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    return f"{py}-{pm:02d}-25", f"{y}-{m:02d}-24"


async def load_rows(
    db: AsyncSession,
    date_from: str,
    date_to: str,
    month: str | None = None,
    cycle: str | None = None,
) -> list[dict]:
    """Registros a reportar, siempre filtrados por fecha (no por el CSV del que vienen):
    - `cycle` (pestaña cuenta de cobro): del 25 del mes anterior al 24 del mes.
    - `month` (pestaña por mes): mes calendario completo.
    - sin ninguno: el rango de fechas dado."""
    if cycle:
        date_from, date_to = cycle_range(cycle)
    elif month:
        date_from, date_to = month_range(month)
    query = select(TimeEntry).where(TimeEntry.date >= date_from, TimeEntry.date <= date_to)
    result = await db.execute(query.order_by(TimeEntry.date))
    return [entry_to_dict(e) for e in result.scalars().all()]


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

    reports.sort(key=lambda r: r["month"], reverse=True)
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
    cycle: bool = False,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    # Ciclo de cuenta de cobro (25 al 24) o mes calendario (1 al último día), por fecha
    month_from, month_to = cycle_range(month) if cycle else month_range(month)
    query = select(TimeEntry).where(TimeEntry.date >= month_from, TimeEntry.date <= month_to)
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
    message = payload.get("message", "")

    if not date_from or not date_to:
        raise HTTPException(status_code=400, detail="date_from y date_to son requeridos")
    # Correo de reporte de horas: Excel + PDF del reporte (la cuenta de cobro va en su propio envío)
    subject = payload.get("subject") or f"Reporte de horas · {month_label(date_to)}"

    rows = await load_rows(db, date_from, date_to, payload.get("month"), payload.get("cycle"))

    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")

    summary     = build_summary(rows)
    if not message.strip():
        message = default_message(date_to, kind="reporte", summary=summary, rows=rows)
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
        # Guardar archivos en reportes_enviados/<mes>/
        month_folder = ENVIADOS_DIR / date_to[:7]
        month_folder.mkdir(parents=True, exist_ok=True)
        base_name = f"reporte_{date_from}_{date_to}"
        (month_folder / f"{base_name}.xlsx").write_bytes(excel_bytes)
        (month_folder / f"{base_name}.pdf").write_bytes(pdf_bytes)

        db.add(EmailLog(
            date_from=date_from, date_to=date_to,
            recipients=json.dumps(sent_to),
            subject=subject,
            total_rows=len(rows),
            status="success",
        ))
        await db.commit()
    except Exception as e:
        db.add(EmailLog(
            date_from=date_from, date_to=date_to,
            recipients=json.dumps(extra or []),
            subject=subject,
            total_rows=len(rows),
            status="error",
            error=str(e),
        ))
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "sent_to": sent_to,
        "total_rows": len(rows),
        "attachments": [f"reporte_{date_from}_{date_to}.xlsx", f"reporte_{date_from}_{date_to}.pdf"],
    }


PLANILLA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
PLANILLA_MAX_BYTES = 10 * 1024 * 1024
PLANILLAS_REQUERIDAS = 2   # la planilla de aportes en línea llega en 2 archivos
PLANILLAS_MAX = 4


@app.post("/api/email/send-cuenta-cobro")
async def send_cuenta_cobro_email(
    date_from: str = Form(...),
    date_to: str = Form(...),
    extra_recipients: str = Form("[]"),   # JSON array
    subject: str = Form(""),
    message: str = Form(""),
    month: str = Form(""),                 # pestaña por mes: mes calendario
    cycle: str = Form(""),                 # pestaña cuenta de cobro: ciclo del 25 al 24
    planillas: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Envía la cuenta de cobro (PDF), el reporte de horas (Excel) y el documento soporte
    GAF-FOR-015 (generados), más los archivos de la planilla de aportes en línea (subidos, 2)."""
    try:
        extra = json.loads(extra_recipients or "[]")
        if not isinstance(extra, list):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="extra_recipients debe ser una lista JSON")
    if not extra:
        raise HTTPException(status_code=400, detail="Agrega al menos un destinatario")

    planillas = [p for p in planillas if p.filename]
    if len(planillas) < PLANILLAS_REQUERIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"La planilla de aportes en línea son {PLANILLAS_REQUERIDAS} archivos: "
                   f"adjuntaste {len(planillas)}",
        )
    if len(planillas) > PLANILLAS_MAX:
        raise HTTPException(status_code=400, detail=f"Máximo {PLANILLAS_MAX} archivos de planilla")

    planilla_files: list[tuple[str, bytes, str]] = []   # (extensión, contenido, mime)
    for p in planillas:
        ext = Path(p.filename).suffix.lower()
        if ext not in PLANILLA_TYPES:
            raise HTTPException(status_code=400, detail=f"{p.filename}: la planilla debe ser PDF, PNG o JPG")
        content = await p.read(PLANILLA_MAX_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail=f"{p.filename} está vacío")
        if len(content) > PLANILLA_MAX_BYTES:
            raise HTTPException(status_code=400, detail=f"{p.filename} supera 10 MB")
        planilla_files.append((ext, content, PLANILLA_TYPES[ext]))

    rows = await load_rows(db, date_from, date_to, month or None, cycle or None)
    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")

    subject = subject.strip() or f"Cuenta de cobro · {month_label(date_to)}"
    summary = build_summary(rows)
    cobro_bytes = build_cuenta_cobro_pdf(date_from, date_to, rows, summary)
    try:
        soporte_bytes = build_documento_soporte(date_from, date_to, summary)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    soporte_name  = f"documento_soporte_{date_to[:7]}.xlsx"
    excel_bytes   = build_excel(date_from, date_to, rows, summary)
    # planilla_aportes_2026-11_1.pdf, planilla_aportes_2026-11_2.pdf
    planilla_named = [
        (f"planilla_aportes_{date_to[:7]}_{i}{ext}", content, mime)
        for i, (ext, content, mime) in enumerate(planilla_files, start=1)
    ]
    try:
        sent_to = await send_report_email(
            date_from, date_to, summary, rows,
            extra_recipients=extra,
            cuenta_cobro_bytes=cobro_bytes,
            excel_bytes=excel_bytes,
            extra_attachments=[
                (soporte_name, soporte_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                *planilla_named,
            ],
            detailed=False,
            subject=subject,
            message=message,
        )
        month_folder = ENVIADOS_DIR / date_to[:7]
        month_folder.mkdir(parents=True, exist_ok=True)
        (month_folder / f"cuenta_cobro_{date_from}_{date_to}.pdf").write_bytes(cobro_bytes)
        (month_folder / f"reporte_{date_from}_{date_to}.xlsx").write_bytes(excel_bytes)
        (month_folder / soporte_name).write_bytes(soporte_bytes)
        for name, content, _mime in planilla_named:
            (month_folder / name).write_bytes(content)

        db.add(EmailLog(
            date_from=date_from, date_to=date_to,
            recipients=json.dumps(sent_to), subject=subject,
            total_rows=len(rows), status="success",
        ))
        await db.commit()
    except Exception as e:
        db.add(EmailLog(
            date_from=date_from, date_to=date_to,
            recipients=json.dumps(extra), subject=subject,
            total_rows=len(rows), status="error", error=str(e),
        ))
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "sent_to": sent_to,
        "attachments": [
            f"cuenta_cobro_{date_from}_{date_to}.pdf",
            f"reporte_{date_from}_{date_to}.xlsx",
            soporte_name,
            *[name for name, _, _ in planilla_named],
        ],
    }


@app.get("/api/email/cc")
async def get_email_cc(_: str = Depends(get_current_user)):
    """Direcciones que reciben copia automática de todos los envíos."""
    return EMAIL_CC


@app.get("/api/email/contacts")
async def get_email_contacts(
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Contactos configurados (EMAIL_CONTACTS) + destinatarios usados en envíos exitosos."""
    # La cuenta remitente y las de copia automática no se sugieren como destinatarios
    # ni las que el usuario ocultó
    hidden = await db.execute(select(HiddenContact.email))
    excluded = {e.lower() for e in [SMTP_FROM, SMTP_USER, *EMAIL_CC] if e} | set(hidden.scalars().all())
    contacts = [c for c in EMAIL_CONTACTS if c["email"].lower() not in excluded]
    known = {c["email"].lower() for c in contacts} | excluded
    result = await db.execute(
        select(EmailLog.recipients).where(EmailLog.status == "success").order_by(EmailLog.sent_at.desc())
    )
    for raw in result.scalars().all():
        for email in json.loads(raw) if raw else []:
            if email.lower() not in known:
                known.add(email.lower())
                contacts.append({"name": "", "email": email})
    return contacts


@app.delete("/api/email/contacts/{email}")
async def hide_email_contact(
    email: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Quita un correo de las sugerencias (no afecta el historial de envíos)."""
    key = email.strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="Correo vacío")
    if not await db.get(HiddenContact, key):
        db.add(HiddenContact(email=key))
        await db.commit()
    return {"hidden": key}


@app.get("/api/logs")
async def get_logs(
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailLog).order_by(EmailLog.sent_at.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "sent_at": l.sent_at.isoformat(),
            "date_from": l.date_from,
            "date_to": l.date_to,
            "recipients": json.loads(l.recipients) if l.recipients else [],
            "subject": l.subject,
            "total_rows": l.total_rows,
            "status": l.status,
            "error": l.error,
        }
        for l in logs
    ]


@app.post("/api/reporte/download")
async def download_reporte(
    payload: dict,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Excel del reporte de horas (Resumen, Por día, Detalle) del periodo visible."""
    date_from = payload.get("date_from")
    date_to   = payload.get("date_to")
    if not date_from or not date_to:
        raise HTTPException(status_code=400, detail="date_from y date_to son requeridos")

    rows = await load_rows(db, date_from, date_to, payload.get("month"), payload.get("cycle"))
    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")

    excel_bytes = build_excel(date_from, date_to, rows, build_summary(rows))
    filename    = f"reporte_{date_from}_{date_to}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/documento-soporte/download")
async def download_documento_soporte(
    payload: dict,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    """Documento soporte GAF-FOR-015 de Complemento 360 lleno con las horas del periodo."""
    date_from = payload.get("date_from")
    date_to   = payload.get("date_to")
    if not date_from or not date_to:
        raise HTTPException(status_code=400, detail="date_from y date_to son requeridos")

    rows = await load_rows(db, date_from, date_to, payload.get("month"), payload.get("cycle"))
    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")
    try:
        xlsx = build_documento_soporte(date_from, date_to, build_summary(rows))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    filename = f"documento_soporte_{date_to[:7]}.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/cuenta-cobro/download")
async def download_cuenta_cobro(
    payload: dict,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    date_from = payload.get("date_from")
    date_to   = payload.get("date_to")
    if not date_from or not date_to:
        raise HTTPException(status_code=400, detail="date_from y date_to son requeridos")

    rows = await load_rows(db, date_from, date_to, payload.get("month"), payload.get("cycle"))
    if not rows:
        raise HTTPException(status_code=404, detail="No hay datos en ese rango de fechas")

    pdf_bytes = build_cuenta_cobro_pdf(date_from, date_to, rows, build_summary(rows))
    filename  = f"cuenta_cobro_{date_from}_{date_to}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
