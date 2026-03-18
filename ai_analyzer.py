from config import ai_client


def is_insightful(title, description):
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a news filter. Determine if the following news article provides meaningful insight about politics, economy, society, technology, environment, or global affairs. Exclude: crime/accidents, entertainment/celebrity, sports, weather, lifestyle/food. Reply ONLY with 'yes' or 'no'."},
            {"role": "user", "content": f"Title: {title}\nDescription: {description}"}
        ]
    )
    return response.choices[0].message.content.strip().lower() == "yes"


def summarize(title, description):
    response = ai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a news analyst. Summarize the following news article in Korean based on the title and description. Include: 1) 핵심 요약 (2-3 sentences) 2) 주요 키워드 (3-5 keywords) 3) 카테고리 (정치/경제/사회/기술/환경/건강 중 선택)"},
            {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"}
        ]
    )
    return response.choices[0].message.content
