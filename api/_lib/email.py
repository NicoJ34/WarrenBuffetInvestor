import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from api._lib.config import get_settings

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, reset_url: str) -> None:
    settings = get_settings()

    if not settings.smtp_host or not settings.smtp_user:
        logger.info("SMTP non configuré — lien de reset (dev) : %s", reset_url)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Réinitialisation de votre mot de passe"
    msg["From"] = settings.email_from
    msg["To"] = to_email

    html = f"""
    <html><body>
      <p>Bonjour,</p>
      <p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe (valable 1 heure) :</p>
      <p><a href="{reset_url}">{reset_url}</a></p>
      <p>Si vous n'avez pas fait cette demande, ignorez cet email.</p>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.email_from, to_email, msg.as_string())
    except Exception as exc:
        logger.error("Erreur envoi email reset : %s", exc)
