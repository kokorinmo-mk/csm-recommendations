#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from gigachat import GigaChat
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================
# НАСТРОЙКИ - читаем из переменных окружения Render
# ============================================================
GIGACHAT_CREDENTIALS = {
    "credentials": os.environ.get("GIGACHAT_CREDENTIALS", ""),
    "scope": "GIGACHAT_API_PERS",
    "verify_ssl_certs": False,
    "model": "GigaChat"
}

# ⚠️ ВАЖНО: Укажите URL вашего Apps Script для сохранения в Google Sheets
# Замените на ваш URL из шага 3
SAVE_TO_SHEETS_URL = "https://script.google.com/macros/s/AKfycbw23tamPZcP3VTYP6nHIJacjGChp6XryrRXGPY_ogU3ww1n5AiEqa2G0V5P0SNZO4KGkw/exec"

# ============================================================
# ФУНКЦИЯ ДЛЯ СОХРАНЕНИЯ РЕКОМЕНДАЦИЙ В GOOGLE SHEETS
# ============================================================
def save_recommendations_to_sheets(user_name, user_email, recommendations):
    """Сохраняет рекомендации в Google Sheets через Apps Script"""
    try:
        payload = {
            "userName": user_name,
            "userEmail": user_email,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📤 Отправка рекомендаций в Google Sheets...")
        
        # Отправляем в Google Sheets
        response = requests.post(SAVE_TO_SHEETS_URL, json=payload)
        
        if response.status_code == 200:
            print(f"✅ Рекомендации сохранены в Google Sheets")
            return True
        else:
            print(f"❌ Ошибка сохранения: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
        return False

# ============================================================
# ФУНКЦИЯ ДЛЯ РАБОТЫ С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores):
    """Отправляет запрос к GigaChat и возвращает рекомендации"""
    
    # Формируем промпт
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0. Пользователь прошёл самооценку и тест.

Данные пользователя:
- ФИО: {user_name}

Результаты самооценки (оценки от 1 до 10, где 1 — совсем не владею, 10 — эксперт):
{json.dumps(self_ratings, ensure_ascii=False, indent=2)}

Результаты теста (проценты правильных ответов):
{json.dumps(test_scores, ensure_ascii=False, indent=2)}

Сформируй ТОП-3 области компетенций, которые требуют развития.
Для каждой области напиши в формате:
N. [Название области] (Почему? На что обратить внимание? Какие материалы изучить?)

Будь конкретным, дружелюбным. Ответ только на русском языке.
"""

    try:
        # Подключаемся к GigaChat с увеличенным таймаутом
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS["credentials"],
            scope=GIGACHAT_CREDENTIALS["scope"],
            verify_ssl_certs=False,
            model=GIGACHAT_CREDENTIALS["model"],
            timeout=120
        ) as giga:
            response = giga.chat(prompt)
            return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Ошибка GigaChat: {e}")
        return get_fallback_recommendations()

def get_fallback_recommendations():
    return """
1. Область 1. Осознание (Рекомендуется изучить современные тренды: AI, Big Data, IoT, Cloud. Обратите внимание на архитектуру цифровой трансформации.)

2. Область 2. Стратегия (Развивайте стратегическое мышление, изучите Business Model Canvas и карту гипотез.)

3. Область 6. Общесистемные компетенции (Освойте инструменты CSM и генеративные модели вроде GigaChat для повышения эффективности.)
"""

# ============================================================
# ЭНДПОИНТЫ СЕРВЕРА
# ============================================================
@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "OK", "message": "Сервер CSM 2.0 работает!"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": str(datetime.now())})

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        print(f"📨 Получен запрос от: {data.get('userName')}")
        
        user_name = data.get('userName')
        user_email = data.get('userEmail')
        self_ratings = data.get('selfRatings', [])
        test_scores = data.get('testScores', [])
        
        # Получаем рекомендации от GigaChat
        recommendations = get_gigachat_recommendations(user_name, self_ratings, test_scores)
        print(f"💡 Рекомендации получены от GigaChat")
        
        # Сохраняем рекомендации в Google Sheets
        saved = save_recommendations_to_sheets(user_name, user_email, recommendations)
        
        if saved:
            return jsonify({
                "success": True,
                "message": "Рекомендации сохранены в Google Sheets. Письмо будет отправлено автоматически."
            })
        else:
            return jsonify({
                "success": False,
                "message": "Не удалось сохранить рекомендации"
            }), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=5000, debug=True)
