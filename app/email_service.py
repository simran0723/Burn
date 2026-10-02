import smtplib
import os
from email.message import EmailMessage

def send_email(to_email , subject , body ):
   
    email = EmailMessage()
    email["From"] = os.getenv("EMAIL_ADDRESS")
    email["to"] = to_email
    email["Subject"] = subject

    email.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"),
            os.getenv("EMAIL_PASSWORD")
        )
        smtp.send_message(email)
    