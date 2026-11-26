import html
import os
import re
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


def month_label(date_from: str) -> str:
    y, m = date_from[:7].split("-")
    return f"{MESES[int(m) - 1]} de {y}"


def default_message(date_from: str, name: str = "Diego") -> str:
    return (
        f"Hola {name},\n\n"
        f"Adjunto cuenta de cobro del mes de {month_label(date_from)}.\n\n"
        "Cordialmente,\n"
        "Fabian Vargas"
    )


def build_html(message: str) -> str:
    body = html.escape(message).replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;font-size:14px;color:#222;line-height:1.6">
{body}
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
) -> list[str]:
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("Credenciales SMTP no configuradas en .env")

    recipients = list(extra_recipients) if extra_recipients else []
    if not recipients:
        raise ValueError("No hay destinatarios configurados")
    recipients = _validate_emails(recipients)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject or f"Cuenta de cobro · {month_label(date_from)}"
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)

    # Cuerpo: texto plano + HTML simple
    body_text = message.strip() if message and message.strip() else default_message(date_from)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(build_html(body_text), "html", "utf-8"))
    msg.attach(alt)

    # Cuenta de cobro attachment
    if cuenta_cobro_bytes:
        part = MIMEBase("application", "pdf")
        part.set_payload(cuenta_cobro_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="cuenta_cobro_{date_from}_{date_to}.pdf"')
        msg.attach(part)

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
