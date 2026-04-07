import json
import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(filename):
    with open(os.path.join(BASE_DIR, "data", filename), "r", encoding="utf-8") as f:
        return json.load(f)


def get_cities_data():
    return load_json("cities.json")


def get_transport_data():
    return load_json("transport.json")


def find_flight(flights, origin, destination):
    key = f"{origin}-{destination}"
    return flights.get(key)


def find_train(trains, city_from, city_to):
    key = f"{city_from}-{city_to}"
    route = trains.get(key)
    if not route:
        key = f"{city_to}-{city_from}"
        route = trains.get(key)
    return route


def time_str(hour, minute=0):
    return f"{hour:02d}:{minute:02d}"


def add_minutes(time_string, minutes):
    h, m = map(int, time_string.split(":"))
    total = h * 60 + m + minutes
    return time_str(total // 60, total % 60)


def time_to_minutes(time_string):
    h, m = map(int, time_string.split(":"))
    return h * 60 + m


def pick_items(items, count, used_names=None):
    if used_names is None:
        used_names = set()
    available = [i for i in items if i["name"] not in used_names]
    if len(available) < count:
        available = items[:]
    random.shuffle(available)
    return available[:count]


def make_restaurant_event(current_time, r, meal_label):
    """식당 이벤트 딕셔너리 생성"""
    duration = r.get("duration_min", 50)
    end_time = add_minutes(current_time, duration)

    rating_str = f" (Tabelog ⭐{r['rating']})" if r.get("rating") else ""
    desc = r.get("description", "") or f"{r['category']}{rating_str}"
    if not desc and r.get("rating"):
        desc = f"Tabelog 평점 {r['rating']}"

    tip_parts = []
    if r.get("hours"):
        tip_parts.append(f"영업시간: {r['hours']}")
    if r.get("station"):
        tip_parts.append(f"위치: {r['station']}")

    event = {
        "time": current_time,
        "end_time": end_time,
        "title": f"🍽️ [{meal_label}] {r['name']}",
        "type": "restaurant",
        "category": r.get("category", ""),
        "description": desc,
        "price": r.get("price_range", ""),
        "must_try": r.get("must_try", ""),
        "tip": " | ".join(tip_parts) if tip_parts else "",
    }
    if r.get("tabelog_url"):
        event["tabelog_url"] = r["tabelog_url"]
    if r.get("rating"):
        event["rating"] = r["rating"]
    if r.get("google_maps_uri"):
        event["google_maps_uri"] = r["google_maps_uri"]
    return event, end_time


def make_spot_event(current_time, s):
    """관광지 이벤트 딕셔너리 생성"""
    duration = s.get("duration_min", 60)
    end_time = add_minutes(current_time, duration)

    event = {
        "time": current_time,
        "end_time": end_time,
        "title": f"📍 {s['name']}",
        "type": "spot",
        "category": s.get("category", ""),
        "description": s.get("description", ""),
        "hours": s.get("hours", ""),
        "name_ja": s.get("name_ja", ""),
        "tip": f"소요시간 약 {duration}분",
    }
    if s.get("google_maps_uri"):
        event["google_maps_uri"] = s["google_maps_uri"]
    return event, end_time


def generate_schedule(cities, nights, departure_time="09:00"):
    cities_data = get_cities_data()
    transport_data = get_transport_data()

    city_keys = [c.strip().lower() for c in cities]
    city_infos = []
    for ck in city_keys:
        for key, val in cities_data.items():
            if key == ck or val["name_ko"] == ck or ck in val["name_ko"].lower():
                city_infos.append((key, val))
                break

    if not city_infos:
        return None

    total_days = nights + 1
    flights = transport_data.get("flights", {})
    trains = transport_data.get("trains", {})

    first_city_key = city_infos[0][0]
    airport_code = city_infos[0][1].get("airport")
    if not airport_code:
        for ck, cv in cities_data.items():
            if cv.get("region") == city_infos[0][1].get("region") and cv.get("airport"):
                airport_code = cv["airport"]
                first_city_key = ck
                break

    flight_in = find_flight(flights, "ICN", airport_code) if airport_code else None
    flight_out = find_flight(flights, airport_code, "ICN") if airport_code else None

    schedule = []
    used_spots = set()
    used_restaurants = set()

    days_per_city = max(1, total_days // len(city_infos))
    remainder = total_days - days_per_city * len(city_infos)

    city_day_map = []
    for i, (ck, cv) in enumerate(city_infos):
        d = days_per_city + (1 if i < remainder else 0)
        for _ in range(d):
            city_day_map.append((ck, cv))

    while len(city_day_map) < total_days:
        city_day_map.append(city_infos[-1])
    city_day_map = city_day_map[:total_days]

    for day_idx in range(total_days):
        city_key, city_data = city_day_map[day_idx]
        day_schedule = {
            "day": day_idx + 1,
            "city": city_data["name_ko"],
            "city_key": city_key,
            "events": []
        }

        current_time = "08:00"

        if day_idx == 0:
            dep_time = departure_time
            if flight_in:
                arrival_time = add_minutes(dep_time, flight_in["duration_min"])
                day_schedule["events"].append({
                    "time": dep_time,
                    "end_time": arrival_time,
                    "title": f"✈️ 인천공항 출발 → {flight_in['to']}",
                    "type": "transport",
                    "description": f"비행시간 약 {flight_in['duration_min']}분",
                    "tip": flight_in.get("note", "")
                })
                customs_done = add_minutes(arrival_time, 45)
                day_schedule["events"].append({
                    "time": arrival_time,
                    "end_time": customs_done,
                    "title": "🛃 입국심사 및 짐 수령",
                    "type": "info",
                    "description": "입국심사, 수하물 수령, 교통카드 구매 등",
                    "tip": "IC카드(SUICA/ICOCA/SUGOCA) 구매 추천"
                })
                current_time = customs_done
            else:
                current_time = "10:00"

            if city_key != first_city_key:
                train = find_train(trains, first_city_key, city_key)
                if train:
                    train_arrival = add_minutes(current_time, train["duration_min"])
                    day_schedule["events"].append({
                        "time": current_time,
                        "end_time": train_arrival,
                        "title": f"🚄 {train['from']} → {train['to']} ({train['type']})",
                        "type": "transport",
                        "description": f"소요시간 약 {train['duration_min']}분 / {train['price']}",
                        "tip": train.get("note", "")
                    })
                    current_time = train_arrival

        elif day_idx > 0:
            prev_city_key = city_day_map[day_idx - 1][0]
            if prev_city_key != city_key:
                train = find_train(trains, prev_city_key, city_key)
                if train:
                    train_arrival = add_minutes(current_time, train["duration_min"])
                    day_schedule["events"].append({
                        "time": current_time,
                        "end_time": train_arrival,
                        "title": f"🚄 {train['from']} → {train['to']} ({train['type']})",
                        "type": "transport",
                        "description": f"소요시간 약 {train['duration_min']}분 / {train['price']}",
                        "tip": train.get("note", "")
                    })
                    current_time = train_arrival

        spots = city_data.get("spots", [])
        restaurants = city_data.get("restaurants", [])

        is_last_day = (day_idx == total_days - 1)

        end_of_day = "21:30"
        flight_dep = None
        checkin_time = None
        train_back_duration = 0
        if is_last_day and flight_out:
            if city_key != first_city_key:
                train_back = find_train(trains, city_key, first_city_key)
                if train_back:
                    train_back_duration = train_back["duration_min"] + 15

            min_dep_hour = 14
            if train_back_duration > 0:
                min_dep_hour = 16
            dep_candidates = [t for t in flight_out.get("typical_departures", [])
                              if time_to_minutes(t) >= min_dep_hour * 60]
            if dep_candidates:
                flight_dep = dep_candidates[0]
            else:
                flight_dep = flight_out["typical_departures"][-1] if flight_out["typical_departures"] else "18:00"
            checkin_time = add_minutes(flight_dep, -120)
            end_of_day = add_minutes(checkin_time, -train_back_duration)

        lunch_done = False
        dinner_done = False
        spot_count = 0
        max_spots = 4 if not is_last_day else 2

        while time_to_minutes(current_time) < time_to_minutes(end_of_day) - 30:
            cm = time_to_minutes(current_time)

            if not lunch_done and 11 * 60 <= cm <= 13 * 60:
                lunch_picks = pick_items(restaurants, 1, used_restaurants)
                if lunch_picks:
                    r = lunch_picks[0]
                    used_restaurants.add(r["name"])
                    event, lunch_end = make_restaurant_event(current_time, r, "점심")
                    day_schedule["events"].append(event)
                    current_time = lunch_end
                    lunch_done = True
                    continue

            if not dinner_done and 17 * 60 + 30 <= cm <= 19 * 60 and not is_last_day:
                dinner_picks = pick_items(restaurants, 1, used_restaurants)
                if dinner_picks:
                    r = dinner_picks[0]
                    used_restaurants.add(r["name"])
                    event, dinner_end = make_restaurant_event(current_time, r, "저녁")
                    day_schedule["events"].append(event)
                    current_time = dinner_end
                    dinner_done = True
                    continue

            if spot_count < max_spots:
                spot_picks = pick_items(spots, 1, used_spots)
                if spot_picks:
                    s = spot_picks[0]
                    used_spots.add(s["name"])
                    event, spot_end = make_spot_event(current_time, s)
                    if time_to_minutes(spot_end) > time_to_minutes(end_of_day):
                        break
                    day_schedule["events"].append(event)
                    current_time = add_minutes(spot_end, 15)
                    spot_count += 1
                    continue
            else:
                break

        if not lunch_done and time_to_minutes(current_time) <= 14 * 60:
            lunch_picks = pick_items(restaurants, 1, used_restaurants)
            if lunch_picks:
                r = lunch_picks[0]
                used_restaurants.add(r["name"])
                event, lunch_end = make_restaurant_event(current_time, r, "점심")
                day_schedule["events"].append(event)
                current_time = lunch_end

        if is_last_day and flight_out and flight_dep and checkin_time:
            if city_key != first_city_key:
                train_back = find_train(trains, city_key, first_city_key)
                if train_back:
                    move_time = add_minutes(checkin_time, -train_back["duration_min"] - 15)
                    if time_to_minutes(move_time) < time_to_minutes(current_time):
                        move_time = current_time
                    train_arrival = add_minutes(move_time, train_back["duration_min"])
                    day_schedule["events"].append({
                        "time": move_time,
                        "end_time": train_arrival,
                        "title": f"🚄 {train_back['from']} → {train_back['to']} ({train_back['type']})",
                        "type": "transport",
                        "description": f"소요시간 약 {train_back['duration_min']}분 / {train_back['price']}",
                        "tip": train_back.get("note", "")
                    })
                    current_time = train_arrival

            day_schedule["events"].append({
                "time": checkin_time,
                "end_time": flight_dep,
                "title": "🛃 공항 도착 및 체크인",
                "type": "info",
                "description": "탑승수속, 면세점 쇼핑, 출국심사",
                "tip": "면세점에서 로이스 초콜릿, 도쿄바나나 등 선물 구매 추천"
            })

            flight_arrival = add_minutes(flight_dep, flight_out["duration_min"])
            day_schedule["events"].append({
                "time": flight_dep,
                "end_time": flight_arrival,
                "title": f"✈️ {flight_out['from']} 출발 → 인천공항",
                "type": "transport",
                "description": f"비행시간 약 {flight_out['duration_min']}분",
                "tip": "수고하셨습니다! 즐거운 여행 되셨길 바랍니다 🎉"
            })

        elif not is_last_day and not dinner_done:
            night_spots = [s for s in spots if "야경" in s.get("category", "") or "야타이" in s["name"]]
            if night_spots:
                ns = night_spots[0]
                day_schedule["events"].append({
                    "time": "20:00",
                    "end_time": "21:30",
                    "title": f"🌙 {ns['name']}",
                    "type": "spot",
                    "category": ns["category"],
                    "description": ns["description"],
                    "tip": "야경 포인트"
                })

        day_schedule["events"].sort(key=lambda e: time_to_minutes(e["time"]))
        schedule.append(day_schedule)

    return schedule


@app.route("/")
def index():
    cities_data = get_cities_data()
    city_list = [{"key": k, "name_ko": v["name_ko"], "name_ja": v["name_ja"], "description": v["description"]}
                 for k, v in cities_data.items()]
    return render_template("index.html", cities=city_list)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    cities = data.get("cities", [])
    nights = int(data.get("nights", 2))
    departure_time = data.get("departure_time", "09:00")

    if not cities:
        return jsonify({"error": "도시를 선택해 주세요"}), 400

    schedule = generate_schedule(cities, nights, departure_time)
    if schedule is None:
        return jsonify({"error": "선택한 도시의 데이터를 찾을 수 없습니다"}), 404

    transport_data = get_transport_data()
    cities_data = get_cities_data()
    city_details = {}
    for ck in cities:
        ck_lower = ck.strip().lower()
        for key, val in cities_data.items():
            if key == ck_lower or val["name_ko"] == ck_lower or ck_lower in val["name_ko"].lower():
                city_details[key] = {"name_ko": val["name_ko"], "name_ja": val["name_ja"], "description": val["description"]}
                break

    return jsonify({
        "schedule": schedule,
        "cities": city_details,
        "nights": nights
    })


@app.route("/api/data-info")
def api_data_info():
    """현재 데이터 소스 정보 반환"""
    cities_data = get_cities_data()
    info = {}
    for ck, cv in cities_data.items():
        restaurants = cv.get("restaurants", [])
        spots = cv.get("spots", [])
        r_source = restaurants[0].get("source", "static") if restaurants else "없음"
        s_source = spots[0].get("source", "static") if spots else "없음"
        info[ck] = {
            "name_ko": cv["name_ko"],
            "restaurant_count": len(restaurants),
            "restaurant_source": r_source,
            "spot_count": len(spots),
            "spot_source": s_source,
        }
    return jsonify(info)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
