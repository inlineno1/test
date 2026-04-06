# KOSPI 시가총액 순위 웹사이트

네이버 금융에서 코스피 시가총액 상위 종목 데이터를 스크래핑하여 깔끔한 웹 UI로 보여주는 Flask 기반 웹 애플리케이션입니다.

## 기능

- 코스피 시가총액 상위 종목 표시 (순위, 종목명, 현재가, 등락, 등락률, 시가총액)
- 종목명 검색 필터링
- 새로고침으로 실시간 데이터 갱신
- 종목 클릭 시 네이버 금융 상세 페이지로 이동
- 반응형 다크 테마 UI

## 실행 방법

```bash
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5000` 으로 접속합니다.

## 기술 스택

- **백엔드**: Python, Flask, BeautifulSoup4, Requests
- **프론트엔드**: HTML5, CSS3, Vanilla JavaScript
- **데이터 출처**: 네이버 금융 (finance.naver.com)