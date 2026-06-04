#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests

app = Flask(__name__)
CORS(app)

QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
QWEN_BASE_URL = "https://openrouter.ai/api/v1"

# Список бесплатных моделей
FREE_MODELS = [
    "nvidia/nemotron-3-super",
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m2.5",
    "qwen/qwen3.6-plus-preview:free",
    "baidu/cobuddy",
    "nvidia/nemotron-nano-9b-v2",
    "openrouter/free",
]

client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

def load_materials():
    """Загружает материалы из Google Apps Script (JSON)"""
    try:
        response = requests.get(MATERIALS_URL)
        data = response.json()
        result = []
        for area, items in data.items():
            result.append(f"\n### {area}")
            for item in items[:9]:  # 9 материалов = 3 курса + 3 статьи + 3 видео
                result.append(f"{item['name']} | {item['url']}")
        print(f"✅ Загружено материалов: {len(result)}")
        return "\n".join(result)
    except Exception as e:
        print(f"❌ Ошибка загрузки материалов: {e}")
        return ""

def get_recommendations_from_model(model_id, prompt):
    print(f"   Пробую модель: {model_id}...")
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
            timeout=90
        )
        recommendations = response.choices[0].message.content
        print(f"   ✅ Модель {model_id} ответила успешно.")
        return recommendations
    except Exception as e:
        print(f"   ❌ Модель {model_id} не отвечает: {e}")
        return None

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Сервер CSM 2.0 работает"})

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
- Список материалов (для каждой области: 3 курса, 3 статьи, 3 видео):
{materials_csv}

### АЛГОРИТМ:
1. Найди области с результатом < 100%
2. Отсортируй их по возрастанию процентов (худшие первые)
3. Возьми первые 3 области
4. Для КАЖДОЙ из выбранных областей:
   - Выбери 3 курса из списка материалов для этой области
   - Выбери 3 статьи из списка материалов для этой области
   - Выбери 3 видео из списка материалов для этой области

### ВЫХОДНЫЕ ДАННЫЕ (строго по шаблону):

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

**[Название области 3]**
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

### ПРАВИЛА:
- ТОЛЬКО 3 самые слабые области
- ТОЛЬКО ссылки из списка материалов выше
- Формат ссылок: [Название](URL)
- НЕ ДОБАВЛЯЙ никаких советов, выводов, "что делать дальше"
- ОТВЕТ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ
"""

        if not QWEN_API_KEY:
            return jsonify({"success": False, "error": "QWEN_API_KEY не настроен"}), 500

        print("🤖 Отправляю запрос к моделям...")
        recommendations = None
        for model in FREE_MODELS:
            recommendations = get_recommendations_from_model(model, prompt)
            if recommendations:
                break

        if not recommendations:
            return jsonify({"success": False, "error": "Сервис временно недоступен"}), 503

        print("✅ Рекомендации получены")
        return jsonify({"success": True, "recommendations": recommendations})

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)