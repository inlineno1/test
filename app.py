import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

NAVER_API_URL = "https://m.stock.naver.com/api/stocks/marketValue/KOSPI"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PAGE_SIZE = 100


def fetch_kospi_market_cap(count=200):
    """네이버 증권 API를 통해 코스피 시가총액 상위 종목을 조회합니다."""
    stocks = []
    pages_needed = (count + PAGE_SIZE - 1) // PAGE_SIZE

    for page in range(1, pages_needed + 1):
        resp = requests.get(
            NAVER_API_URL,
            params={"page": page, "pageSize": PAGE_SIZE},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        for rank_offset, item in enumerate(data.get("stocks", []), start=1):
            rank = (page - 1) * PAGE_SIZE + rank_offset

            price_info = item.get("compareToPreviousPrice", {})
            change_code = price_info.get("code", "0")
            change_sign = ""
            if change_code == "2":
                change_sign = "+"
            elif change_code == "5":
                change_sign = "-"

            raw_change = item.get("compareToPreviousClosePrice", "0").replace(",", "")
            change_abs = raw_change.lstrip("-")

            raw_rate = item.get("fluctuationsRatio", "0")
            rate_abs = raw_rate.lstrip("-+")

            stocks.append({
                "rank": rank,
                "name": item.get("stockName", ""),
                "code": item.get("itemCode", ""),
                "current_price": item.get("closePrice", "0").replace(",", ""),
                "change": change_abs,
                "change_sign": change_sign,
                "change_rate": rate_abs,
                "market_cap": item.get("marketValue", "0").replace(",", ""),
                "market_cap_text": item.get("marketValueHangeul", ""),
                "logo_url": item.get("itemLogoPngUrl", ""),
            })

            if rank >= count:
                break

        if rank >= count:
            break

    return stocks


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


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host="0.0.0.0", port=port)
