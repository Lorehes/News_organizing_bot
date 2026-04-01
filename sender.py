from __future__ import annotations

import re
import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _validate_env():
    """필수 환경변수 존재 확인"""
    required = ["EMAIL_FROM", "EMAIL_TO", "EMAIL_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"환경변수 누락: {', '.join(missing)} — .env 파일을 확인하세요")


def _markdown_to_html(text: str) -> str:
    """마크다운 텍스트를 간단한 HTML로 변환"""
    lines = text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
            continue

        # 제목 (## / ###)
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h3 style="color:#1a5276;margin:18px 0 8px 0;">{stripped[4:]}</h3>')
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h2 style="color:#154360;margin:24px 0 10px 0;border-bottom:2px solid #2c3e50;padding-bottom:4px;">{stripped[3:]}</h2>')
            continue

        # 구분선
        if stripped == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<hr style="border:1px solid #bdc3c7;margin:16px 0;">')
            continue

        # 리스트 항목
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append('<ul style="margin:4px 0;">')
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
            continue

        # 번호 리스트 (1. 2. 등)
        if re.match(r'^\d+\.\s', stripped):
            content = re.sub(r'^\d+\.\s', '', stripped)
            html_lines.append(f'<p style="margin:4px 0;"><strong>{stripped[:stripped.index(" ")]}</strong> {content}</p>')
            continue

        # 일반 텍스트
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f'<p style="margin:4px 0;line-height:1.6;">{stripped}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _linkify(html: str) -> str:
    """URL을 클릭 가능한 링크로 변환"""
    url_pattern = r'(https?://[^\s<>"\']+)'
    return re.sub(url_pattern, r'<a href="\1" style="color:#2980b9;">\1</a>', html)


def send_email(briefing_text: str, article_count: dict, max_retries: int = 3):
    _validate_env()

    today = datetime.now().strftime("%Y.%m.%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[글로벌 브리핑] {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]

    # plain text 버전 (fallback)
    plain_body = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
글로벌 뉴스 인텔리전스 브리핑 — {today}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{briefing_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수집: {article_count['collected']}건 → 정제: {article_count['cleaned']}건 → 분석: {article_count['top']}건
생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")} KST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # HTML 버전
    briefing_html = _linkify(_markdown_to_html(briefing_text))
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:700px;margin:0 auto;padding:20px;color:#2c3e50;font-size:15px;">
  <div style="background:#1a5276;color:white;padding:16px 20px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:20px;">글로벌 뉴스 인텔리전스 브리핑</h1>
    <p style="margin:4px 0 0 0;opacity:0.85;font-size:14px;">{today}</p>
  </div>
  <div style="padding:16px 20px;border:1px solid #d5dbdb;border-top:none;border-radius:0 0 8px 8px;">
    {briefing_html}
  </div>
  <div style="margin-top:16px;padding:12px 20px;background:#f2f4f4;border-radius:6px;font-size:13px;color:#7f8c8d;">
    수집: {article_count['collected']}건 → 정제: {article_count['cleaned']}건 → 분석: {article_count['top']}건<br>
    생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")} KST
  </div>
</body>
</html>"""

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    last_error = None
    for attempt in range(max_retries):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASSWORD"])
                server.send_message(msg)
            print("[발송 완료] 이메일 전송 성공")
            return
        except Exception as e:
            last_error = e
            print(f"[발송 실패] 시도 {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    # 모든 재시도 실패 → 로컬 파일 저장
    filename = f"briefing_{today}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(plain_body)
    print(f"[발송 포기] {max_retries}회 실패 → 로컬 저장: {filename} — 오류: {last_error}")
