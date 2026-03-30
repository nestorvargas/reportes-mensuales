import os
import re
import base64
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import aiosmtplib

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Logo embebido en base64
_LOGO_PATH = Path(__file__).parent.parent / "frontend" / "image" / "complemento360_logo.jpeg"
_LOGO_B64 = ""
if _LOGO_PATH.exists():
    _LOGO_B64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
_LOGO_SRC = f"data:image/jpeg;base64,{_LOGO_B64}" if _LOGO_B64 else ""


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _validate_emails(addresses: list[str]) -> list[str]:
    invalid = [a for a in addresses if not _EMAIL_RE.match(a.strip())]
    if invalid:
        raise ValueError(f"Direcciones de correo inválidas: {', '.join(invalid)}")
    return [a.strip() for a in addresses]


def _to_hhmm(minutes: int) -> str:
    return f"{minutes // 60}:{str(minutes % 60).zfill(2)}"


def build_html(date_from: str, date_to: str, summary: dict, rows: list[dict], message: str | None = None) -> str:
    by_type_rows = "".join(
        f"<tr><td>{t['type']}</td><td style='text-align:right;font-weight:700;color:#E8752A'>{_to_hhmm(t['minutes'])}</td></tr>"
        for t in summary["by_type"]
    )
    by_week_rows = "".join(
        f"<tr><td>{w['week']}</td><td style='text-align:right;font-weight:700;color:#E8752A'>{_to_hhmm(w['minutes'])}</td></tr>"
        for w in summary["by_week"]
    )
    detail_rows = "".join(
        f"""<tr>
          <td style='white-space:nowrap'>{r['date']}</td>
          <td>{r['work_item_title']}</td>
          <td style='white-space:nowrap'>{r['type']}</td>
          <td>{r['comment']}</td>
          <td style='text-align:right;font-weight:700;color:#E8752A;white-space:nowrap'>{_to_hhmm(r['minutes'])}</td>
        </tr>"""
        for r in rows
    )

    logo_html = f'<img src="{_LOGO_SRC}" alt="C360" style="height:48px;width:48px;object-fit:contain;border-radius:10px;background:#fff;padding:4px" />' if _LOGO_SRC else ""

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #37474f; margin: 0; padding: 0; background: #f5f5f5; }}
  .wrap {{ max-width: 680px; margin: 24px auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.1); }}
  .header {{ background: #E8752A; color: #fff; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }}
  .header h1 {{ margin: 0; font-size: 1.4rem; }}
  .header p {{ margin: 6px 0 0; opacity: .8; font-size: 0.9rem; }}
  .body {{ padding: 24px 32px; }}
  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .kpi {{ flex: 1; background: #f8fafc; border-radius: 8px; padding: 14px; text-align: center; }}
  .kpi .val {{ font-size: 1.6rem; font-weight: 800; color: #0f3460; }}
  .kpi .lbl {{ font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .04em; margin-top: 2px; }}
  h2 {{ font-size: 0.95rem; color: #0f3460; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 20px 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.83rem; }}
  th {{ background: #f8fafc; padding: 8px 10px; text-align: left; color: #64748b; font-size: 0.75rem; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom: none; }}
  .footer {{ background: #f8fafc; padding: 14px 32px; font-size: 0.75rem; color: #94a3b8; text-align: center; }}
  .message-block {{ background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 6px; padding: 16px 20px; margin-bottom: 20px; }}
  .message-label {{ font-size: 0.7rem; font-weight: 700; color: #92400e; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 6px; }}
  .message-text {{ font-size: 0.92rem; color: #1a1a2e; margin: 0; line-height: 1.6; white-space: pre-line; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    {logo_html}
    <div>
      <h1>Complemento 360 — Reporte de horas</h1>
      <p>Período: {date_from} al {date_to}</p>
    </div>
  </div>
  <div class="body">
    {f'''<div class="message-block">
      <p class="message-label">Mensaje</p>
      <p class="message-text">{message.replace(chr(10), "<br>")}</p>
    </div>''' if message and message.strip() else ""}
    <div class="kpi-row">
      <div class="kpi"><div class="val">{_to_hhmm(summary['total_minutes'])}</div><div class="lbl">Total horas</div></div>
      <div class="kpi"><div class="val">{len(rows)}</div><div class="lbl">Registros</div></div>
      <div class="kpi"><div class="val">{len(summary['by_week'])}</div><div class="lbl">Semanas</div></div>
      <div class="kpi"><div class="val">{len(summary['by_work_item'])}</div><div class="lbl">Work Items</div></div>
    </div>

    <h2>Horas por tipo</h2>
    <table><thead><tr><th>Tipo</th><th style="text-align:right">Tiempo</th></tr></thead>
    <tbody>{by_type_rows}</tbody></table>

    <h2>Horas por semana</h2>
    <table><thead><tr><th>Semana</th><th style="text-align:right">Tiempo</th></tr></thead>
    <tbody>{by_week_rows}</tbody></table>

    <h2>Detalle de registros</h2>
    <table>
      <thead><tr><th>Fecha</th><th>Work Item</th><th>Tipo</th><th>Comentario</th><th style="text-align:right">Tiempo</th></tr></thead>
      <tbody>{detail_rows}</tbody>
    </table>
  </div>
  <div class="footer">Generado por Complemento 360 · {date_from} – {date_to}</div>
</div>
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
    subject: str | None = None,
    message: str | None = None,
) -> list[str]:
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("Credenciales SMTP no configuradas en .env")

    recipients = list(extra_recipients) if extra_recipients else []
    if not recipients:
        raise ValueError("No hay destinatarios configurados")
    recipients = _validate_emails(recipients)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject or f"Reporte Complemento 360 · {date_from} al {date_to}"
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)

    # HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(build_html(date_from, date_to, summary, rows, message), "html"))
    msg.attach(alt)

    # Excel attachment
    if excel_bytes:
        part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.set_payload(excel_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="reporte_{date_from}_{date_to}.xlsx"')
        msg.attach(part)

    # PDF attachment
    if pdf_bytes:
        part = MIMEBase("application", "pdf")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="reporte_{date_from}_{date_to}.pdf"')
        msg.attach(part)

    await aiosmtplib.send(
        msg,
        recipients=recipients,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        start_tls=True,
    )
    return recipients
