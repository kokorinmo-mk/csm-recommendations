#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests

app = Flask(__name__)
CORS(app)

# ============================================================
# НАСТРОЙКИ QWEN через OpenRouter
# ============================================================

QWEN_API_KEY = "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"
QWEN_BASE_URL = "https://openrouter.ai/api/v1"
QWEN_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"

# Инициализация клиента
client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

# URL твоего Google Apps Script
MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

def load_materials():
    """Загружает материалы из Google Apps Script (JSON)"""
    try:
        response = requests.get(MATERIALS_URL)
        data = response.json()
        
        result = []
        for area, items in data.items():
            result.append(f"\n### {area}")
            # Берём первые 5 материалов на область, чтобы не перегружать
            for item in items[:5]:
                result.append(f"{item['name']} | {item['url']}")
        
        print(f"✅ Загружено материалов: {len(result)}")
        return "\n".join(result)
    except Exception as e:
        print(f"❌ Ошибка загрузки материалов: {e}")
        return ""

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Сервер CSM 2.0 работает на Qwen"})

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        print(f"📨 Получен запрос от: {data.get('userName')}")

        user_name = data.get('userName')
        user_email = data.get('userEmail')
        test_scores = data.get('testScores', [])

        if not test_scores or len(test_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные теста"}), 400

        area_names = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]

        scores_text = ""
        for i, name in enumerate(area_names):
            scores_text += f"{name}: {test_scores[i]}%\n"

        materials_csv = load_materials()

        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

### ВХОДНЫЕ ДАННЫЕ:
- Имя пользователя: {user_name}
- Почта пользователя: {user_email}
- Результаты теста: {scores_text} (содержит 8 областей и процент по каждой)
- Список материалов (курсы, статьи, видео со ссылками):
{materials_csv}

### ЧТО ТЫ ДЕЛАЕШЬ ВНУТРИ СЕБЯ (алгоритм):
1. Проверяешь: каждая ли из 8 областей имеет 100%?
   - Если ДА → переходишь к п.6
   - Если НЕТ → продолжаешь
2. Отбираешь области, где процент < 100%
3. Сортируешь их по возрастанию процента (от худшего к лучшему)
4. Берёшь первые 3 области из отсортированного списка
5. Для каждой из 3 областей подбираешь из списка материалов:
   - 3 курса (с названиями и ссылками)
   - 3 статьи (с названиями и ссылками)
   - 3 видео (с названиями и ссылками)
6. Формируешь выходные данные по шаблону (см. ниже)

### ВЫХОДНЫЕ ДАННЫЕ (что выводишь пользователю):

**Если все 8 областей = 100%:**
{user_name}, поздравляем! Вы набрали 100% по всем компетенциям CSM 2.0. Отличный результат!

**Если есть области с <100% (выводишь ТОЛЬКО 3 самые слабые области):**

{user_name}, ваши результаты теста CSM 2.0:

**[Название области 1]**
📊 Результат: X%
📚 Рекомендуем изучить:
**[Курсы]**
• [Название курса](ссылка)
• [Название курса](ссылка)
• [Название курса](ссылка)
**[Статьи]**
• [Название статьи](ссылка)
• [Название статьи](ссылка)
• [Название статьи](ссылка)
**[Видео]**
• [Название видео](ссылка)
• [Название видео](ссылка)
• [Название видео](ссылка)

**[Название области 2]**
📊 Результат: X%
📚 Рекомендуем изучить:
... (то же самое: 3 курса, 3 статьи, 3 видео)

**[Название области 3]**
📊 Результат: X%
📚 Рекомендуем изучить:
... (то же самое)

### ЖЁСТКИЕ ОГРАНИЧЕНИЯ:
- Не выводишь никаких областей, кроме трёх самых слабых
- Не выводишь советы, выводы, «что делать дальше»
- Не выводишь свой внутренний ход мыслей
- Не добавляешь фраз вроде «нет материалов» — используешь только те ссылки, что есть в списке
- Ответ строго на русском языке
- ВСЕ ССЫЛКИ ДОЛЖНЫ БЫТЬ В ФОРМАТЕ [Название](URL). НЕЛЬЗЯ ПИСАТЬ URL ОТДЕЛЬНО.
"""

        print("🤖 Отправляю запрос в Qwen...")

        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            timeout=120
        )

        recommendations = response.choices[0].message.content
        print("✅ Рекомендации получены от Qwen")

        return jsonify({
            "success": True,
            "recommendations": recommendations
        })

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
