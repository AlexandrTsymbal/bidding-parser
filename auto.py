import os
import time
import csv
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from parser import get_all_trades_by_region
import telegram
from telegram.constants import ParseMode
from utils import extract_vin, estimate_car_price
import asyncio

# ================= НАСТРОЙКИ =================
TELEGRAM_TOKEN = "8425814101:AAEBGmfEYtG2LK4eW03UEU3rz4u068QY0WM"
TELEGRAM_CHAT_ID = "-1002852880660"
CSV_FILE = "trades_auto.csv"
REGION_CODE = 65  # Москва
MAX_PAGES = 5
MAX_AGE_HOURS = 15  # отсеиваем старые объявления
PAUSE_BETWEEN_REQUESTS = 0.5  # пауза между запросами к карточке

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# ============================================

def get_trade_details(url):
    """Берём данные с карточки торгов"""
    session = requests.Session()
    response = session.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    })
    soup = BeautifulSoup(response.text, "html.parser")

    # Начальная цена
    price_tag = soup.find("tr", id="ctl00_cphBody_lvLotList_ctrl0_trStartPrice")
    price = ""
    if price_tag:
        td = price_tag.find_all("td")[1]
        price = td.get_text(strip=True)

    # Предмет торгов
    trade_object_tag = soup.find("tr", id="ctl00_cphBody_lvLotList_ctrl0_trTradeObject")
    trade_object = ""
    if trade_object_tag:
        div = trade_object_tag.find("div")
        if div:
            trade_object = div.get_text(strip=True)

    return {
        "Ссылка": url,
        "Начальная цена": price,
        "Предмет торгов": trade_object
    }

async def parse_and_notify():
    """Основная функция: парсим, фильтруем, сохраняем, отправляем в Telegram"""
    print(f"📍 Запуск парсера {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    trades = get_all_trades_by_region(REGION_CODE, max_pages=MAX_PAGES)

    now = datetime.now()
    max_age = now - timedelta(hours=MAX_AGE_HOURS)

    # Загружаем уже сохранённые ID
    seen_ids = set()
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seen_ids.add(row["Номер"])
    except FileNotFoundError:
        pass

    new_trades = []

    for trade in trades:
        # Парсим дату публикации
        try:
            publish_date = datetime.strptime(trade["Дата публикации"], "%d.%m.%Y %H:%M")
        except ValueError:
            publish_date = datetime.strptime(trade["Дата публикации"], "%d.%m.%Y")

        if publish_date < max_age or trade["Номер"] in seen_ids:
            continue

        # Берём данные с карточки торгов
        details = get_trade_details(trade["Ссылка на торги"])
        new_trades.append({**trade, **details})
        seen_ids.add(trade["Номер"])
        descrip = details['Предмет торгов']

        vin_code = extract_vin(descrip)
        if not vin_code:
            vin_code = "не найден"

        car_price = estimate_car_price(descrip)



        # Формируем сообщение и отправляем в Telegram
        msg = (
            f"🆕 <b><code>{trade.get('Номер')}</code></b>\n\n"
            f"📅 {trade.get('Дата публикации')}\n\n"
            f"💰 Начальная цена: <b> {details['Начальная цена']} ₽</b>\n\n"
            f"🚗 Предмет торгов: {descrip}\n\n"
            f"🛠 VIN: <code>{vin_code}</code>\n\n"
            f"🔍 Оценка vb bbbbbbbbbbbbbbbb vbbbbbbbbb565656565656t6 авто от ИИ (носит информативный характер, может содержать грубые ошибки) 🔍\n<i>{car_price}</i>\n\n"
            f"🔗 <a href='{details['Ссылка']}'>Ссылка на торги</a>"
        )
        try:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
            print(f"✅ Отправлено объявление {trade['Номер']}")
        except Exception as e:
            print(f"❌ Ошибка при отправке: {e}")

        time.sleep(PAUSE_BETWEEN_REQUESTS)

    # Сохраняем новые записи в CSV
    if new_trades:
        write_header = not os.path.exists(CSV_FILE)
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=new_trades[0].keys())
            if write_header:
                writer.writeheader()
            writer.writerows(new_trades)
        print(f"✅ Сохранено {len(new_trades)} новых торгов.")
    else:
        print("ℹ️ Новых объявлений нет.")

# ================= MAIN LOOP =================
if __name__ == "__main__":
    while True:
        asyncio.run(parse_and_notify())
        print("⏱ Ожидание 1 час до следующего запуска...")
        time.sleep(1 * 60 * 60)  # 2 часа
