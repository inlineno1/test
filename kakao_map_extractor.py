"""
카카오맵 장소 추출기 (Kakao Map Place Extractor)

카카오 로컬 REST API를 활용하여 장소 정보를 검색하고,
결과를 CSV 또는 JSON 파일로 저장하는 도구입니다.

사용법:
    python kakao_map_extractor.py --help
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests

BASE_URL = "https://dapi.kakao.com/v2/local"

CATEGORY_GROUPS = {
    "MT1": "대형마트",
    "CS2": "편의점",
    "PS3": "어린이집, 유치원",
    "SC4": "학교",
    "AC5": "학원",
    "PK6": "주차장",
    "OL7": "주유소, 충전소",
    "SW8": "지하철역",
    "BK9": "은행",
    "CT1": "문화시설",
    "AG2": "중개업소",
    "PO3": "공공기관",
    "AT4": "관광명소",
    "AD5": "숙박",
    "FD6": "음식점",
    "CE7": "카페",
    "HP8": "병원",
    "PM9": "약국",
}

MAX_PAGE = 45
KEYWORD_MAX_SIZE = 15
CATEGORY_MAX_SIZE = 15


@dataclass
class Place:
    id: str = ""
    place_name: str = ""
    category_name: str = ""
    category_group_code: str = ""
    category_group_name: str = ""
    phone: str = ""
    address_name: str = ""
    road_address_name: str = ""
    x: str = ""
    y: str = ""
    place_url: str = ""
    distance: str = ""


@dataclass
class SearchResult:
    total_count: int = 0
    pageable_count: int = 0
    is_end: bool = True
    places: list = field(default_factory=list)


class KakaoMapExtractor:
    """카카오맵 장소 데이터 추출기"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"KakaoAK {api_key}",
        })

    def _request(self, endpoint: str, params: dict) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_keyword(
        self,
        query: str,
        x: Optional[str] = None,
        y: Optional[str] = None,
        radius: Optional[int] = None,
        category_group_code: Optional[str] = None,
        page: int = 1,
        size: int = KEYWORD_MAX_SIZE,
        sort: str = "accuracy",
    ) -> SearchResult:
        """키워드로 장소 검색"""
        params = {"query": query, "page": page, "size": size, "sort": sort}
        if x and y:
            params["x"] = x
            params["y"] = y
        if radius is not None:
            params["radius"] = radius
        if category_group_code:
            params["category_group_code"] = category_group_code

        data = self._request("search/keyword.json", params)
        return self._parse_search(data)

    def search_category(
        self,
        category_group_code: str,
        x: str,
        y: str,
        radius: int = 2000,
        page: int = 1,
        size: int = CATEGORY_MAX_SIZE,
        sort: str = "accuracy",
    ) -> SearchResult:
        """카테고리로 장소 검색"""
        params = {
            "category_group_code": category_group_code,
            "x": x,
            "y": y,
            "radius": radius,
            "page": page,
            "size": size,
            "sort": sort,
        }
        data = self._request("search/category.json", params)
        return self._parse_search(data)

    def search_address(self, query: str, page: int = 1, size: int = 10) -> dict:
        """주소를 좌표로 변환"""
        params = {"query": query, "page": page, "size": size}
        return self._request("search/address.json", params)

    def coord_to_address(self, x: str, y: str) -> dict:
        """좌표를 주소로 변환"""
        params = {"x": x, "y": y}
        return self._request("geo/coord2address.json", params)

    def _parse_search(self, data: dict) -> SearchResult:
        meta = data.get("meta", {})
        docs = data.get("documents", [])
        places = [Place(**{k: doc.get(k, "") for k in Place.__dataclass_fields__}) for doc in docs]
        return SearchResult(
            total_count=meta.get("total_count", 0),
            pageable_count=meta.get("pageable_count", 0),
            is_end=meta.get("is_end", True),
            places=places,
        )

    def search_all_keyword(
        self,
        query: str,
        x: Optional[str] = None,
        y: Optional[str] = None,
        radius: Optional[int] = None,
        category_group_code: Optional[str] = None,
        sort: str = "accuracy",
        delay: float = 0.2,
    ) -> list[Place]:
        """키워드 검색 결과를 모든 페이지에서 수집"""
        all_places = []
        page = 1
        while page <= MAX_PAGE:
            result = self.search_keyword(
                query, x=x, y=y, radius=radius,
                category_group_code=category_group_code,
                page=page, sort=sort,
            )
            all_places.extend(result.places)
            print(f"  [페이지 {page}] {len(result.places)}건 수집 (누적 {len(all_places)}/{result.total_count}건)")
            if result.is_end or not result.places:
                break
            page += 1
            time.sleep(delay)
        return all_places

    def search_all_category(
        self,
        category_group_code: str,
        x: str,
        y: str,
        radius: int = 2000,
        sort: str = "accuracy",
        delay: float = 0.2,
    ) -> list[Place]:
        """카테고리 검색 결과를 모든 페이지에서 수집"""
        all_places = []
        page = 1
        while page <= MAX_PAGE:
            result = self.search_category(
                category_group_code, x=x, y=y, radius=radius,
                page=page, sort=sort,
            )
            all_places.extend(result.places)
            print(f"  [페이지 {page}] {len(result.places)}건 수집 (누적 {len(all_places)}/{result.total_count}건)")
            if result.is_end or not result.places:
                break
            page += 1
            time.sleep(delay)
        return all_places


