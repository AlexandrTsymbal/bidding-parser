import requests
from bs4 import BeautifulSoup
import csv
import time

URL = "https://old.bankrot.fedresurs.ru/TradeList.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
}


def get_hidden_fields(soup):
    """Получаем скрытые поля ASP.NET: __VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR"""
    hidden = {}
    for tag in soup.select("input[type=hidden]"):
        name = tag.get("name")
        if name:
            hidden[name] = tag.get("value", "")
    return hidden


def parse_table(soup):
    """Парсим таблицу торгов и возвращаем список словарей"""
    table = soup.find("table", {"id": "ctl00_cphBody_gvTradeList"})
    if not table:
        return []

    rows = []
    for tr in table.find_all("tr"):  # пропускаем заголовок
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue

        number = tds[0].get_text(strip=True)
        end_date = tds[1].get_text(strip=True)
        publish_date = tds[2].get_text(strip=True)

        trade_type = tds[5].get_text(strip=True)
        trade_link = tds[5].find("a")["href"] if tds[5].find("a") else ""

        access = tds[6].get_text(strip=True)
        status = tds[7].get_text(strip=True)

        rows.append({
            "Номер": number,
            "Дата окончания": end_date,
            "Дата публикации": publish_date,
            "Тип торгов": trade_type,
            "Ссылка на торги": "https://old.bankrot.fedresurs.ru" + trade_link,
            "Форма доступа": access,
            "Статус": status,
        })
    return rows


def get_all_trades_by_region(region_code, max_pages=2):
    """Парсим таблицу торгов для региона, переходя по страницам Page$N"""
    session = requests.Session()
    response = session.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    hidden = get_hidden_fields(soup)

    # === Фильтры ===
    hidden["ctl00$cphBody$ucRegion$ddlBoundList"] = str(region_code)
    hidden["ctl00$cphBody$ucTradeType$ddlBoundList"] = "3"  # публичное предложение

    # Нажатие кнопки поиска
    hidden["ctl00$cphBody$btnTradeSearch.x"] = "10"
    hidden["ctl00$cphBody$btnTradeSearch.y"] = "10"

    trades = []
    filtered_trades = []
    page = 1

    while page <= max_pages:
        # Для первой страницы используем только фильтр
        hidden["ctl00$cphBody$ucRegion$ddlBoundList"] = str(region_code)
        hidden["ctl00$cphBody$ucTradeType$ddlBoundList"] = "3"  # публичное предложение

        if page == 1:
            # первая страница: фильтры + кнопка поиска
            hidden["ctl00$cphBody$btnTradeSearch.x"] = "10"
            hidden["ctl00$cphBody$btnTradeSearch.y"] = "10"
        else:
            # последующие страницы: фильтры + __doPostBack

            hidden["__EVENTTARGET"] = "ctl00$cphBody$gvTradeList"
            hidden["__EVENTARGUMENT"] = f"Page${page}"
            # кнопка поиска не нужна

        response = session.post(URL, data=hidden, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        rows = parse_table(soup)[:-2]
        if not rows:
            break  # пустая таблица — конец
        trades.extend(rows)

        # Обновляем hidden поля для следующего запроса
        hidden = get_hidden_fields(soup)
        page += 1
        time.sleep(1)  # пауза, чтобы сервер не нагружать

    for trade in trades:
        url = trade["Ссылка на торги"]
        response = session.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        classification_label = soup.find("b", string="Классификация имущества")
        if classification_label:
            classification_div = classification_label.find_next("div")
            if classification_div and "автомобили" in classification_div.get_text(strip=True).lower():
                filtered_trades.append(trade)
        time.sleep(0.5)  # пауза, чтобы сервер не нагружать

    return filtered_trades




def save_to_csv(trades, filename="trades.csv"):
    if not trades:
        print("❗ Нет данных для сохранения.")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
    print(f"✅ Сохранено {len(trades)} записей в {filename}")


if __name__ == "__main__":
    region_code = 65  # Москва, можно заменить на любой другой
    print(f"📍 Сбор данных для региона {region_code}...")


    trades = get_all_trades_by_region(region_code)
    print(f"Найдено {len(trades)} торгов")
    save_to_csv(trades)
