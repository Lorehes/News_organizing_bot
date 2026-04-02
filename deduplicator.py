from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from dateutil import parser as dateutil_parser

from collector import Article


def _parse_date(date_str: str) -> datetime | None:
    """다양한 날짜 형식 파싱 (RFC 2822, ISO 8601 등)"""
    if not date_str or not date_str.strip():
        return None
    # 1차: RFC 2822 (RSS 표준)
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    # 2차: ISO 8601 및 기타 형식 (dateutil)
    try:
        dt = dateutil_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


KST = timezone(timedelta(hours=9))


def filter_recent(articles: list[Article]) -> list[Article]:
    """전날 오전 8시(KST) ~ 오늘 오전 8시(KST) 기사만 유지"""
    now_kst = datetime.now(KST)
    today_8am = now_kst.replace(hour=8, minute=0, second=0, microsecond=0)
    # 현재가 오전 8시 이전이면 기준을 하루 더 앞으로
    if now_kst < today_8am:
        today_8am -= timedelta(days=1)
    cutoff = today_8am - timedelta(days=1)

    recent = []
    for a in articles:
        dt = _parse_date(a.published_at)
        if dt is None:
            recent.append(a)  # 날짜 파싱 실패 시 포함
        elif dt >= cutoff:
            recent.append(a)
    print(f"[시간 필터] {len(articles)}건 → {len(recent)}건 ({cutoff.strftime('%m/%d %H:%M')}~{today_8am.strftime('%m/%d %H:%M')} KST)")
    return recent


def deduplicate(articles: list[Article], threshold: float = 0.85) -> list[Article]:
    """TF-IDF 코사인 유사도로 중복 제거 (제목 + 본문 앞부분 결합)"""
    if len(articles) <= 1:
        return articles

    # 제목 + 본문 앞 100자 결합으로 의미적 중복 판단 강화
    texts = [f"{a.title} {a.content[:100]}" for a in articles]
    tfidf = TfidfVectorizer(stop_words="english").fit_transform(texts)
    sim = cosine_similarity(tfidf)

    keep = []
    removed = set()
    for i in range(len(articles)):
        if i in removed:
            continue
        keep.append(articles[i])
        for j in range(i + 1, len(articles)):
            if sim[i][j] >= threshold:
                removed.add(j)  # 유사 기사 제거

    print(f"[중복 제거] {len(articles)}건 → {len(keep)}건 (중복 {len(articles) - len(keep)}건 제거)")
    return keep


def clean(articles: list[Article]) -> list[Article]:
    articles = filter_recent(articles)
    articles = deduplicate(articles)
    return articles
