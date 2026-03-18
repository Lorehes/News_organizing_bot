import os
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gdeltdoc import GdeltDoc, Filters
from newspaper import Article
from openai import OpenAI

load_dotenv()

client = MongoClient(
    host=os.getenv("MONGODB_HOST"),
    port=int(os.getenv("MONGODB_PORT"))
)

db = client['test']

collection = db['NewsText']

gd = GdeltDoc()

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("GITHUB_TOKEN")
)


def get_articles(keywords, start_date, end_date, num_records=10, max_retries=3):
    f = Filters(
        keyword=keywords,
        start_date=start_date,
        end_date=end_date,
        num_records=num_records,
    )
    for attempt in range(max_retries):
        try:
            articles = gd.article_search(f)
            return articles
        except ValueError:
            if attempt < max_retries - 1:
                wait = 6 * (attempt + 1)
                print(f"GDELT 속도 제한 - {wait}초 대기 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


def crawl_texts(df):
    texts = []
    for _, row in df.iterrows():
        try:
            article = Article(row["url"])
            article.download()
            article.parse()
            texts.append(article.text)
        except Exception:
            texts.append("텍스트를 불러올 수 없습니다.")
    return texts


def summarize(title, text):
    response = client.chat.completions.create(
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

    df = get_articles("climate change", yesterday, today)
    texts = crawl_texts(df)

    for i, text in enumerate(texts):
        title = df.iloc[i]["title"]
        print(f"\n[{i+1}] {title}")
        print("----------------")
        result = summarize(title, text)
        print(result)
        print("================")
