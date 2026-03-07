import smtplib
import ssl
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Locate templates directory relative to this file's location
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, context: dict) -> str:
    """Render a Jinja2 email template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


def _send(to_email: str, subject: str, html_body: str) -> bool:
    """Core SMTP send function. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email NOT sent.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, message.as_string())
        logger.info(f"Email sent successfully to {to_email} | Subject: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending to {to_email}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}", exc_info=True)
    return False


def send_password_reset(to_email: str, reset_token: str) -> bool:
    """Send a password reset email with a link containing the token."""
    reset_url = f"{FRONTEND_URL}/password-reset/confirm?token={reset_token}"
    html_body = _render("password_reset.html", {
        "reset_url": reset_url,
        "frontend_url": FRONTEND_URL,
        "email": to_email,
    })
    return _send(to_email, "Reset Your VRA Password", html_body)


def send_verification(to_email: str, verify_token: str) -> bool:
    """Send an email verification link."""
    verify_url = f"{FRONTEND_URL}/verify-email?token={verify_token}"
    html_body = _render("verify_email.html", {
        "verify_url": verify_url,
        "frontend_url": FRONTEND_URL,
        "email": to_email,
    })
    return _send(to_email, "Verify Your VRA Account Email", html_body)
