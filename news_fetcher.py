from config import newsapi, NEWS_SOURCES, NEWS_DOMAINS


def get_articles(from_date, to_date, page_size=100):
    response = newsapi.get_everything(
        domains=NEWS_DOMAINS,
        from_param=from_date,
        to=to_date,
        language="en",
        sort_by="publishedAt",
        page_size=page_size,
    )
    return response.get("articles", [])


def group_by_domain(articles):
    domain_articles = {}
    for article in articles:
        url = article.get("url", "")
        for s in NEWS_SOURCES:
            if s["domain"] in url:
                domain_articles.setdefault(s["domain"], []).append(article)
                break
    return domain_articles
