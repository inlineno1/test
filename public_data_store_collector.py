"""
공공데이터포털 - 소상공인시장진흥공단 상가(상권)정보 API 데이터 수집 스크립트

이 스크립트는 공공데이터포털의 상가(상권)정보 API를 호출하여
특정 지역의 상가 데이터를 엑셀 파일로 저장합니다.
"""

import requests
import pandas as pd
from urllib.parse import quote

# ============================================================
# [설정 영역] 아래 값들을 본인 환경에 맞게 수정하세요.
# ============================================================

# 공공데이터포털에서 발급받은 인증키 (일반 인증키 - Encoding)
SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"

# API 기본 URL (소상공인시장진흥공단_상가(상권)정보 - 지정 상권 내 상가 조회)
BASE_URL = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"

# 조회할 행정동 코드 (기본값: 서울 강남구 역삼동 - 11680105)
# 행정동 코드는 공공데이터포털 API 문서를 참고하세요.
DONG_CODE = "11680105"

# 한 페이지당 조회할 건수
NUM_OF_ROWS = 1000

# 조회할 페이지 번호
PAGE_NO = 1

# 저장할 엑셀 파일명
OUTPUT_FILENAME = "공공데이터_상가리스트.xlsx"

# ============================================================


def build_request_params():
    """API 요청에 필요한 파라미터 딕셔너리를 생성합니다."""
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": str(PAGE_NO),
        "numOfRows": str(NUM_OF_ROWS),
        "divId": "adongCd",
        "key": DONG_CODE,
        "type": "json",
    }
    return params


def call_api():
    """
    공공데이터포털 API를 호출하고 JSON 응답을 반환합니다.

    Returns:
        dict | None: 성공 시 JSON 응답 딕셔너리, 실패 시 None
    """
    params = build_request_params()

    # API 호출 시도
    try:
        print(f"[INFO] API 호출을 시작합니다. (행정동 코드: {DONG_CODE})")
        response = requests.get(BASE_URL, params=params, timeout=30)
    except requests.exceptions.ConnectionError:
        print("[ERROR] 네트워크 연결에 실패했습니다. 인터넷 연결 상태를 확인하세요.")
        return None
    except requests.exceptions.Timeout:
        print("[ERROR] API 응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API 요청 중 알 수 없는 오류가 발생했습니다: {e}")
        return None

    # HTTP 상태 코드 확인
    if response.status_code != 200:
        print(f"[ERROR] API 서버 응답 오류 (HTTP {response.status_code})")
        print(f"        응답 내용: {response.text[:500]}")
        return None

    # JSON 파싱
    try:
        json_data = response.json()
    except ValueError:
        print("[ERROR] 응답 데이터를 JSON으로 파싱할 수 없습니다.")
        print(f"        응답 내용(앞 500자): {response.text[:500]}")
        return None

    print("[INFO] API 호출이 성공적으로 완료되었습니다.")
    return json_data


def extract_store_data(json_data):
    """
    JSON 응답에서 필요한 상가 데이터만 추출합니다.

    Args:
        json_data (dict): API 응답 JSON 데이터

    Returns:
        list[dict] | None: 추출된 상가 데이터 리스트, 실패 시 None
    """
    # 응답 데이터 구조 검증 - 최상위 키 확인
    if not json_data or not isinstance(json_data, dict):
        print("[ERROR] 유효하지 않은 응답 데이터입니다.")
        return None

    # 응답 헤더에서 결과 코드 확인
    try:
        header = json_data.get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg", "")

        if result_code and result_code != "00":
            print(f"[ERROR] API 응답 오류 - 코드: {result_code}, 메시지: {result_msg}")
            return None
    except (AttributeError, TypeError):
        pass

    # 상가 데이터가 들어있는 body > items 경로 탐색
    try:
        body = json_data.get("body", {})
        items = body.get("items", [])
    except AttributeError:
        print("[ERROR] 응답 데이터에서 'body' 또는 'items' 키를 찾을 수 없습니다.")
        print(f"        응답 키 목록: {list(json_data.keys())}")
        return None

    # 데이터 존재 여부 확인
    if not items:
        print("[WARN] 조회된 상가 데이터가 없습니다.")
        print("       행정동 코드를 확인하거나 다른 지역으로 시도하세요.")
        return None

    total_count = body.get("totalCount", len(items))
    print(f"[INFO] 총 {total_count}건의 상가 데이터 중 {len(items)}건을 조회했습니다.")

    # 필요한 필드만 추출: 상호명, 상권업종소분류명, 도로명주소, 경도, 위도
    extracted = []
    for item in items:
        store = {
            "상호명": item.get("bizesNm", ""),
            "상권업종소분류명": item.get("indsSclsNm", ""),
            "도로명주소": item.get("rdnmAdr", ""),
            "경도": item.get("lon", ""),
            "위도": item.get("lat", ""),
        }
        extracted.append(store)

    print(f"[INFO] {len(extracted)}건의 상가 데이터 추출이 완료되었습니다.")
    return extracted


