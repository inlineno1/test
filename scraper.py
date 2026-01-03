import sys
import requests
from bs4 import BeautifulSoup

def scrape_naver_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 뉴스 검색 결과 리스트 아이템 선택
        # 1. 기존에 알려진 news_tit 클래스 시도
        news_items = soup.select(".news_tit")
        
        # 2. news_tit가 없으면 최신 UI 클래스 시도 (동적 클래스일 수 있으므로 주의)
        if not news_items:
            # 관찰된 제목 클래스 패턴: fender-ui... yuu64AGiOBzaFbBUUZbL
            # yuu64... 클래스를 사용
            news_items = soup.select("a.yuu64AGiOBzaFbBUUZbL")

        print(f"'{keyword}' 검색 결과:")
        if not news_items:
            print("뉴스를 찾을 수 없습니다. (HTML 구조가 변경되었을 수 있습니다)")
            return

        for item in news_items:
            title = item.get_text()
            link = item['href']
            print(f"- {title} ({link})")

    except requests.exceptions.RequestException as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:])
    else:
        keyword = input("검색할 키워드를 입력하세요: ")
    scrape_naver_news(keyword)
