from email.message import EmailMessage
import smtplib
import os
from dotenv import load_dotenv


load_dotenv()
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT"))
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_FROM = os.environ.get("EMAIL_FROM")


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_link = f"http://localhost:8000/auth/password-reset/confirm?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Restablece tu contraseña"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg.set_content(f"Usa este enlace (válido 30 minutos):\n{reset_link}")

    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp.send_message(msg)