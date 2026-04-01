from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from collector import Article


def filter_recent(articles: list[Article], hours: int = 24) -> list[Article]:
    """24시간 이내 기사만 유지"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for a in articles:
        try:
            pub = parsedate_to_datetime(a.published_at)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                recent.append(a)
        except Exception:
            recent.append(a)  # 날짜 파싱 실패 시 포함
    print(f"[시간 필터] {len(articles)}건 → {len(recent)}건 (24시간 이내)")
    return recent


def deduplicate(articles: list[Article], threshold: float = 0.85) -> list[Article]:
    """TF-IDF 코사인 유사도로 중복 제거"""
    if len(articles) <= 1:
        return articles

    titles = [a.title for a in articles]
    tfidf = TfidfVectorizer(stop_words="english").fit_transform(titles)
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
