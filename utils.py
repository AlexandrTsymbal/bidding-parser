import re
import os
from groq import Groq

# Инициализация клиента


def extract_vin(text: str) -> str | None:
    """
    Извлекает первую строку из текста, подходящую под шаблон VIN (17 символов из A–H, J–N, P, R–Z, 0–9).
    Возвращает найденную строку или None, если совпадений нет.
    """
    pattern = r"\b[A-HJ-NPR-Z0-9]{17}\b"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def estimate_car_price(description: str) -> str:
    """
    Определяет примерную рыночную стоимость автомобиля по текстовому описанию.
    Возвращает строку вроде:
    "Примерная рыночная цена такого автомобиля 350.000 рублей"
    """
    prompt = f"""
Ты — эксперт по оценке автомобилей на вторичном рынке России 2025.
Оцени максимально точно рыночную стоимость автомобиля в Екатеринбурге по следующему описанию:

{description}

Формат ответа:
"Примерная рыночная цена такого автомобиля <сумма> рублей"

Не добавляй ничего лишнего, только фразу в заданном формате.
Если данных недостаточно — сделай разумное предположение.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты помощник по автооценке."},
            {"role": "user", "content": prompt}
        ],
        temperature=1  # пониже для стабильных оценок
    )

    return completion.choices[0].message.content.strip()
