from datetime import datetime, timedelta
from config import NEWS_SOURCES
from news_fetcher import get_articles, group_by_domain
from ai_analyzer import is_insightful, summarize


if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    all_articles = get_articles(yesterday, today)
    print(f"총 {len(all_articles)}건 수집\n")

    domain_articles = group_by_domain(all_articles)

    # 티어 순서대로 처리 (낮은 티어 = 높은 우선순위)
    count = 0
    for src in sorted(NEWS_SOURCES, key=lambda s: s["tier"]):
        domain = src["domain"]
        target = src["count"]
        filled = 0

        for article in domain_articles.get(domain, []):
            if filled >= target:
                break

            title = article["title"]
            description = article.get("description", "")
            source_name = article["source"]["name"]

            try:
                if not is_insightful(title, description):
                    continue
            except Exception:
                continue

            filled += 1
            count += 1
            print(f"\n[{count}] [Tier {src['tier']}] [{source_name}] {title}")
            print("----------------")
            try:
                result = summarize(title, description)
                print(result)
            except Exception:
                print("[건너뜀] 콘텐츠 필터에 의해 요약할 수 없는 기사입니다.")
            print("================")

        if filled > 0:
            print(f"  → {domain}: {filled}/{target}건 완료")

    print(f"\n총 {count}건 인사이트 기사 요약 완료")
