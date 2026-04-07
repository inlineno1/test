"""
일본 여행 데이터 수집 스크립트
- Tabelog: 도시별 맛집 데이터 스크래핑
- Google Places API: 도시별 관광지 데이터 조회
"""

import json
import os
import sys
import time
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

CITY_CONFIG = {
    "fukuoka": {
        "name_ko": "후쿠오카",
        "name_ja": "福岡",
        "region": "kyushu",
        "description": "규슈의 관문, 일본 라멘과 야타이의 성지",
        "airport": "FUK",
        "tabelog_prefecture": "fukuoka",
        "tabelog_area": "A4001",
        "center_lat": 33.5904,
        "center_lng": 130.4017,
        "places_query_spots": [
            "후쿠오카 인기 관광지",
            "하카타 관광 명소",
            "후쿠오카 신사 공원",
        ],
    },
    "nagasaki": {
        "name_ko": "나가사키",
        "name_ja": "長崎",
        "region": "kyushu",
        "description": "이국적인 분위기와 역사가 공존하는 항구 도시",
        "tabelog_prefecture": "nagasaki",
        "tabelog_area": "A4201",
        "center_lat": 32.7503,
        "center_lng": 129.8779,
        "places_query_spots": [
            "나가사키 관광 명소",
            "나가사키 역사 유적",
        ],
    },
    "osaka": {
        "name_ko": "오사카",
        "name_ja": "大阪",
        "region": "kansai",
        "description": "맛의 도시, 쿠이다오레 문화의 본고장",
        "airport": "KIX",
        "tabelog_prefecture": "osaka",
        "tabelog_area": "A2701",
        "center_lat": 34.6937,
        "center_lng": 135.5023,
        "places_query_spots": [
            "오사카 인기 관광지",
            "오사카 쇼핑 명소",
        ],
    },
    "tokyo": {
        "name_ko": "도쿄",
        "name_ja": "東京",
        "region": "kanto",
        "description": "일본의 수도, 전통과 현대가 조화로운 메가시티",
        "airport": "NRT",
        "tabelog_prefecture": "tokyo",
        "tabelog_area": None,
        "center_lat": 35.6762,
        "center_lng": 139.6503,
        "places_query_spots": [
            "도쿄 인기 관광지",
            "도쿄 신사 사찰",
        ],
    },
    "kyoto": {
        "name_ko": "교토",
        "name_ja": "京都",
        "region": "kansai",
        "description": "천년 고도, 일본 전통문화의 중심지",
        "tabelog_prefecture": "kyoto",
        "tabelog_area": "A2601",
        "center_lat": 35.0116,
        "center_lng": 135.7681,
        "places_query_spots": [
            "교토 인기 관광지",
            "교토 사찰 신사",
        ],
    },
    "beppu": {
        "name_ko": "벳푸",
        "name_ja": "別府",
        "region": "kyushu",
        "description": "일본 최대의 온천 도시",
        "tabelog_prefecture": "oita",
        "tabelog_area": "A4402",
        "center_lat": 33.2846,
        "center_lng": 131.4914,
        "places_query_spots": [
            "벳푸 온천 관광",
            "별부 지옥 온천",
        ],
    },
    "kumamoto": {
        "name_ko": "구마모토",
        "name_ja": "熊本",
        "region": "kyushu",
        "description": "구마몬의 고장, 웅장한 구마모토 성의 도시",
        "tabelog_prefecture": "kumamoto",
        "tabelog_area": "A4301",
        "center_lat": 32.8032,
        "center_lng": 130.7079,
        "places_query_spots": [
            "구마모토 관광 명소",
        ],
    },
    "yufuin": {
        "name_ko": "유후인",
        "name_ja": "由布院",
        "region": "kyushu",
        "description": "그림 같은 온천 마을, 유후다케 산 아래 아기자기한 거리",
        "tabelog_prefecture": "oita",
        "tabelog_area": "A4402",
        "tabelog_keyword": "由布院",
        "center_lat": 33.2672,
        "center_lng": 131.3650,
        "places_query_spots": [
            "유후인 관광 명소",
        ],
    },
}


# ─────────────────────────────────────────────
#  Tabelog Scraper
# ─────────────────────────────────────────────

