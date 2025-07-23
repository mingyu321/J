import requests
from bs4 import BeautifulSoup
import time
import mysql.connector # MySQL 연결을 위한 라이브러리

# 1. 설정
BASE_URL = "https://zdnet.co.kr"
LIST_URL = f"{BASE_URL}/news/?lstcode=0020&page=1"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# MySQL 데이터베이스 연결 설정
DB_CONFIG = {
    'host': 'localhost',       # 예: 'localhost' 또는 '127.0.0.1'
    'user': 'root',       # 예: 'root'
    'password': '', # MySQL 비밀번호
    'database': 'mysql-container' # 미리 생성된 데이터베이스 이름 (예: 'crawling_db')
}

def get_article_links(list_url):
    """뉴스 목록 페이지에서 기사 링크 추출"""
    res = requests.get(list_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.select("div.newsPost")

    article_info_list = []
    for article in articles:
        try:
            title = article.select_one("h3").text.strip()
            summary = article.select_one("p").text.strip()
            relative_link = article.select_one("a")["href"]
            article_url = BASE_URL + relative_link
            date = article.select_one("p.byline span").text.strip()
            reporter_element = article.select_one("p.byline a")
            reporter = reporter_element.text.strip() if reporter_element else "N/A" # 기자가 없는 경우 처리
            image = article.select_one("img")["data-src"]

            article_info_list.append({
                "title": title,
                "summary": summary,
                "url": article_url,
                "date": date,
                "reporter": reporter,
                "image": image
            })
        except Exception as e:
            print("Error parsing article block:", e)
    return article_info_list

def get_article_content(article_url):
    """개별 기사 페이지에서 본문 내용 추출"""
    res = requests.get(article_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    content_div = soup.select_one("div.view_cont")
    if content_div:
        paragraphs = content_div.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        return content
    return "본문 없음"

def create_table_if_not_exists(cursor):
    """크롤링 데이터를 저장할 테이블 생성 (테이블이 없으면)"""
    # MySQL의 VARCHAR(255)는 255자까지 저장 가능하며, TEXT는 긴 텍스트 저장에 용이
    table_create_query = """
    CREATE TABLE IF NOT EXISTS articles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
        summary TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        url VARCHAR(1000) NOT NULL UNIQUE,
        date VARCHAR(100),
        reporter VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        image_url VARCHAR(1000),
        content LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """
    cursor.execute(table_create_query)
    print("Table 'articles' checked/created successfully.")

def insert_article_data(cursor, article_data):
    """크롤링된 기사 데이터를 테이블에 삽입"""
    insert_query = """
    INSERT INTO articles (title, summary, url, date, reporter, image_url, content)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        title=VALUES(title), summary=VALUES(summary), date=VALUES(date),
        reporter=VALUES(reporter), image_url=VALUES(image_url), content=VALUES(content);
    """
    # ON DUPLICATE KEY UPDATE를 사용하여, URL이 중복될 경우 기존 데이터를 업데이트합니다.
    # 이는 재크롤링 시 동일한 기사가 중복으로 저장되는 것을 방지합니다.

    try:
        cursor.execute(insert_query, (
            article_data['title'],
            article_data['summary'],
            article_data['url'],
            article_data['date'],
            article_data['reporter'],
            article_data['image'],
            article_data['content']
        ))
        print(f"Data for '{article_data['title']}' inserted/updated successfully.")
    except mysql.connector.Error as err:
        print(f"Error inserting data for '{article_data['title']}': {err}")

# 2. 실행
if __name__ == "__main__":
    conn = None # 연결 객체 초기화
    try:
        # DB 연결
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 테이블 생성
        create_table_if_not_exists(cursor)

        articles = get_article_links(LIST_URL)

        for i, article in enumerate(articles, 1):
            print(f"[{i}] Processing: {article['title']}")
            article_content = get_article_content(article['url'])
            article['content'] = article_content # 본문 내용을 딕셔너리에 추가

            insert_article_data(cursor, article)
            conn.commit() # 변경사항을 DB에 반영

            # 너무 빠른 요청을 방지하기 위해 잠시 대기
            time.sleep(2) # 5초에서 2초로 줄여 빠르게 테스트 가능, 실제 운영 시에는 더 길게 설정 고려

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection closed.")