"""
Розклад ЗВОРОТНОГО напрямку: Академмістечко -> Лісова.

Те саме, що scrape_inmetro_schedule.py, але:
  STATION_ID      = 101 (Академмістечко замість Лісової)
  DIRECTION_INDEX = 0   ("До Лісової" замість "До Академмістечка")

Перевірено на реальних даних: 251 рейс, перший 05:51, останній 22:30.

Запуск:
  python scrape_inmetro_reverse.py --debug
"""

import re
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

import requests

STATION_ID = 101          # Академмістечко - підтверджено збереженою сторінкою
DIRECTION_INDEX = 0       # "До Лісової"
STATION_URL = f"https://inmetro.pp.ua/Розклад/timetable.php?city=1&station={STATION_ID}"

OUTPUT_FILE = "schedule_akademmistechko_to_lisova.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
}

TIME_PATTERN = re.compile(
    r"currentTime\.setHours\((\d{1,2}),\s*(\d{1,2}),\s*0\);"
    r"departure_times\[" + str(DIRECTION_INDEX) + r"\]\.push\(currentTime\)"
)

KYIV_TZ = timezone(timedelta(hours=3))


def fetch_page(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_departures(html: str) -> list[str]:
    matches = TIME_PATTERN.findall(html)
    return [f"{int(h):02d}:{int(m):02d}" for h, m in matches]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    html = fetch_page(STATION_URL)

    if args.debug:
        with open("raw_page_reverse.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Збережено raw_page_reverse.html ({len(html)} байт)")

    times = extract_departures(html)

    if args.debug:
        print(f"Знайдено часів (index {DIRECTION_INDEX}): {len(times)}")
        if times:
            print("Перші 5:", times[:5])
            print("Останні 5:", times[-5:])

    if not times:
        print("ПОМИЛКА: не знайшли жодного часу.", file=sys.stderr)
        sys.exit(1)

    if len(times) < 50:
        print(f"УВАГА: підозріло мало рейсів ({len(times)}), зазвичай ~250.",
              file=sys.stderr)

    data = {
        "updated": datetime.now(KYIV_TZ).isoformat(timespec="seconds"),
        "station": "Академмістечко",
        "direction": "Лісова",
        "departures": times,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK: збережено {len(times)} часів у {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
