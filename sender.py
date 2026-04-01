from __future__ import annotations

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_email(briefing_text: str, article_count: dict):
    today = datetime.now().strftime("%Y.%m.%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[글로벌 브리핑] {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    body = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
글로벌 뉴스 인텔리전스 브리핑 — {today}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{briefing_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수집: {article_count['collected']}건 → 정제: {article_count['cleaned']}건 → 분석: {article_count['top']}건
생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")} KST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASSWORD"])
            server.send_message(msg)
        print("[발송 완료] 이메일 전송 성공")
    except Exception as e:
        # fallback: 로컬 파일 저장
        filename = f"briefing_{today}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"[발송 실패] 로컬 저장: {filename} — 오류: {e}")
