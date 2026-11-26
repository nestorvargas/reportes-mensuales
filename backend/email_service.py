import html
from datetime import date, timedelta
import os
from pathlib import Path
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from dotenv import load_dotenv
import aiosmtplib

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
LOGO_PATH = Path(__file__).parent.parent / "frontend" / "image" / "complemento360_logo.jpeg"
LOGO_CID = "logo_c360"

# Direcciones que reciben copia (Cc) de todos los envíos, separadas por coma
EMAIL_CC = [e.strip() for e in os.getenv("EMAIL_CC", "").split(",") if e.strip()]

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _validate_emails(addresses: list[str]) -> list[str]:
    invalid = [a for a in addresses if not _EMAIL_RE.match(a.strip())]
    if invalid:
        raise ValueError(f"Direcciones de correo inválidas: {', '.join(invalid)}")
    return [a.strip() for a in addresses]


MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _parse_contacts(raw: str) -> list[dict]:
    """Parse 'Nombre <correo>, Otro <correo2>' into [{name, email}]."""
    contacts = []
    for item in raw.split(","):
        m = re.match(r"^\s*(.*?)\s*<([^>]+)>\s*$", item)
        if m:
            contacts.append({"name": m.group(1), "email": m.group(2).strip()})
        elif item.strip():
            contacts.append({"name": "", "email": item.strip()})
    return contacts


EMAIL_CONTACTS = _parse_contacts(
    os.getenv("EMAIL_CONTACTS", "Diego Restrepo <diego.restrepo@complemento360.com>")
)


def month_label(date_to: str) -> str:
    """Nombre del mes del periodo. Se usa la fecha final: el ciclo 25 oct – 24 nov es 'Noviembre'."""
    y, m = date_to[:7].split("-")
    return f"{MESES[int(m) - 1]} de {y}"


def default_message(
    date_to: str,
    name: str = "Diego",
    kind: str = "cobro",            # "cobro" | "reporte"
    summary: dict | None = None,
    rows: list[dict] | None = None,
) -> str:
    """Mensaje por defecto cuando el usuario no escribe uno (debe coincidir con buildMessage del frontend)."""
    mes = month_label(date_to)
    if kind == "reporte":
        totales = ""
        if summary and rows:
            dias = len({r["date"] for r in rows})
            totales = f" En total registré {_to_hhmm(summary['total_minutes'])} horas distribuidas en {dias} días de trabajo."
        parts = [
            f"Hola {name},",
            "Espero que se encuentre muy bien.",
            f"Comparto el reporte de horas correspondiente al mes de {mes}.{totales}",
            "Adjunto el detalle en Excel y en PDF, con el resumen por tipo de actividad, "
            "por semana y el listado completo de registros.",
            "Quedo atento a cualquier comentario o ajuste.",
        ]
    else:
        parts = [
            f"Hola {name},",
            "Espero que se encuentre muy bien.",
            f"Envío la cuenta de cobro correspondiente al mes de {mes}, junto con el reporte de horas en Excel, "
            "el documento soporte de prestación de servicios y la planilla de aportes en línea (seguridad social) "
            "del mismo período, como soporte para el pago.",
            "Agradezco su ayuda gestionando el pago. Si necesita algún documento adicional o algún ajuste, quedo atento.",
        ]
    return "\n\n".join(parts + ["Cordialmente,\nFabian Vargas"])


def _fmt_date(d: str) -> str:
    y, m, day = d[:10].split("-")
    return f"{int(day)} de {MESES[int(m) - 1].lower()} de {y}"


def _to_hhmm(minutes: int) -> str:
    return f"{minutes // 60}:{minutes % 60:02d}"


def _attachment_icon(filename: str) -> tuple[str, str]:
    """(etiqueta, color) según la extensión."""
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "pdf": ("PDF", "#C62828"),
        "xlsx": ("XLS", "#2E7D32"),
        "png": ("IMG", "#1565C0"),
        "jpg": ("IMG", "#1565C0"),
        "jpeg": ("IMG", "#1565C0"),
    }.get(ext, ("DOC", "#546E7A"))


_ATTACHMENT_LABELS = {
    "cuenta_cobro": "Cuenta de cobro",
    "planilla_aportes": "Planilla de aportes en línea",
    "documento_soporte": "Documento soporte GAF-FOR-015",
    "reporte": "Reporte de horas",
}


def _attachment_label(filename: str) -> str:
    for prefix, label in _ATTACHMENT_LABELS.items():
        if filename.startswith(prefix):
            ext = filename.rsplit(".", 1)[-1].lower()
            return f"{label} ({'Excel' if ext == 'xlsx' else ext.upper()})"
    return filename


def _week_label(week: str) -> str:
    """'2026-W45' -> 'Semana 45 · 2 al 8 de nov'."""
    try:
        y, w = week.split("-W")
        start = date.fromisocalendar(int(y), int(w), 1)
        end = start + timedelta(days=6)
    except ValueError:
        return week
    mes = MESES[end.month - 1][:3].lower()
    if start.month == end.month:
        rango = f"{start.day} al {end.day} de {mes}"
    else:
        rango = f"{start.day} de {MESES[start.month - 1][:3].lower()} al {end.day} de {mes}"
    return f"Semana {int(w)} · {rango}"


