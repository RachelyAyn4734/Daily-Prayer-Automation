import smtplib, ssl
from email.mime.text import MIMEText

sender = "YOUR_GMAIL@gmail.com"
app_password = "xxxx xxxx xxxx xxxx"  # App Password מגוגל (חובה עם 2FA)
to = "recipient@example.com"

msg = MIMEText("Hello via SMTPS 465")
msg["Subject"] = "SMTP_SSL test"
msg["From"] = sender
msg["To"] = to

context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as s:
    s.set_debuglevel(1)
    s.login(sender, app_password)
    s.sendmail(sender, [to], msg.as_string())
