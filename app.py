import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BASE_URL = "https://finance.naver.com/sise/sise_market_sum.naver"


def scrape_kospi_market_cap(pages=4):
    """네이버 금융에서 코스피 시가총액 상위 종목을 스크래핑합니다."""
    stocks = []

    for page in range(1, pages + 1):
        url = f"{BASE_URL}?sosok=0&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="type_2")
        if not table:
            continue

        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue

            rank_text = cols[0].get_text(strip=True)
            if not rank_text.isdigit():
                continue

            name_tag = cols[1].find("a")
            if not name_tag:
                continue

            name = name_tag.get_text(strip=True)
            code_href = name_tag.get("href", "")
            stock_code = code_href.split("code=")[-1] if "code=" in code_href else ""

            current_price = cols[2].get_text(strip=True).replace(",", "")
            change = cols[3].get_text(strip=True).replace(",", "")

            change_img = cols[3].find("img") or cols[2].find_next("img")
            change_sign = ""
            if change_img:
                alt = change_img.get("alt", "")
                if "상승" in alt:
                    change_sign = "+"
                elif "하락" in alt:
                    change_sign = "-"

            change_rate = cols[4].get_text(strip=True).replace("%", "")

            market_cap = cols[6].get_text(strip=True).replace(",", "")

            stocks.append({
                "rank": int(rank_text),
                "name": name,
                "code": stock_code,
                "current_price": current_price,
                "change": change,
                "change_sign": change_sign,
                "change_rate": change_rate,
                "market_cap": market_cap,
            })

    stocks.sort(key=lambda x: x["rank"])
    return stocks


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stocks")
def api_stocks():
    try:
        stocks = scrape_kospi_market_cap(pages=4)
        return jsonify({"success": True, "data": stocks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host="0.0.0.0", port=port)