def _section_title(text: str) -> str:
    return f'<div style="font-size:15px;font-weight:700;color:#1e293b;margin:22px 0 8px">{html.escape(text)}</div>'


def _bar_rows(items: list[tuple[str, int]], total: int, color: str = "#E8752A") -> str:
    """Filas con etiqueta, barra proporcional, horas y porcentaje."""
    peak = max((m for _, m in items), default=1) or 1
    out = []
    for label, minutes in items:
        width = max(2, round(minutes / peak * 100))
        pct = round(minutes / total * 100) if total else 0
        out.append(f"""<tr>
          <td style="padding:7px 0;border-bottom:1px solid #f1f5f9">
            <div style="font-size:13px;color:#334155;margin-bottom:5px">{html.escape(label)}</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="background:#f1f5f9;border-radius:4px;height:6px;font-size:0;line-height:0">
                <div style="width:{width}%;background:{color};height:6px;border-radius:4px;font-size:0;line-height:0">&nbsp;</div>
              </td>
            </tr></table>
          </td>
          <td width="104" style="width:104px;padding:7px 0 7px 14px;border-bottom:1px solid #f1f5f9;text-align:right;white-space:nowrap;vertical-align:bottom">
            <span style="font-size:14px;font-weight:700;color:#1e293b">{_to_hhmm(minutes)}</span>
            <span style="font-size:12px;color:#94a3b8;padding-left:4px">{pct}%</span>
          </td>
        </tr>""")
    return f'<table width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(out)}</table>'


def _report_details(summary: dict, rows: list[dict]) -> str:
    """Bloque del correo de reporte: indicadores, horas por tipo, por semana y principales tareas."""
    total = summary["total_minutes"]
    days = len({r["date"] for r in rows}) or 1
    kpis = [
        (_to_hhmm(total), "Horas totales"),
        (str(days), "Días trabajados"),
        (_to_hhmm(round(total / days)), "Promedio por día"),
        (str(len(rows)), "Registros"),
    ]
    kpi_cells = "".join(
        f"""<td width="25%" style="padding:4px">
          <div style="background:#FFF4EC;border:1px solid #FBD9C0;border-radius:8px;padding:12px 6px;text-align:center">
            <div style="font-size:20px;font-weight:800;color:#C65D0A;line-height:1.2">{value}</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px">{label}</div>
          </div>
        </td>"""
        for value, label in kpis
    )

    types = [(t["type"], t["minutes"]) for t in summary["by_type"]]
    if len(types) > 6:   # agrupar el resto para que el correo no se alargue
        types = types[:6] + [("Otros", sum(m for _, m in types[6:]))]
    weeks = [(_week_label(w["week"]), w["minutes"]) for w in summary["by_week"]]
    tasks = [(t["title"], t["minutes"]) for t in summary["by_work_item"][:5]]

    return f"""
      <tr><td style="padding:16px 28px 0">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{kpi_cells}</tr></table>
      </td></tr>
      <tr><td style="padding:0 32px">
        {_section_title("Horas por tipo de actividad")}
        {_bar_rows(types, total)}
        {_section_title("Horas por semana")}
        {_bar_rows(weeks, total, "#1A2744")}
        {_section_title("Principales tareas")}
        {_bar_rows(tasks, total, "#94a3b8")}
      </td></tr>"""