TABELOG_SORT_OPTIONS = [
    ("inbound_most_reserved", "여행자 예약순"),
    ("rt", "평점순"),
]

TABELOG_CATEGORY_MAP = {
    "라멘": "라멘", "ramen": "라멘",
    "스시": "스시", "sushi": "스시", "초밥": "스시",
    "야키니쿠": "야키니쿠", "yakiniku": "야키니쿠",
    "야키토리": "야키토리", "yakitori": "야키토리",
    "이자카야": "이자카야", "izakaya": "이자카야",
    "내장전골": "모츠나베", "모츠나베": "모츠나베", "motsu": "모츠나베",
    "덴푸라": "텐푸라", "tempura": "텐푸라", "튀김": "텐푸라",
    "우동": "우동", "udon": "우동",
    "프렌치": "프렌치", "french": "프렌치",
    "이탈리안": "이탈리안", "italian": "이탈리안",
    "일본 요리": "일본 요리", "japanese": "일본 요리", "카이세키": "일본 요리",
    "해물": "해산물", "seafood": "해산물",
    "카페": "카페", "cafe": "카페",
    "돈카츠": "돈카츠", "tonkatsu": "돈카츠",
    "오코노미야키": "오코노미야키",
    "타코야키": "타코야키",
    "짬뽕": "짬뽕", "champon": "짬뽕",
    "덮밥": "덮밥", "donburi": "덮밥",
    "중화요리": "중화요리", "chinese": "중화요리",
    "닭 요리": "닭요리", "chicken": "닭요리",
    "카레": "카레", "curry": "카레",
    "소바": "소바", "soba": "소바",
    "규동": "규동",
    "경양식": "경양식",
    "디저트": "디저트", "케이크": "디저트",
    "빵": "베이커리", "베이커리": "베이커리", "bakery": "베이커리",
}


def normalize_category(raw_category):
    """카테고리 문자열에서 주요 카테고리를 추출"""
    raw_lower = raw_category.lower()
    for keyword, mapped in TABELOG_CATEGORY_MAP.items():
        if keyword in raw_lower:
            return mapped
    return raw_category.split(",")[0].strip() if raw_category else "기타"


def parse_price(price_text):
    """가격 텍스트를 정리"""
    if not price_text or price_text.strip() == "-":
        return ""
    return price_text.strip()


def scrape_tabelog_list(prefecture, area=None, sort_key="inbound_most_reserved",
                        lang="kr", keyword=None, max_items=15):
    """Tabelog 리스트 페이지 스크래핑"""
    if area:
        base_url = f"https://tabelog.com/{lang}/{prefecture}/{area}/rstLst/"
    else:
        base_url = f"https://tabelog.com/{lang}/{prefecture}/rstLst/"

    params = {"Srt": "D", "SrtT": sort_key, "sort_mode": "1"}
    if keyword:
        params["LstKind"] = "01"
        params["sw"] = keyword

    restaurants = []
    try:
        resp = requests.get(base_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".list-rst")

        for item in items[:max_items]:
            name_el = item.select_one(".list-rst__rst-name-target")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            link = name_el.get("href", "")

            area_genre_el = item.select_one(".list-rst__area-genre")
            area_genre = area_genre_el.get_text(strip=True) if area_genre_el else ""

            station = ""
            category = ""
            if "/" in area_genre:
                parts = area_genre.split("/", 1)
                station = parts[0].strip()
                category = parts[1].strip()
            else:
                category = area_genre

            rating_el = item.select_one(".c-rating__val")
            rating = rating_el.get_text(strip=True) if rating_el else ""

            prices = item.select(".c-rating-v3__val")
            dinner_price = parse_price(prices[0].get_text(strip=True)) if len(prices) > 0 else ""
            lunch_price = parse_price(prices[1].get_text(strip=True)) if len(prices) > 1 else ""

            price_display = lunch_price or dinner_price
            if lunch_price and dinner_price:
                price_display = f"점심 {lunch_price} / 저녁 {dinner_price}"

            pr_el = item.select_one(".list-rst__pr-title")
            description = pr_el.get_text(strip=True) if pr_el else ""

            restaurants.append({
                "name": name,
                "category": normalize_category(category),
                "raw_category": category,
                "rating": rating,
                "price_range": price_display,
                "station": station,
                "description": description,
                "tabelog_url": link,
                "source": "tabelog",
            })

    except requests.RequestException as e:
        print(f"  ⚠️  Tabelog 요청 실패 ({prefecture}/{area}): {e}")

    return restaurants


