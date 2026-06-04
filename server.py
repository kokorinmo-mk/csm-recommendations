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
# КЛЮЧ БЕРЁТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (Render Environment Variables)
# ============================================================

QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
QWEN_BASE_URL = "https://openrouter.ai/api/v1"
QWEN_MODEL = "qwen/qwen3.6-plus-preview:free"  # БЕСПЛАТНО!

if not QWEN_API_KEY:
    print("⚠️ ВНИМАНИЕ: QWEN_API_KEY не задан! Добавьте его в Environment Variables на Render")

client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

def load_materials():
    try:
        response = requests.get(MATERIALS_URL)
        data = response.json()
        result = []
        for area, items in data.items():
            result.append(f"\n### {area}")
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
        print(f"📨 Запрос от: {data.get('userName')}")

        user_name = data.get('userName')
        user_email = data.get('userEmail')
        test_scores = data.get('testScores', [])

        if not test_scores or len(test_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные"}), 400

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
- Результаты теста: {scores_text}
- Список материалов:
{materials_csv}

### АЛГОРИТМ:
1. Найди области с результатом < 100%
2. Отсортируй их по возрастанию (худшие первые)
3. Возьми первые 3 области
4. Для каждой области выбери 3 курса, 3 статьи, 3 видео

### ВЫХОДНЫЕ ДАННЫЕ:

{user_name}, ваши результаты теста CSM 2.0:

**[Название области 1]**
📊 Результат: X%
📚 Рекомендуем изучить:
**[Курсы]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)
**[Статьи]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)
**[Видео]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)

**[Название области 2]**
... (то же самое)

**[Название области 3]**
... (то же самое)

### ПРАВИЛА:
- Только 3 самые слабые области
- Только ссылки из списка выше
- Формат ссылок: [Название](URL)
- Без лишних советов
- Только русский язык
"""

        if not QWEN_API_KEY:
            return jsonify({"success": False, "error": "QWEN_API_KEY не настроен"}), 500

        print("🤖 Отправляю запрос в Qwen...")

        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
            timeout=120
        )

        recommendations = response.choices[0].message.content
        print("✅ Рекомендации получены от Qwen")

        return jsonify({"success": True, "recommendations": recommendations})

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
