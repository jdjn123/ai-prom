import smtplib
from email.mime.text import MIMEText
import requests
from .config import (
    WECOM_ENABLED, WECOM_WEBHOOK, 
    DINGTALK_ENABLED, DINGTALK_WEBHOOK, 
    EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO
)

def send_wecom(text: str) -> bool:
    if not (WECOM_ENABLED and WECOM_WEBHOOK):
        return False
    try:
        r = requests.post(WECOM_WEBHOOK, json={"msgtype": "text", "text": {"content": text}}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"WeCom Alert Error: {e}")
        return False

def send_dingtalk(text: str) -> bool:
    if not (DINGTALK_ENABLED and DINGTALK_WEBHOOK):
        return False
    try:
        r = requests.post(DINGTALK_WEBHOOK, json={"msgtype": "text", "text": {"content": text}}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"DingTalk Alert Error: {e}")
        return False

def send_email(subject: str, body: str) -> bool:
    if not (EMAIL_ENABLED and SMTP_HOST and SMTP_USER and SMTP_PASS and MAIL_TO):
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = MAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            try:
                s.starttls()
            except Exception:
                pass
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, [MAIL_TO], msg.as_string())
        return True
    except Exception as e:
        print(f"Email Alert Error: {e}")
        return False
