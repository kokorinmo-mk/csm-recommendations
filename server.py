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
QWEN_MODEL = "openrouter/free"

client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

def load_materials():
    """Загружает ТОЛЬКО нужные материалы для слабых областей"""
    try:
        response = requests.get(MATERIALS_URL, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return {}

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

        # Находим 3 самые слабые области
        weak_areas = []
        for i, score in enumerate(test_scores):
            if score < 100:
                weak_areas.append((area_names[i], score))
        
        weak_areas.sort(key=lambda x: x[1])
        top_weak = weak_areas[:3]
        
        if not top_weak:
            return jsonify({
                "success": True,
                "recommendations": f"🎉 Поздравляем, {user_name}! Вы набрали 100% по всем компетенциям!"
            })
        
        # Загружаем все материалы
        all_materials = load_materials()
        
        # Формируем короткий промпт ТОЛЬКО для слабых областей
        materials_text = ""
        for area, score in top_weak:
            materials_text += f"\n### {area}\n"
            if area in all_materials:
                for item in all_materials[area][:9]:
                    materials_text += f"{item['name']} | {item['url']}\n"
        
        scores_text = ""
        for area, score in top_weak:
            scores_text += f"{area}: {score}%\n"
        
        prompt = f"""Ты эксперт CSM 2.0.

Результаты пользователя {user_name}:
{scores_text}

Материалы для этих областей:
{materials_text}

Для каждой области выбери 3 курса, 3 статьи, 3 видео.
Формат:
**Название области**
📊 Результат: X%
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

Только ссылки из списка выше. Только русский язык. Без лишних слов."""

        print("🤖 Отправляю запрос в LLM...")
        
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=3000,
            timeout=60
        )

        recommendations = f"{user_name}, ваши результаты теста CSM 2.0:\n\n{response.choices[0].message.content}"
        print("✅ Рекомендации получены")
        
        return jsonify({"success": True, "recommendations": recommendations})

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)