def save_csv(places: list[Place], filepath: str) -> None:
    if not places:
        print("저장할 데이터가 없습니다.")
        return
    fieldnames = list(Place.__dataclass_fields__.keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for place in places:
            writer.writerow(asdict(place))
    print(f"CSV 저장 완료: {filepath} ({len(places)}건)")


def save_json(places: list[Place], filepath: str) -> None:
    if not places:
        print("저장할 데이터가 없습니다.")
        return
    data = [asdict(p) for p in places]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON 저장 완료: {filepath} ({len(places)}건)")


def print_places(places: list[Place], limit: int = 20) -> None:
    if not places:
        print("검색 결과가 없습니다.")
        return
    shown = places[:limit]
    print(f"\n{'='*80}")
    print(f"{'장소명':<30} {'주소':<35} {'전화번호':<15}")
    print(f"{'='*80}")
    for p in shown:
        name = p.place_name[:28]
        addr = (p.road_address_name or p.address_name)[:33]
        phone = p.phone[:13]
        print(f"{name:<30} {addr:<35} {phone:<15}")
    if len(places) > limit:
        print(f"  ... 외 {len(places) - limit}건")
    print(f"{'='*80}")
    print(f"총 {len(places)}건")


def get_api_key() -> str:
    key = os.environ.get("KAKAO_REST_API_KEY", "")
    if not key:
        key = input("카카오 REST API 키를 입력하세요: ").strip()
    if not key:
        print("오류: API 키가 필요합니다. 환경변수 KAKAO_REST_API_KEY를 설정하거나 직접 입력하세요.")
        print("  카카오 개발자 사이트에서 발급: https://developers.kakao.com")
        sys.exit(1)
    return key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="카카오맵 장소 추출기 - 카카오 로컬 API를 활용한 장소 데이터 수집 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 키워드로 장소 검색
  python kakao_map_extractor.py keyword "강남역 맛집"

  # 키워드 검색 + 반경 제한 (좌표 중심 2km 이내)
  python kakao_map_extractor.py keyword "카페" --x 127.027 --y 37.498 --radius 2000

  # 카테고리로 검색 (좌표 중심 반경 내 음식점)
  python kakao_map_extractor.py category FD6 --x 127.027 --y 37.498 --radius 3000

  # 주소를 좌표로 변환
  python kakao_map_extractor.py address "서울 강남구 역삼동"

  # 좌표를 주소로 변환
  python kakao_map_extractor.py coord2addr --x 127.027 --y 37.498

  # CSV로 저장
  python kakao_map_extractor.py keyword "서울 병원" -o hospitals.csv

  # JSON으로 저장
  python kakao_map_extractor.py keyword "판교 카페" -o cafes.json

카테고리 코드:
  MT1=대형마트, CS2=편의점, PS3=어린이집/유치원, SC4=학교,
  AC5=학원, PK6=주차장, OL7=주유소, SW8=지하철역, BK9=은행,
  CT1=문화시설, AG2=중개업소, PO3=공공기관, AT4=관광명소,
  AD5=숙박, FD6=음식점, CE7=카페, HP8=병원, PM9=약국
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # keyword 서브커맨드
    kw = subparsers.add_parser("keyword", help="키워드로 장소 검색")
    kw.add_argument("query", help="검색할 키워드 (예: '강남역 맛집')")
    kw.add_argument("--x", type=str, default=None, help="중심 좌표 경도 (longitude)")
    kw.add_argument("--y", type=str, default=None, help="중심 좌표 위도 (latitude)")
    kw.add_argument("--radius", type=int, default=None, help="검색 반경 (미터, 최대 20000)")
    kw.add_argument("--category", type=str, default=None, help="카테고리 그룹 코드 필터")
    kw.add_argument("--sort", choices=["accuracy", "distance"], default="accuracy", help="정렬 방식")
    kw.add_argument("-o", "--output", type=str, default=None, help="결과 저장 파일 경로 (.csv 또는 .json)")

    # category 서브커맨드
    cat = subparsers.add_parser("category", help="카테고리로 장소 검색")
    cat.add_argument("code", help="카테고리 그룹 코드 (예: FD6=음식점, CE7=카페)")
    cat.add_argument("--x", type=str, required=True, help="중심 좌표 경도 (longitude)")
    cat.add_argument("--y", type=str, required=True, help="중심 좌표 위도 (latitude)")
    cat.add_argument("--radius", type=int, default=2000, help="검색 반경 (미터, 기본값 2000)")
    cat.add_argument("--sort", choices=["accuracy", "distance"], default="accuracy", help="정렬 방식")
    cat.add_argument("-o", "--output", type=str, default=None, help="결과 저장 파일 경로 (.csv 또는 .json)")

    # address 서브커맨드
    addr = subparsers.add_parser("address", help="주소를 좌표로 변환")
    addr.add_argument("query", help="검색할 주소 (예: '서울 강남구 역삼동')")

    # coord2addr 서브커맨드
    c2a = subparsers.add_parser("coord2addr", help="좌표를 주소로 변환")
    c2a.add_argument("--x", type=str, required=True, help="경도 (longitude)")
    c2a.add_argument("--y", type=str, required=True, help="위도 (latitude)")

    # categories 서브커맨드
    subparsers.add_parser("categories", help="사용 가능한 카테고리 코드 목록 보기")

    return parser


def cmd_keyword(extractor: KakaoMapExtractor, args: argparse.Namespace) -> None:
    print(f"\n키워드 검색: '{args.query}'")
    if args.x and args.y:
        print(f"  중심 좌표: ({args.x}, {args.y}), 반경: {args.radius or '미지정'}m")
    places = extractor.search_all_keyword(
        query=args.query,
        x=args.x, y=args.y,
        radius=args.radius,
        category_group_code=args.category,
        sort=args.sort,
    )
    print_places(places)
    if args.output:
        _save_output(places, args.output)


def cmd_category(extractor: KakaoMapExtractor, args: argparse.Namespace) -> None:
    code = args.code.upper()
    name = CATEGORY_GROUPS.get(code, "알 수 없음")
    print(f"\n카테고리 검색: {code} ({name})")
    print(f"  중심 좌표: ({args.x}, {args.y}), 반경: {args.radius}m")
    places = extractor.search_all_category(
        category_group_code=code,
        x=args.x, y=args.y,
        radius=args.radius,
        sort=args.sort,
    )
    print_places(places)
    if args.output:
        _save_output(places, args.output)


def cmd_address(extractor: KakaoMapExtractor, args: argparse.Namespace) -> None:
    print(f"\n주소 → 좌표 변환: '{args.query}'")
    data = extractor.search_address(args.query)
    docs = data.get("documents", [])
    if not docs:
        print("검색 결과가 없습니다.")
        return
    for doc in docs:
        name = doc.get("address_name", "")
        x = doc.get("x", "")
        y = doc.get("y", "")
        addr_type = doc.get("address_type", "")
        print(f"  [{addr_type}] {name} → 경도: {x}, 위도: {y}")


def cmd_coord2addr(extractor: KakaoMapExtractor, args: argparse.Namespace) -> None:
    print(f"\n좌표 → 주소 변환: ({args.x}, {args.y})")
    data = extractor.coord_to_address(args.x, args.y)
    docs = data.get("documents", [])
    if not docs:
        print("변환 결과가 없습니다.")
        return
    for doc in docs:
        addr = doc.get("address", {})
        road = doc.get("road_address")
        if addr:
            print(f"  [지번] {addr.get('address_name', '')}")
        if road:
            print(f"  [도로명] {road.get('address_name', '')}")


def cmd_categories() -> None:
    print("\n사용 가능한 카테고리 코드:")
    print(f"  {'코드':<6} {'설명'}")
    print(f"  {'─'*6} {'─'*20}")
    for code, desc in CATEGORY_GROUPS.items():
        print(f"  {code:<6} {desc}")


def _save_output(places: list[Place], filepath: str) -> None:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".json":
        save_json(places, filepath)
    else:
        if not ext:
            filepath += ".csv"
        save_csv(places, filepath)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "categories":
        cmd_categories()
        return

    api_key = get_api_key()
    extractor = KakaoMapExtractor(api_key)

    try:
        if args.command == "keyword":
            cmd_keyword(extractor, args)
        elif args.command == "category":
            cmd_category(extractor, args)
        elif args.command == "address":
            cmd_address(extractor, args)
        elif args.command == "coord2addr":
            cmd_coord2addr(extractor, args)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 401:
            print(f"오류: 인증 실패 (401). API 키를 확인하세요.")
        elif status == 429:
            print(f"오류: 요청 한도 초과 (429). 잠시 후 다시 시도하세요.")
        else:
            print(f"HTTP 오류: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"네트워크 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
