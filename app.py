import concurrent.futures
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

NAVER_MARKET_API = "https://m.stock.naver.com/api/stocks/marketValue/KOSPI"
NAVER_FINANCE_API = "https://m.stock.naver.com/api/stock/{code}/finance/annual"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PAGE_SIZE = 100


def _parse_stock_item(item, rank):
    price_info = item.get("compareToPreviousPrice", {})
    change_code = price_info.get("code", "0")
    change_sign = ""
    if change_code == "2":
        change_sign = "+"
    elif change_code == "5":
        change_sign = "-"

    raw_change = item.get("compareToPreviousClosePrice", "0").replace(",", "")
    raw_rate = item.get("fluctuationsRatio", "0")

    return {
        "rank": rank,
        "name": item.get("stockName", ""),
        "code": item.get("itemCode", ""),
        "current_price": item.get("closePrice", "0").replace(",", ""),
        "change": raw_change.lstrip("-"),
        "change_sign": change_sign,
        "change_rate": raw_rate.lstrip("-+"),
        "market_cap": item.get("marketValue", "0").replace(",", ""),
        "market_cap_text": item.get("marketValueHangeul", ""),
        "logo_url": item.get("itemLogoPngUrl", ""),
    }


def fetch_kospi_market_cap(count=200):
    """네이버 증권 API를 통해 코스피 시가총액 상위 종목을 조회합니다."""
    stocks = []
    pages_needed = (count + PAGE_SIZE - 1) // PAGE_SIZE

    for page in range(1, pages_needed + 1):
        resp = requests.get(
            NAVER_MARKET_API,
            params={"page": page, "pageSize": PAGE_SIZE},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        for rank_offset, item in enumerate(data.get("stocks", []), start=1):
            rank = (page - 1) * PAGE_SIZE + rank_offset
            stocks.append(_parse_stock_item(item, rank))
            if rank >= count:
                break

        if len(stocks) >= count:
            break

    return stocks


def _fetch_operating_profit(code):
    """한 종목의 연간 영업이익 데이터를 조회합니다."""
    try:
        resp = requests.get(
            NAVER_FINANCE_API.format(code=code),
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        fi = data.get("financeInfo", {})
        titles = fi.get("trTitleList", [])
        rows = fi.get("rowList", [])

        op_row = None
        for row in rows:
            if row.get("title") == "영업이익":
                op_row = row
                break

        if not op_row:
            return None

        actual_periods = sorted(
            [t for t in titles if t.get("isConsensus") == "N"],
            key=lambda t: t["key"],
        )

        if len(actual_periods) < 2:
            return None

        latest = actual_periods[-1]
        previous = actual_periods[-2]

        cols = op_row.get("columns", {})
        latest_val = cols.get(latest["key"], {}).get("value", "")
        prev_val = cols.get(previous["key"], {}).get("value", "")

        def parse_num(s):
            if not s or s == "-":
                return None
            return float(s.replace(",", ""))

        latest_num = parse_num(latest_val)
        prev_num = parse_num(prev_val)

        if latest_num is None or prev_num is None:
            return None

        return {
            "latest_period": latest["title"],
            "previous_period": previous["title"],
            "latest_op": latest_num,
            "previous_op": prev_num,
            "latest_op_formatted": latest_val,
            "previous_op_formatted": prev_val,
        }

    except Exception:
        return None


def fetch_top_stocks_with_profit_growth(top_n=50, threshold=20.0):
    """시총 상위 종목 중 영업이익 증가율이 threshold% 이상인 종목을 반환합니다."""
    stocks = fetch_kospi_market_cap(count=top_n)

    def enrich(stock):
        profit = _fetch_operating_profit(stock["code"])
        if profit is None:
            return None

        prev_op = profit["previous_op"]
        latest_op = profit["latest_op"]

        if prev_op == 0:
            if latest_op > 0:
                growth = float("inf")
            else:
                return None
        else:
            growth = ((latest_op - prev_op) / abs(prev_op)) * 100

        if growth < threshold:
            return None

        stock["previous_period"] = profit["previous_period"]
        stock["latest_period"] = profit["latest_period"]
        stock["previous_op"] = profit["previous_op"]
        stock["latest_op"] = profit["latest_op"]
        stock["previous_op_formatted"] = profit["previous_op_formatted"]
        stock["latest_op_formatted"] = profit["latest_op_formatted"]
        stock["op_growth"] = round(growth, 2) if growth != float("inf") else "흑자전환"
        return stock

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(enrich, s): s for s in stocks}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)

    results.sort(key=lambda x: x["rank"])
    return results


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stocks")
def api_stocks():
    try:
        count = min(int(request.args.get("count", 200)), 500)
        stocks = fetch_kospi_market_cap(count=count)
        return jsonify({"success": True, "data": stocks, "total": len(stocks)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/profit-growth")
def api_profit_growth():
    try:
        top_n = min(int(request.args.get("top", 50)), 100)
        threshold = float(request.args.get("threshold", 20))
        stocks = fetch_top_stocks_with_profit_growth(top_n=top_n, threshold=threshold)
        return jsonify({
            "success": True,
            "data": stocks,
            "total": len(stocks),
            "criteria": {
                "top_n": top_n,
                "threshold": threshold,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host="0.0.0.0", port=port)