def save_to_excel(store_list):
    """
    추출된 상가 데이터를 엑셀 파일로 저장합니다.

    Args:
        store_list (list[dict]): 추출된 상가 데이터 리스트

    Returns:
        bool: 저장 성공 여부
    """
    # 데이터프레임 생성
    try:
        df = pd.DataFrame(store_list)
    except Exception as e:
        print(f"[ERROR] 데이터프레임 생성 중 오류가 발생했습니다: {e}")
        return False

    # 데이터프레임이 비어있는지 확인
    if df.empty:
        print("[WARN] 저장할 데이터가 없습니다.")
        return False

    print(f"[INFO] 데이터프레임 생성 완료 (총 {len(df)}행 x {len(df.columns)}열)")

    # 경도/위도를 숫자형으로 변환 (빈 문자열은 NaN 처리)
    for col in ["경도", "위도"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 엑셀 파일로 저장
    try:
        df.to_excel(OUTPUT_FILENAME, index=False, engine="openpyxl")
    except PermissionError:
        print(f"[ERROR] '{OUTPUT_FILENAME}' 파일이 다른 프로그램에서 열려 있습니다. 닫고 다시 시도하세요.")
        return False
    except Exception as e:
        print(f"[ERROR] 엑셀 파일 저장 중 오류가 발생했습니다: {e}")
        return False

    print(f"[INFO] 엑셀 파일 저장 완료 → {OUTPUT_FILENAME}")
    return True


def main():
    """메인 실행 함수: API 호출 → 데이터 추출 → 엑셀 저장 순서로 진행합니다."""

    print("=" * 60)
    print(" 소상공인시장진흥공단 상가(상권)정보 데이터 수집기")
    print("=" * 60)

    # 인증키 설정 여부 확인
    if SERVICE_KEY == "YOUR_SERVICE_KEY_HERE":
        print("[WARN] SERVICE_KEY가 기본값입니다.")
        print("       공공데이터포털(data.go.kr)에서 인증키를 발급받아 설정하세요.")
        print("       (테스트를 위해 기본값으로 계속 진행합니다.)\n")

    # 1단계: API 호출
    print("\n[STEP 1] API 호출 중...")
    json_data = call_api()
    if json_data is None:
        print("[FAIL] API 호출에 실패했습니다. 프로그램을 종료합니다.")
        return

    # 2단계: 데이터 추출
    print("\n[STEP 2] 데이터 추출 중...")
    store_list = extract_store_data(json_data)
    if store_list is None:
        print("[FAIL] 데이터 추출에 실패했습니다. 프로그램을 종료합니다.")
        return

    # 3단계: 엑셀 파일 저장
    print("\n[STEP 3] 엑셀 파일 저장 중...")
    success = save_to_excel(store_list)
    if not success:
        print("[FAIL] 엑셀 파일 저장에 실패했습니다.")
        return

    print("\n" + "=" * 60)
    print(" 모든 작업이 완료되었습니다!")
    print(f" 저장 파일: {OUTPUT_FILENAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
