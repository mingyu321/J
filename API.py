from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

# MySQL 데이터베이스 연결 설정 (이전 크롤링 코드와 동일하게 본인 정보로 업데이트)
DB_CONFIG = {
    'host': 'localhost',        # 예: 'localhost' 또는 컨테이너 IP
    'user': 'root',             # 예: 'root' 또는 다른 MySQL 사용자
    'password': '',# MySQL 비밀번호 (이전에 설정한 값)
    'database': 'YOUR_DATABASE' # 미리 생성해 둔 데이터베이스 이름 (예: 'crawling_db')
}

@app.route('/articles', methods=['GET'])
def get_articles():
    """
    데이터베이스에서 모든 기사 데이터를 조회하여 JSON 형태로 반환합니다.
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True) # 딕셔너리 형태로 결과를 받기 위해 dictionary=True 설정

        query = "SELECT id, title, summary, url, date, reporter, image_url, content FROM articles"
        cursor.execute(query)
        articles = cursor.fetchall() # 모든 결과 가져오기

        return jsonify(articles)

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return jsonify({"error": "Database connection or query failed", "details": str(err)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection closed.")

if __name__ == '__main__':
    # Flask 앱 실행
    # debug=True는 개발 중에 유용하며, 코드 변경 시 서버가 자동으로 재시작됩니다.
    # 실제 운영 환경에서는 debug=False로 설정해야 합니다.
    app.run(debug=True, host='0.0.0.0', port=5000)