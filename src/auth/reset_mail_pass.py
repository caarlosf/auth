from email.message import EmailMessage
import smtplib


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_link = f"http://localhost:8000/auth/password-reset/confirm?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Restablece tu contraseña"
    msg["From"] = "no-reply@tuapp.com"
    msg["To"] = to_email
    msg.set_content(f"Usa este enlace (válido 30 minutos):\n{reset_link}")

    with smtplib.SMTP("mailpit", 1025) as smtp:
        smtp.send_message(msg)