def scrape_tabelog_detail(url):
    """Tabelog 상세 페이지에서 영업시간, 주소 등 추가 정보 스크래핑"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        info = {}

        rstinfo_table = soup.select_one("#rst-data-head")
        if rstinfo_table:
            rows = rstinfo_table.select("tr")
            for row in rows:
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td:
                    key = th.get_text(strip=True)
                    val = td.get_text(strip=True)
                    if "주소" in key or "住所" in key or "address" in key.lower():
                        info["address"] = val
                    elif "영업" in key or "시간" in key or "営業" in key:
                        info["hours"] = val
                    elif "정기" in key or "정휴" in key or "定休" in key or "holiday" in key.lower():
                        info["holiday"] = val

        name_ja_el = soup.select_one(".rd-header__rst-name-ja")
        if name_ja_el:
            info["name_ja"] = name_ja_el.get_text(strip=True)

        return info
    except requests.RequestException:
        return {}


def fetch_tabelog_restaurants(city_key, config, max_per_sort=10, fetch_details=True):
    """도시별 Tabelog 식당 데이터 수집"""
    print(f"\n🍽️  [{config['name_ko']}] Tabelog 맛집 수집 중...")

    all_restaurants = {}
    prefecture = config["tabelog_prefecture"]
    area = config.get("tabelog_area")
    keyword = config.get("tabelog_keyword")

    for sort_key, sort_label in TABELOG_SORT_OPTIONS:
        print(f"   정렬: {sort_label} ({sort_key})")
        items = scrape_tabelog_list(
            prefecture, area, sort_key,
            lang="kr", keyword=keyword, max_items=max_per_sort
        )
        print(f"   → {len(items)}개 식당 수집")

        for item in items:
            key = item["tabelog_url"] or item["name"]
            if key not in all_restaurants:
                all_restaurants[key] = item

        time.sleep(1.5)

    restaurants = list(all_restaurants.values())

    if fetch_details and restaurants:
        print(f"   📋 상세 정보 수집 중 (최대 {min(len(restaurants), 15)}개)...")
        for i, r in enumerate(restaurants[:15]):
            if r.get("tabelog_url"):
                kr_url = r["tabelog_url"]
                detail = scrape_tabelog_detail(kr_url)
                if detail:
                    r.update({k: v for k, v in detail.items() if v})
                time.sleep(1.0)
                if (i + 1) % 5 == 0:
                    print(f"      {i + 1}/{min(len(restaurants), 15)} 완료")

    print(f"   ✅ 총 {len(restaurants)}개 식당 수집 완료")
    return restaurants


# ─────────────────────────────────────────────
#  Google Places API
# ─────────────────────────────────────────────

def search_google_places(query, location_lat, location_lng, api_key, max_results=10, lang="ko"):
    """Google Places API Text Search로 장소 검색"""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.userRatingCount,places.types,"
            "places.regularOpeningHours,places.editorialSummary,"
            "places.googleMapsUri,places.primaryTypeDisplayName"
        ),
    }
    body = {
        "textQuery": query,
        "languageCode": lang,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": location_lat,
                    "longitude": location_lng,
                },
                "radius": 30000.0,
            }
        },
        "pageSize": max_results,
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("places", [])
    except requests.RequestException as e:
        print(f"  ⚠️  Google Places API 요청 실패: {e}")
        return []


def parse_google_place(place):
    """Google Places API 응답을 내부 포맷으로 변환"""
    display_name = place.get("displayName", {})
    name = display_name.get("text", "")

    location = place.get("location", {})
    lat = location.get("latitude", 0)
    lng = location.get("longitude", 0)

    rating = place.get("rating", 0)
    user_rating_count = place.get("userRatingCount", 0)

    types = place.get("types", [])
    primary_type = place.get("primaryTypeDisplayName", {}).get("text", "")

    editorial = place.get("editorialSummary", {}).get("text", "")

    hours_info = place.get("regularOpeningHours", {})
    weekday_texts = hours_info.get("weekdayDescriptions", [])
    hours_str = ""
    if weekday_texts:
        hours_str = weekday_texts[0] if len(weekday_texts) == 1 else "; ".join(weekday_texts[:2]) + "..."

    category = classify_spot_type(types, primary_type)

    return {
        "name": name,
        "type": "attraction",
        "category": category,
        "hours": hours_str or "영업시간 확인 필요",
        "duration_min": estimate_duration(types),
        "description": editorial or f"{name} - {primary_type}",
        "lat": lat,
        "lng": lng,
        "rating": rating,
        "user_rating_count": user_rating_count,
        "google_maps_uri": place.get("googleMapsUri", ""),
        "source": "google_places",
    }


TYPE_CATEGORY_MAP = {
    "shrine": "신사",
    "buddhist_temple": "사찰",
    "temple": "사찰",
    "church": "교회/성당",
    "museum": "박물관",
    "art_gallery": "미술관",
    "park": "자연/공원",
    "garden": "정원",
    "zoo": "동물원",
    "aquarium": "수족관",
    "amusement_park": "테마파크",
    "shopping_mall": "쇼핑",
    "market": "시장/먹거리",
    "castle": "역사/성",
    "historical_landmark": "역사/문화",
    "landmark": "랜드마크",
    "observation_deck": "전망대",
    "tower": "전망대",
    "beach": "자연/해변",
    "hot_spring": "온천",
    "spa": "온천",
    "night_club": "야경/엔터테인먼트",
    "tourist_attraction": "관광",
}

DURATION_MAP = {
    "amusement_park": 300,
    "museum": 90,
    "art_gallery": 90,
    "zoo": 150,
    "aquarium": 120,
    "park": 60,
    "shopping_mall": 120,
    "market": 90,
    "shrine": 40,
    "buddhist_temple": 60,
    "castle": 90,
}


def classify_spot_type(types, primary_type):
    for t in types:
        if t in TYPE_CATEGORY_MAP:
            return TYPE_CATEGORY_MAP[t]
    if primary_type:
        return primary_type
    return "관광"


def estimate_duration(types):
    for t in types:
        if t in DURATION_MAP:
            return DURATION_MAP[t]
    return 60


def fetch_google_spots(city_key, config, api_key):
    """도시별 Google Places 관광지 데이터 수집"""
    print(f"\n📍 [{config['name_ko']}] Google Places 관광지 수집 중...")

    all_spots = {}
    queries = config.get("places_query_spots", [])
    lat = config["center_lat"]
    lng = config["center_lng"]

    for query in queries:
        print(f"   검색: \"{query}\"")
        places = search_google_places(query, lat, lng, api_key, max_results=10)
        print(f"   → {len(places)}개 장소 발견")

        for place in places:
            parsed = parse_google_place(place)
            key = parsed["name"]
            if key and key not in all_spots:
                all_spots[key] = parsed

        time.sleep(0.5)

    spots = list(all_spots.values())
    spots.sort(key=lambda s: (s.get("user_rating_count", 0)), reverse=True)
    spots = spots[:12]

    print(f"   ✅ 총 {len(spots)}개 관광지 수집 완료")
    return spots


# ─────────────────────────────────────────────
#  데이터 통합 및 저장
# ─────────────────────────────────────────────

def convert_tabelog_to_app_format(restaurants, city_center_lat, city_center_lng):
    """Tabelog 데이터를 앱 형식으로 변환"""
    result = []
    for r in restaurants:
        entry = {
            "name": r["name"],
            "category": r["category"],
            "price_range": r.get("price_range", ""),
            "hours": r.get("hours", "영업시간 확인 필요"),
            "duration_min": 50,
            "description": r.get("description", f"Tabelog 평점 {r.get('rating', 'N/A')}"),
            "must_try": "",
            "rating": r.get("rating", ""),
            "tabelog_url": r.get("tabelog_url", ""),
            "source": "tabelog",
        }
        if r.get("name_ja"):
            entry["name_ja"] = r["name_ja"]
        if r.get("station"):
            entry["station"] = r["station"]
        result.append(entry)
    return result


def convert_google_to_app_format(spots):
    """Google Places 데이터를 앱 형식으로 변환"""
    result = []
    for s in spots:
        entry = {
            "name": s["name"],
            "type": "attraction",
            "category": s["category"],
            "hours": s.get("hours", "영업시간 확인 필요"),
            "duration_min": s.get("duration_min", 60),
            "description": s.get("description", ""),
            "lat": s.get("lat", 0),
            "lng": s.get("lng", 0),
            "source": "google_places",
        }
        if s.get("google_maps_uri"):
            entry["google_maps_uri"] = s["google_maps_uri"]
        result.append(entry)
    return result


def load_existing_data():
    """기존 cities.json 로드"""
    path = os.path.join(DATA_DIR, "cities.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cities_data(data):
    """cities.json 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "cities.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 저장 완료: {path}")


