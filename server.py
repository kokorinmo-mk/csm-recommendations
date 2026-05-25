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
# КОНФИГУРАЦИЯ
# ============================================================
GIGACHAT_CREDENTIALS = {
    "credentials": os.environ.get("GIGACHAT_CREDENTIALS", ""),
    "scope": "GIGACHAT_API_PERS",
    "verify_ssl_certs": False,
    "model": "GigaChat"
}

# URL для получения материалов из Google Sheets (твой новый скрипт)
MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

# URL для сохранения рекомендаций в Google Sheets
SAVE_TO_SHEETS_URL = "https://script.google.com/macros/s/AKfycbw23tamPZcP3VTYP6nHIJacjGChp6XryrRXGPY_ogU3ww1n5AiEqa2G0V5P0SNZO4KGkw/exec"

# ============================================================
# ЗАГРУЗКА МАТЕРИАЛОВ ИЗ GOOGLE SHEETS
# ============================================================
def load_materials_from_sheets():
    """Загружает курсы из листа 'Материалы для рекомендаций'"""
    try:
        response = requests.get(MATERIALS_URL)
        if response.status_code == 200:
            materials = response.json()
            print(f"✅ Загружено {len(materials)} материалов")
            return materials
        else:
            print(f"❌ Ошибка загрузки материалов: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Ошибка при загрузке материалов: {e}")
        return {}

# ============================================================
# СОХРАНЕНИЕ РЕКОМЕНДАЦИЙ В GOOGLE SHEETS
# ============================================================
def save_recommendations_to_sheets(user_name, user_email, recommendations):
    """Сохраняет рекомендации в Google Sheets"""
    try:
        payload = {
            "userName": user_name,
            "userEmail": user_email,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        response = requests.post(SAVE_TO_SHEETS_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Рекомендации сохранены в Sheets")
            return True
        else:
            print(f"❌ Ошибка сохранения: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

# ============================================================
# ФОРМИРОВАНИЕ ПРОМПТА С МАТЕРИАЛАМИ
# ============================================================
def build_prompt(user_name, self_ratings, test_scores, materials):
    """Формирует промпт с абсолютно жесткой логикой и проверкой"""
    
    # Форматируем материалы
    materials_text = ""
    for area, items in materials.items():
        materials_text += f"\n### {area}\n"
        courses = [item for item in items if item['name'].startswith('[Курс]')]
        articles = [item for item in items if item['name'].startswith('[Статья]')]
        videos = [item for item in items if item['name'].startswith('[Видео]')]
        
        if courses:
            materials_text += "**[Курсы]**\n"
            for c in courses[:3]:
                materials_text += f"• {c['name']} — {c['url']}\n"
        if articles:
            materials_text += "**[Статьи]**\n"
            for a in articles[:3]:
                materials_text += f"• {a['name']} — {a['url']}\n"
        if videos:
            materials_text += "**[Видео]**\n"
            for v in videos[:3]:
                materials_text += f"• {v['name']} — {v['url']}\n"
    
    # Преобразуем данные для проверки
    all_self_10 = all(r == 10 for r in self_ratings)
    all_test_100 = all(s == 100 for s in test_scores)
    
    # КРИТИЧЕСКИ ВАЖНО: явная проверка
    if all_self_10 and all_test_100:
        # Поздравление
        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

Пользователь {user_name} достиг максимальных результатов:
- Все оценки самооценки = 10
- Все результаты теста = 100%

Напиши короткое поздравление (3-4 предложения) с рекомендацией стать наставником.
Формат: просто текст, без лишних деталей.
"""
    else:
        # Анализ и рекомендации
        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

Данные пользователя:
- ФИО: {user_name}
- Результаты самооценки (1-10): {self_ratings}
- Результаты теста (%): {test_scores}

### Доступные материалы (бери ссылки ТОЛЬКО отсюда):
{materials_text}

### Твоя задача (выполни строго):

1. НЕ ПИШИ ПОЗДРАВЛЕНИЕ. Пользователь НЕ достиг максимальных результатов.
2. Найди области с низкими баллами (самооценка < 7 ИЛИ тест < 75%).
3. Выбери ТОП-3 области с САМЫМИ НИЗКИМИ баллами.
4. Для каждой области напиши в формате:

**N. Название области**

📊 Результаты: самооценка — X/10, тест — Y%

📚 Рекомендую изучить:

**[Курсы]**
• Название курса — ссылка

**[Статьи]**
• Название статьи — ссылка

**[Видео]**
• Название видео — ссылка

5. Если каких-то материалов нет в списке, пропусти раздел.

### Важно:
- Используй ТОЛЬКО ссылки из списка материалов.
- НЕ ПИШИ "Поздравляем", если баллы не максимальные.
- Ответ ТОЛЬКО на русском языке.
"""
    return prompt

# ============================================================
# РАБОТА С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores, materials):
    """Отправляет запрос к GigaChat и возвращает рекомендации"""
    
    # Диагностика - выводим полученные данные
    print(f"🔍 ДИАГНОСТИКА:")
    print(f"   - Имя пользователя: {user_name}")
    print(f"   - Самооценка (первые 10 значений): {self_ratings[:10] if len(self_ratings) > 10 else self_ratings}")
    print(f"   - Тест (первые 10 значений): {test_scores[:10] if len(test_scores) > 10 else test_scores}")
    print(f"   - Все оценки = 10? {all(r == 10 for r in self_ratings) if self_ratings else False}")
    print(f"   - Все тесты = 100? {all(s == 100 for s in test_scores) if test_scores else False}")
    print(f"   - Количество областей с низкими баллами: {sum(1 for r in self_ratings if r < 7) if self_ratings else 0}")
    
    # Формируем промпт
    prompt = build_prompt(user_name, self_ratings, test_scores, materials)
    
    # Сохраняем промпт в файл для отладки (опционально)
    print(f"📝 Промпт отправлен GigaChat (первые 500 символов): {prompt[:500]}...")
    
    try:
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS["credentials"],
            scope=GIGACHAT_CREDENTIALS["scope"],
            verify_ssl_certs=False,
            model=GIGACHAT_CREDENTIALS["model"],
            timeout=120
        ) as giga:
            response = giga.chat(prompt)
            result = response.choices[0].message.content
            print(f"💡 Ответ GigaChat получен (длина: {len(result)} символов)")
            print(f"📄 Первые 300 символов ответа: {result[:300]}...")
            return result
    except Exception as e:
        print(f"❌ ОШИБКА GigaChat: {e}")
        return get_fallback_recommendations()

def get_fallback_recommendations():
    return """
1. Область 1. Осознание (Изучите тренды AI, Big Data, Cloud. Рекомендуем курс «Введение в искусственный интеллект»)
2. Область 2. Стратегия (Изучите Business Model Canvas. Курс «Стратегия Сбера»)
3. Область 6. Общесистемные компетенции (Освойте GigaChat. Курс «Работа с LLM GigaChat»)
"""

# ============================================================
# ЭНДПОИНТЫ
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
        
        # Загружаем материалы из Google Sheets
        materials = load_materials_from_sheets()
        
        # Получаем рекомендации от GigaChat
        recommendations = get_gigachat_recommendations(user_name, self_ratings, test_scores, materials)
        print(f"💡 Рекомендации получены от GigaChat")
        
        # Сохраняем в Google Sheets
        saved = save_recommendations_to_sheets(user_name, user_email, recommendations)
        
        if saved:
            return jsonify({
                "success": True,
                "message": "Рекомендации сохранены. Письмо будет отправлено автоматически."
            })
        else:
            return jsonify({"success": False, "message": "Ошибка сохранения"}), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=5000, debug=True)
