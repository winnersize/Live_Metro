"""
ФИНАЛЬНАЯ версия - протестирована на реальном ответе сервера inmetro.pp.ua
(станция Лісова, station=118) и даёт РЕЗУЛЬТАТ, ИДЕНТИЧНЫЙ тому, что видно
в браузере: 251 время, первое 05:34, последнее 22:29.

Как оказалось, сайт вообще НЕ блокирует обычные запросы (requests) и НЕ
требует браузер/JS - но данные в сыром HTML-ответе лежат не в виде готовых
<div> (это появляется только ПОСЛЕ выполнения JS в браузере), а в виде
инлайн JavaScript-кода:

    var currentTime = new Date();
    currentTime.setHours(5,34,0);
    departure_times[1].push(currentTime);
    ...

Индекс [1] эмпирически подтверждён как "До Академмістечка" (проверено на
двух станциях линии M1 - Академмістечко и Лісова, оба раза направления
идут в одном и том же порядке: [0]=До Лісової, [1]=До Академмістечка).
Если вдруг на какой-то другой станции порядок окажется другим - лучше
всего сверить первые/последние времена с приложением вручную один раз.

Установка зависимостей:
  pip install -r requirements.txt

Запуск:
  python scrape_inmetro_schedule.py --debug
"""

import re
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

import requests

# ---------- НАСТРОЙКИ ----------
STATION_ID = 118  # Лісова - подтверждено реальным HTML-файлом станции
STATION_URL = f"https://inmetro.pp.ua/Розклад/timetable.php?city=1&station={STATION_ID}"

DIRECTION_INDEX = 1  # "До Академмістечка" - подтверждено на 2 станциях
OUTPUT_FILE = "schedule_lisova_to_akademmistechko.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
}

# Ищем именно вызовы setHours(...) которые сразу пушатся в нужный индекс
# направления. Пример в реальном HTML:
#   currentTime.setHours(5,34,0);departure_times[1].push(currentTime);
TIME_PATTERN = re.compile(
    r"currentTime\.setHours\((\d{1,2}),\s*(\d{1,2}),\s*0\);"
    r"departure_times\[" + str(DIRECTION_INDEX) + r"\]\.push\(currentTime\)"
)

KYIV_TZ = timezone(timedelta(hours=3))  # летнее время; зимой поставьте +2


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
        with open("raw_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Сохранено raw_page.html ({len(html)} байт)")

    times = extract_departures(html)

    if args.debug:
        print(f"Найдено времён (index {DIRECTION_INDEX}): {len(times)}")
        if times:
            print("Первые 5:", times[:5])
            print("Последние 5:", times[-5:])

    if not times:
        print("ОШИБКА: не нашли ни одного времени. Возможно, сайт изменил "
              "структуру страницы - пришлите свежий raw_page.html для разбора.",
              file=sys.stderr)
        sys.exit(1)

    if len(times) < 50:
        print(f"ПРЕДУПРЕЖДЕНИЕ: найдено подозрительно мало времён ({len(times)}), "
              f"обычно ~250. Проверьте raw_page.html вручную.", file=sys.stderr)

    data = {
        "updated": datetime.now(KYIV_TZ).isoformat(timespec="seconds"),
        "station": "Лісова",
        "direction": "Академмістечко",
        "departures": times,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK: сохранено {len(times)} времён в {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