def main():
    google_api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")

    print("=" * 60)
    print("🇯🇵 일본 여행 데이터 수집기")
    print("=" * 60)
    print(f"  Tabelog 스크래핑: ✅ 사용 가능")
    print(f"  Google Places API: {'✅ API 키 설정됨' if google_api_key else '❌ API 키 없음 (기존 관광지 데이터 유지)'}")
    print()

    if not google_api_key:
        print("💡 Google Places API를 사용하려면:")
        print("   export GOOGLE_PLACES_API_KEY='your-api-key'")
        print("   를 설정한 후 다시 실행하세요.")
        print()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_cities = args if args else list(CITY_CONFIG.keys())
    print(f"🎯 대상 도시: {', '.join(target_cities)}")
    print()

    existing_data = load_existing_data()
    cities_data = dict(existing_data)

    fetch_details_flag = "--no-details" not in sys.argv

    for city_key in target_cities:
        if city_key.startswith("--"):
            continue
        config = CITY_CONFIG.get(city_key)
        if not config:
            print(f"⚠️  알 수 없는 도시: {city_key} (건너뜀)")
            continue

        city_entry = {
            "name_ko": config["name_ko"],
            "name_ja": config["name_ja"],
            "region": config["region"],
            "description": config["description"],
        }
        if config.get("airport"):
            city_entry["airport"] = config["airport"]

        # Tabelog 맛집 수집
        tabelog_restaurants = fetch_tabelog_restaurants(
            city_key, config,
            max_per_sort=10,
            fetch_details=fetch_details_flag,
        )
        if tabelog_restaurants:
            city_entry["restaurants"] = convert_tabelog_to_app_format(
                tabelog_restaurants,
                config["center_lat"],
                config["center_lng"],
            )
        else:
            print(f"   ⚠️  Tabelog 데이터 없음, 기존 데이터 유지")
            if city_key in existing_data and "restaurants" in existing_data[city_key]:
                city_entry["restaurants"] = existing_data[city_key]["restaurants"]
            else:
                city_entry["restaurants"] = []

        # Google Places 관광지 수집
        if google_api_key:
            google_spots = fetch_google_spots(city_key, config, google_api_key)
            if google_spots:
                city_entry["spots"] = convert_google_to_app_format(google_spots)
            else:
                print(f"   ⚠️  Google Places 데이터 없음, 기존 데이터 유지")
                if city_key in existing_data and "spots" in existing_data[city_key]:
                    city_entry["spots"] = existing_data[city_key]["spots"]
                else:
                    city_entry["spots"] = []
        else:
            if city_key in existing_data and "spots" in existing_data[city_key]:
                city_entry["spots"] = existing_data[city_key]["spots"]
            else:
                city_entry["spots"] = []

        cities_data[city_key] = city_entry

    save_cities_data(cities_data)

    print("\n" + "=" * 60)
    print("📊 수집 결과 요약")
    print("=" * 60)
    for ck, cd in cities_data.items():
        r_count = len(cd.get("restaurants", []))
        s_count = len(cd.get("spots", []))
        r_source = "tabelog" if r_count > 0 and cd["restaurants"][0].get("source") == "tabelog" else "기존"
        s_source = "google" if s_count > 0 and cd["spots"][0].get("source") == "google_places" else "기존"
        print(f"  {cd['name_ko']:8s} | 식당 {r_count:2d}개 ({r_source}) | 관광지 {s_count:2d}개 ({s_source})")
    print()


if __name__ == "__main__":
    main()
