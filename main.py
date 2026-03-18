import sys
from datetime import datetime, timedelta
from config import ALL_SOURCES
from news_fetcher import fetch_all
from ai_analyzer import filter_and_summarize, SKIP

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None


if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print("=== 뉴스 수집 중 ===\n")
    domain_articles = fetch_all(yesterday, today)

    print("\n=== AI 분석 시작 ===\n")

    # 티어 순서대로 처리 (낮은 티어 = 높은 우선순위)
    count = 0
    rate_limited = False
    for src in ALL_SOURCES:
        if rate_limited:
            break

        domain = src["domain"]
        target = src["count"]
        filled = 0

        for article in domain_articles.get(domain, []):
            if filled >= target:
                break

            title = article["title"]
            description = article.get("description", "")
            source_name = article["source"]

            try:
                result = filter_and_summarize(title, description)
            except Exception as e:
                if "429" in str(e) or "RateLimit" in str(e):
                    print(f"\n[!] API 일일 한도 초과 — 분석 중단")
                    rate_limited = True
                    break
                continue

            if result == SKIP:
                continue

            filled += 1
            count += 1
            print(f"\n[{count}] [Tier {src['tier']}] [{source_name}] {title}")
            print("----------------")
            print(result)
            print("================")

        if filled > 0:
            print(f"  → {domain}: {filled}/{target}건 완료")

    if rate_limited:
        print(f"\n총 {count}건 분석 완료 (API 한도 초과로 중단됨)")
    else:
        print(f"\n총 {count}건 인사이트 기사 요약 완료")
