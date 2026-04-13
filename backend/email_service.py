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
    total = summary["total_minutes"] or 1

    by_type_rows = "".join(
        f"""<tr>
          <td>{t['type']}</td>
          <td style='text-align:right;font-weight:700;color:#E8752A;white-space:nowrap'>{_to_hhmm(t['minutes'])}</td>
          <td style='width:120px;padding-left:8px'>
            <div style='background:#f1f5f9;border-radius:4px;height:6px;overflow:hidden'>
              <div style='background:#E8752A;height:6px;width:{round(t["minutes"]/total*100)}%'></div>
            </div>
          </td>
        </tr>"""
        for t in summary["by_type"]
    )
    by_week_rows = "".join(
        f"<tr><td>{w['week']}</td><td style='text-align:right;font-weight:700;color:#E8752A'>{_to_hhmm(w['minutes'])}</td></tr>"
        for w in summary["by_week"]
    )
    detail_rows = "".join(
        f"""<tr>
          <td style='white-space:nowrap;color:#64748b'>{r['date']}</td>
          <td style='font-weight:500'>{r['work_item_title']}</td>
          <td style='white-space:nowrap'><span style='background:#FEF0E6;color:#C65D0A;font-size:.72rem;font-weight:600;padding:2px 8px;border-radius:20px'>{r['type']}</span></td>
          <td style='color:#64748b;font-size:.82rem'>{r['comment']}</td>
          <td style='text-align:right;font-weight:700;color:#E8752A;white-space:nowrap'>{_to_hhmm(r['minutes'])}</td>
        </tr>"""
        for r in rows
    )

    logo_html = f'<img src="{_LOGO_SRC}" alt="C360" style="height:56px;width:56px;object-fit:contain;border-radius:12px;background:#fff;padding:6px;box-shadow:0 2px 8px rgba(0,0,0,.15)" />' if _LOGO_SRC else ""
    unique_days = len(set(r["date"] for r in rows))

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #37474f; margin: 0; padding: 0; background: #f0f4f8; }}
  .wrap {{ max-width: 680px; margin: 32px auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.10); }}

  /* ── Header ── */
  .header {{ background: linear-gradient(135deg, #E8752A 0%, #C65D0A 100%); padding: 0; }}
  .header-top {{ display: flex; align-items: center; gap: 18px; padding: 28px 36px 20px; }}
  .header-title {{ color: #fff; }}
  .header-title h1 {{ margin: 0 0 4px; font-size: 1.35rem; font-weight: 700; letter-spacing: -.01em; }}
  .header-title p  {{ margin: 0; font-size: .85rem; opacity: .85; }}
  .header-banner {{ background: rgba(0,0,0,.15); padding: 12px 36px; display: flex; align-items: center; gap: 8px; }}
  .header-banner span {{ color: rgba(255,255,255,.8); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }}
  .header-banner strong {{ color: #fff; font-size: 1.6rem; font-weight: 800; margin-right: 4px; }}

  /* ── Body ── */
  .body {{ padding: 28px 36px; }}

  /* ── Message ── */
  .message-block {{ background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 0 8px 8px 0; padding: 14px 18px; margin-bottom: 24px; }}
  .message-label {{ font-size: .68rem; font-weight: 700; color: #92400e; text-transform: uppercase; letter-spacing: .07em; margin: 0 0 5px; }}
  .message-text  {{ font-size: .9rem; color: #1a1a2e; margin: 0; line-height: 1.65; white-space: pre-line; }}

  /* ── KPIs ── */
  .kpi-row {{ display: flex; gap: 10px; margin-bottom: 28px; }}
  .kpi {{ flex: 1; background: #f8fafc; border-radius: 10px; padding: 14px 10px; text-align: center; border: 1px solid #e2e8f0; }}
  .kpi .val {{ font-size: 1.4rem; font-weight: 800; color: #E8752A; line-height: 1.1; }}
  .kpi .lbl {{ font-size: .67rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; margin-top: 4px; }}

  /* ── Section headers ── */
  .section-title {{ display: flex; align-items: center; gap: 8px; font-size: .85rem; font-weight: 700; color: #37474f; text-transform: uppercase; letter-spacing: .05em; margin: 24px 0 10px; padding-bottom: 8px; border-bottom: 2px solid #f1f5f9; }}
  .section-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #E8752A; flex-shrink: 0; }}

  /* ── Two-column layout ── */
  .two-col {{ display: flex; gap: 20px; margin-bottom: 4px; }}
  .two-col .col {{ flex: 1; min-width: 0; }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; font-size: .83rem; }}
  th {{ background: #f8fafc; padding: 8px 10px; text-align: left; color: #64748b; font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover td {{ background: #fafafa; }}

  /* ── Footer ── */
  .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 36px; display: flex; justify-content: space-between; align-items: center; }}
  .footer-left {{ font-size: .72rem; color: #94a3b8; }}
  .footer-brand {{ font-size: .72rem; font-weight: 700; color: #E8752A; }}
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <div class="header">
    <div class="header-top">
      {logo_html}
      <div class="header-title">
        <h1>Complemento 360</h1>
        <p>Reporte de horas &nbsp;·&nbsp; {date_from} al {date_to}</p>
      </div>
    </div>
    <div class="header-banner">
      <strong>{_to_hhmm(summary['total_minutes'])}</strong>
      <span>horas registradas &nbsp;·&nbsp; {len(rows)} registros &nbsp;·&nbsp; {unique_days} días trabajados</span>
    </div>
  </div>

  <!-- Body -->
  <div class="body">

    {f'''<div class="message-block">
      <p class="message-label">Mensaje</p>
      <p class="message-text">{message.replace(chr(10), "<br>")}</p>
    </div>''' if message and message.strip() else ""}

    <!-- KPIs -->
    <div class="kpi-row">
      <div class="kpi"><div class="val">{_to_hhmm(summary['total_minutes'])}</div><div class="lbl">Total horas</div></div>
      <div class="kpi"><div class="val">{len(rows)}</div><div class="lbl">Registros</div></div>
      <div class="kpi"><div class="val">{len(summary['by_week'])}</div><div class="lbl">Semanas</div></div>
      <div class="kpi"><div class="val">{unique_days}</div><div class="lbl">Días</div></div>
      <div class="kpi"><div class="val">{len(summary['by_work_item'])}</div><div class="lbl">Work Items</div></div>
    </div>

    <!-- Horas por tipo + por semana -->
    <div class="two-col">
      <div class="col">
        <div class="section-title"><span class="section-dot"></span>Horas por tipo</div>
        <table>
          <thead><tr><th>Tipo</th><th style="text-align:right">Tiempo</th><th></th></tr></thead>
          <tbody>{by_type_rows}</tbody>
        </table>
      </div>
      <div class="col">
        <div class="section-title"><span class="section-dot"></span>Horas por semana</div>
        <table>
          <thead><tr><th>Semana</th><th style="text-align:right">Tiempo</th></tr></thead>
          <tbody>{by_week_rows}</tbody>
        </table>
      </div>
    </div>

    <!-- Detalle -->
    <div class="section-title" style="margin-top:28px"><span class="section-dot"></span>Detalle de registros</div>
    <table>
      <thead>
        <tr>
          <th>Fecha</th><th>Work Item</th><th>Tipo</th><th>Comentario</th><th style="text-align:right">Tiempo</th>
        </tr>
      </thead>
      <tbody>{detail_rows}</tbody>
    </table>

  </div>

  <!-- Footer -->
  <div class="footer">
    <span class="footer-left">Generado automáticamente · {date_from} – {date_to}</span>
    <span class="footer-brand">Complemento 360</span>
  </div>

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
