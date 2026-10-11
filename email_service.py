"""
email_service.py — Trimitere email prin Gmail SMTP.

Folosit pentru a trimite coduri de activare pacienților nou-creați.

SETUP GMAIL (necesar o singură dată):
  1. Activează 2-Step Verification pe contul Google:
     https://myaccount.google.com/security
  2. Generează un "App Password":
     https://myaccount.google.com/apppasswords
     (alege "Mail" → "Other" → numește-l "MedRec")
  3. Pune în .env:
     SMTP_USER=email-ul-tau@gmail.com
     SMTP_PASSWORD=cele-16-caractere-din-app-password

NOTĂ: NU folosi parola normală a contului Google — Gmail blochează SMTP
cu parola obișnuită. Trebuie App Password.
"""

import os
import html as html_escape
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MedRec")

# Dacă SMTP nu e configurat, intrăm în "mod dev" — printăm emailul în consolă
# în loc să-l trimitem. Util pentru testare fără un cont Gmail.
EMAIL_DEV_MODE = not (SMTP_USER and SMTP_PASSWORD)
if EMAIL_DEV_MODE:
    print("ℹ️  Email DEV MODE: emailurile vor fi printate în consolă, nu trimise.")
    print("    Configurează SMTP_USER și SMTP_PASSWORD în .env pentru trimitere reală.")


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Trimite un email HTML. Întoarce True dacă a reușit.

    În DEV MODE (fără SMTP configurat), printează emailul în consolă și
    întoarce True (pentru a nu bloca flow-ul în timpul dezvoltării).
    """
    if EMAIL_DEV_MODE:
        print("\n" + "=" * 60)
        print("EMAIL (DEV MODE — neexpedat)")
        print("=" * 60)
        print(f"Către:   {to_email}")
        print(f"Subiect: {subject}")
        print("-" * 60)
        # Printează versiunea text (strip tags simplu)
        import re
        text = re.sub(r"<[^>]+>", "", html_body)
        text = re.sub(r"\n\s*\n", "\n", text).strip()
        print(text)
        print("=" * 60 + "\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✓ Email trimis către {to_email}")
        return True

    except Exception as e:
        print(f"❌ Eroare trimitere email către {to_email}: {e}")
        return False


def send_activation_email(to_email: str, patient_name: str,
                          activation_code: str) -> bool:
    """Trimite codul de activare unui pacient nou."""
    subject = "MedRec — Cod de activare cont"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg, #667eea, #764ba2);
                  padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0;">🏥 MedRec</h1>
      </div>
      <div style="background: #f8f9ff; padding: 30px; border-radius: 0 0 12px 12px;">
        <p>Bună, <b>{html_escape.escape(patient_name)}</b>,</p>
        <p>Medicul tău a încărcat rezultatele tale de laborator în sistemul MedRec.
           Pentru a-ți accesa contul și a vedea raportul, activează-ți contul
           folosind codul de mai jos:</p>
        <div style="background: white; border: 2px dashed #667eea;
                    border-radius: 10px; padding: 20px; text-align: center;
                    margin: 25px 0;">
          <div style="font-size: 2.2em; font-weight: bold; color: #667eea;
                      letter-spacing: 8px;">{activation_code}</div>
        </div>
        <p>Mergi la pagina de activare, introdu acest cod și emailul tău,
           apoi setează-ți propria parolă.</p>
        <p style="color: #888; font-size: 0.9em;">
           Codul expiră în 48 de ore. Dacă nu ai solicitat acest cont,
           ignoră acest email.</p>
      </div>
      <p style="text-align: center; color: #aaa; font-size: 0.8em; margin-top: 20px;">
        MedRec — Sistem de recomandare specialist medical
      </p>
    </div>
    """
    return send_email(to_email, subject, html)