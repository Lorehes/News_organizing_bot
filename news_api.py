import os
import time
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gdeltdoc import GdeltDoc, Filters
from newspaper import Article
from openai import OpenAI


load_dotenv()

mongo_client = MongoClient(
    host=os.getenv("MONGODB_HOST"),
    port=int(os.getenv("MONGODB_PORT"))
)

db = mongo_client['test']
collection = db['NewsText']

gd = GdeltDoc()

ai_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("GITHUB_TOKEN")
)


def get_articles(keywords, start_date, end_date, num_records=10, max_retries=5):
    f = Filters(
        keyword=keywords,
        start_date=start_date,
        end_date=end_date,
        num_records=num_records,
        domain="nytimes.com",
        country="US",
    )
    for attempt in range(max_retries):
        try:
            articles = gd.article_search(f)
            return articles
        except ValueError:
            if attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"GDELT 속도 제한 - {wait}초 대기 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


def crawl_texts(df: pd.DataFrame):
    results = []
    for _, row in df.iterrows():
        try:
            article = Article(row["url"])
            article.download()
            article.parse()
            results.append({
                "title": row["title"],
                "date": row["seendate"],
                "text": article.text,
            })
        except Exception:
            results.append({
                "title": row["title"],
                "date": row["seendate"],
                "text": "텍스트를 불러올 수 없습니다.",
            })
    return results


def summarize(title, text):
    response = ai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a news analyst. Summarize the following news article in Korean. Include: 1) 핵심 요약 (2-3 sentences) 2) 주요 키워드 (3-5 keywords) 3) 카테고리 (정치/경제/사회/기술/환경/건강 중 선택)"},
            {"role": "user", "content": f"Title: {title}\n\nArticle:\n{text}"}
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    keywords = ["trump", "biden", "climate change"]
    all_dfs = []

    for keyword in keywords:
        df = get_articles(keyword, yesterday, today)
        all_dfs.append(df)
        time.sleep(6)

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["url"])
    articles = crawl_texts(combined)

    for i, article in enumerate(articles):
        print(f"\n[{i+1}] {article['title']}")
        print("----------------")
        result = summarize(article["title"], article["text"])
        print(result)
        print("================")
