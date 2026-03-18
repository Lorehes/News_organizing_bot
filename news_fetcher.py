import time
import feedparser
from gdeltdoc import GdeltDoc, Filters
from config import (
    newsapi, NEWSAPI_SOURCES, NEWSAPI_DOMAINS,
    RSS_SOURCES, GDELT_SOURCES,
)
from ai_analyzer import extract_keywords

gd = GdeltDoc()


def fetch_from_newsapi(from_date, to_date):
    response = newsapi.get_everything(
        domains=NEWSAPI_DOMAINS,
        from_param=from_date,
        to=to_date,
        language="en",
        sort_by="publishedAt",
        page_size=100,
    )
    articles = []
    for a in response.get("articles", []):
        articles.append({
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "source": a.get("source", {}).get("name", ""),
            "published": a.get("publishedAt", ""),
        })
    return articles


def fetch_from_rss(source):
    feed = feedparser.parse(source["rss"])
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": entry.get("title", ""),
            "description": entry.get("summary", ""),
            "url": entry.get("link", ""),
            "source": source["domain"],
            "published": entry.get("published", ""),
        })
    return articles


def fetch_from_gdelt(source, from_date, to_date, keywords=None):
    """여러 키워드로 GDELT 검색 후 중복 제거하여 반환"""
    if keywords is None:
        keywords = ["economy", "politics", "technology"]

    seen_urls = set()
    articles = []

    for keyword in keywords:
        f = Filters(
            keyword=keyword,
            start_date=from_date,
            end_date=to_date,
            domain=source["domain"],
            num_records=10,
        )
        try:
            df = gd.article_search(f)
            for _, row in df.iterrows():
                url = row.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                articles.append({
                    "title": row.get("title", ""),
                    "description": row.get("title", ""),
                    "url": url,
                    "source": source["domain"],
                    "published": row.get("seendate", ""),
                })
        except ValueError:
            pass
        time.sleep(6)

    return articles


def fetch_all(from_date, to_date):
    """NewsAPI + RSS + GDELT 혼합 수집"""
    domain_articles = {}

    # 1) NewsAPI 수집
    newsapi_articles = fetch_from_newsapi(from_date, to_date)
    for a in newsapi_articles:
        for s in NEWSAPI_SOURCES:
            if s["domain"] in a["url"]:
                domain_articles.setdefault(s["domain"], []).append(a)
                break
    for s in NEWSAPI_SOURCES:
        count = len(domain_articles.get(s["domain"], []))
        print(f"  [NewsAPI] {s['domain']}: {count}건")

    # 2) RSS 수집
    for source in RSS_SOURCES:
        try:
            rss_articles = fetch_from_rss(source)
            domain_articles[source["domain"]] = rss_articles
            print(f"  [RSS] {source['domain']}: {len(rss_articles)}건")
        except Exception:
            print(f"  [RSS 실패] {source['domain']}")

    # 3) 1단계 기사에서 동적 키워드 추출
    tier1_articles = []
    for s in NEWSAPI_SOURCES:
        if s["tier"] == 1:
            tier1_articles.extend(domain_articles.get(s["domain"], []))
    for s in RSS_SOURCES:
        if s["tier"] <= 2:
            tier1_articles.extend(domain_articles.get(s["domain"], []))

    if tier1_articles:
        print("\n  [AI] 1단계 기사에서 키워드 추출 중...")
        keywords = extract_keywords(tier1_articles)
        print(f"  [AI] 추출된 키워드: {keywords}")
    else:
        keywords = None
        print("  [AI] 1단계 기사 없음 → 기본 키워드 사용")

    # 4) GDELT 수집 (동적 키워드 사용)
    for source in GDELT_SOURCES:
        articles = fetch_from_gdelt(source, from_date, to_date, keywords=keywords)
        domain_articles[source["domain"]] = articles
        print(f"  [GDELT] {source['domain']}: {len(articles)}건")

    return domain_articles