def build_html(
    message: str,
    date_from: str,
    date_to: str,
    summary: dict | None,
    rows: list[dict] | None,
    attachments: list[str],
    detailed: bool = False,
    logo_src: str | None = f"cid:{LOGO_CID}",
) -> str:
    """detailed=True agrega el resumen de horas (correo de reporte).
    logo_src: 'cid:…' para el correo; una ruta/URL para vistas previas; None sin logo."""
    esc = html.escape
    body = esc(message).replace("\n", "<br>")

    # Datos del periodo
    if date_from[:7] == date_to[:7]:   # mismo mes: "1 al 30 de noviembre de 2026"
        period = f"{int(date_from[8:10])} al {_fmt_date(date_to)}"
    else:
        period = f"{_fmt_date(date_from)} al {_fmt_date(date_to)}"
    stats = [("Período", period)]
    if summary and rows and not detailed:
        stats.append(("Horas registradas", _to_hhmm(summary["total_minutes"])))
        stats.append(("Días trabajados", str(len({r["date"] for r in rows}))))
    stats_html = "".join(
        f"""<tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;width:150px">{esc(label)}</td>
          <td style="padding:6px 0;color:#1e293b;font-size:14px;font-weight:600">{esc(value)}</td>
        </tr>"""
        for label, value in stats
    )

    att_html = "".join(
        f"""<tr>
          <td style="padding:6px 0;width:44px">
            <span style="display:inline-block;width:36px;padding:4px 0;border-radius:4px;background:{color};color:#fff;font-size:10px;font-weight:700;text-align:center">{tag}</span>
          </td>
          <td style="padding:6px 0">
            <div style="color:#1e293b;font-size:14px;font-weight:600">{esc(_attachment_label(name))}</div>
            <div style="color:#94a3b8;font-size:12px">{esc(name)}</div>
          </td>
        </tr>"""
        for name in attachments
        for tag, color in [_attachment_icon(name)]
    )
    att_block = f"""
      <tr><td style="padding:0 32px 8px">
        <div style="font-size:15px;font-weight:700;color:#1e293b;margin:22px 0 4px">Archivos adjuntos ({len(attachments)})</div>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">{att_html}</table>
      </td></tr>""" if attachments else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;padding:24px 12px">
  <tr><td align="center">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e2e8f0">
      <tr><td style="padding:20px 32px 16px;border-bottom:3px solid #E8752A">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          {f'<td valign="middle" style="padding-right:14px"><img src="{logo_src}" width="52" height="52" alt="C360" style="display:block;width:52px;height:52px;border:0"></td>' if logo_src else ''}
          <td valign="middle">
            <div style="font-size:18px;font-weight:700;color:#1e293b;line-height:1.2">Complemento 360</div>
            <div style="font-size:13px;color:#64748b;margin-top:2px">{esc(("Reporte de horas" if detailed else "Cuenta de cobro") + " · " + month_label(date_to))}</div>
          </td>
        </tr></table>
      </td></tr>

      <tr><td style="padding:28px 32px 8px;font-size:15px;line-height:1.65;color:#1e293b">
        {body}
      </td></tr>

      <tr><td style="padding:16px 32px 8px">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px">
          <tr><td style="padding:12px 18px">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">{stats_html}</table>
          </td></tr>
        </table>
      </td></tr>
      {_report_details(summary, rows) if detailed and summary and rows else ""}
      {att_block}
      <tr><td style="padding:20px 32px 24px">
        <div style="border-top:1px solid #e2e8f0;padding-top:14px;font-size:12px;color:#94a3b8">
          Complemento 360 · {esc(month_label(date_to))}
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""


async def send_report_email(
    date_from: str,
    date_to: str,
    summary: dict,
    rows: list[dict],
    extra_recipients: list[str] | None = None,
    excel_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    cuenta_cobro_bytes: bytes | None = None,
    subject: str | None = None,
    message: str | None = None,
    extra_attachments: list[tuple[str, bytes, str]] | None = None,
    detailed: bool | None = None,
) -> list[str]:
    """extra_attachments: lista de (nombre_archivo, contenido, mime_type).
    detailed: True = correo de reporte con resumen de horas; por defecto, si no hay cuenta de cobro."""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("Credenciales SMTP no configuradas en .env")

    recipients = list(extra_recipients) if extra_recipients else []
    if not recipients:
        raise ValueError("No hay destinatarios configurados")
    recipients = _validate_emails(recipients)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject or f"Cuenta de cobro · {month_label(date_to)}"
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)
    to_lower = {r.lower() for r in recipients}
    cc = [c for c in _validate_emails(EMAIL_CC) if c.lower() not in to_lower] if EMAIL_CC else []
    if cc:
        msg["Cc"] = ", ".join(cc)

    attachments: list[str] = []
    attachment_parts: list[MIMEBase] = []

    def _attach(filename: str, content: bytes, mime: str) -> None:
        maintype, _, subtype = mime.partition("/")
        part = MIMEBase(maintype or "application", subtype or "octet-stream")
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        attachment_parts.append(part)
        attachments.append(filename)

    if cuenta_cobro_bytes:
        _attach(f"cuenta_cobro_{date_from}_{date_to}.pdf", cuenta_cobro_bytes, "application/pdf")
    if excel_bytes:
        _attach(f"reporte_{date_from}_{date_to}.xlsx", excel_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if pdf_bytes:
        _attach(f"reporte_{date_from}_{date_to}.pdf", pdf_bytes, "application/pdf")
    for filename, content, mime in extra_attachments or []:
        _attach(filename, content, mime)

    # Cuerpo: texto plano + HTML
    body_text = message.strip() if message and message.strip() else default_message(date_to)
    plain = body_text + "\n\nAdjuntos:\n" + "\n".join(f"- {a}" for a in attachments) if attachments else body_text
    has_logo = LOGO_PATH.exists()
    html_body = build_html(body_text, date_from, date_to, summary, rows, attachments,
                           detailed=(not cuenta_cobro_bytes) if detailed is None else detailed,
                           logo_src=f"cid:{LOGO_CID}" if has_logo else None)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    if has_logo:
        related = MIMEMultipart("related")
        related.attach(alt)
        logo = MIMEImage(LOGO_PATH.read_bytes(), "jpeg")
        logo.add_header("Content-ID", f"<{LOGO_CID}>")
        logo.add_header("Content-Disposition", "inline", filename="logo.jpeg")
        related.attach(logo)
        msg.attach(related)
    else:
        msg.attach(alt)
    for part in attachment_parts:
        msg.attach(part)

    await aiosmtplib.send(
        msg,
        recipients=recipients + cc,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        start_tls=True,
    )
    return recipients
