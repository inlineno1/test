# 카카오맵 장소 추출기 (Kakao Map Place Extractor)

카카오 로컬 REST API를 활용하여 장소 정보를 검색하고, CSV 또는 JSON 파일로 저장하는 CLI 도구입니다.

## 기능

- **키워드 검색** — 키워드로 장소 검색 (전체 페이지 자동 수집)
- **카테고리 검색** — 특정 좌표 기준 반경 내 카테고리별 장소 검색
- **주소 → 좌표 변환** — 주소를 입력하면 좌표 반환
- **좌표 → 주소 변환** — 좌표를 입력하면 주소 반환
- **CSV/JSON 내보내기** — 검색 결과를 파일로 저장

## 사전 준비

1. [카카오 개발자 사이트](https://developers.kakao.com)에서 앱을 생성합니다.
2. **앱 설정 > 카카오맵 > 사용 설정**을 ON으로 변경합니다.
3. 발급된 **REST API 키**를 준비합니다.

## 설치

```bash
pip install -r requirements.txt
```

## API 키 설정

환경변수로 설정하거나, 실행 시 직접 입력할 수 있습니다.

```bash
export KAKAO_REST_API_KEY="여기에_REST_API_키_입력"
```

## 사용법

### 키워드로 장소 검색

```bash
python kakao_map_extractor.py keyword "강남역 맛집"
```

### 키워드 검색 + 좌표/반경 제한

```bash
python kakao_map_extractor.py keyword "카페" --x 127.027 --y 37.498 --radius 2000
```

### 카테고리로 검색

```bash
python kakao_map_extractor.py category FD6 --x 127.027 --y 37.498 --radius 3000
```

### 주소 → 좌표 변환

```bash
python kakao_map_extractor.py address "서울 강남구 역삼동"
```

### 좌표 → 주소 변환

```bash
python kakao_map_extractor.py coord2addr --x 127.027 --y 37.498
```

### 결과를 파일로 저장

```bash
# CSV로 저장
python kakao_map_extractor.py keyword "서울 병원" -o hospitals.csv

# JSON으로 저장
python kakao_map_extractor.py keyword "판교 카페" -o cafes.json
```

### 카테고리 코드 목록 보기

```bash
python kakao_map_extractor.py categories
```

## 카테고리 코드 목록

| 코드 | 설명 |
|------|------|
| MT1 | 대형마트 |
| CS2 | 편의점 |
| PS3 | 어린이집, 유치원 |
| SC4 | 학교 |
| AC5 | 학원 |
| PK6 | 주차장 |
| OL7 | 주유소, 충전소 |
| SW8 | 지하철역 |
| BK9 | 은행 |
| CT1 | 문화시설 |
| AG2 | 중개업소 |
| PO3 | 공공기관 |
| AT4 | 관광명소 |
| AD5 | 숙박 |
| FD6 | 음식점 |
| CE7 | 카페 |
| HP8 | 병원 |
| PM9 | 약국 |

## 출력 필드

| 필드 | 설명 |
|------|------|
| id | 장소 ID |
| place_name | 장소명 |
| category_name | 카테고리 이름 |
| category_group_code | 카테고리 그룹 코드 |
| category_group_name | 카테고리 그룹 이름 |
| phone | 전화번호 |
| address_name | 지번 주소 |
| road_address_name | 도로명 주소 |
| x | 경도 (longitude) |
| y | 위도 (latitude) |
| place_url | 카카오맵 상세 페이지 URL |
| distance | 중심 좌표로부터 거리 (m) |
