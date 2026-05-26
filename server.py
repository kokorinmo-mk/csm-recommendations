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

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"
SAVE_TO_SHEETS_URL = "https://script.google.com/macros/s/AKfycbw23tamPZcP3VTYP6nHIJacjGChp6XryrRXGPY_ogU3ww1n5AiEqa2G0V5P0SNZO4KGkw/exec"

# ============================================================
# ЗАГРУЗКА МАТЕРИАЛОВ
# ============================================================
def load_materials_from_sheets():
    try:
        response = requests.get(MATERIALS_URL, timeout=30)
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
# СОХРАНЕНИЕ РЕКОМЕНДАЦИЙ
# ============================================================
def save_recommendations_to_sheets(user_name, user_email, recommendations):
    try:
        payload = {
            "userName": user_name,
            "userEmail": user_email,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        response = requests.post(SAVE_TO_SHEETS_URL, json=payload, timeout=30)
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
# ФОРМИРОВАНИЕ ПРОМПТА
# ============================================================
def build_prompt(user_name, user_email, self_ratings, test_scores, materials):
    """Формирует промпт с данными построчно"""
    
    area_names = [
        "Осознание",
        "Стратегия",
        "Реинжиниринг процессов и оргструктуры",
        "Проектирование и разработка решения",
        "Внедрение и развитие решения",
        "Общесистемные компетенции и методология проектов развития",
        "Отраслевые компетенции",
        "Soft skills"
    ]
    
    # Преобразуем списки в объекты с названиями областей
    self_ratings_obj = {}
    test_scores_obj = {}
    
    for i, name in enumerate(area_names):
        self_ratings_obj[name] = self_ratings[i] if i < len(self_ratings) else 0
        test_scores_obj[name] = test_scores[i] if i < len(test_scores) else 0
    
    # Формируем строку с данными построчно
    data_text = f"Имя: {user_name}\n"
    data_text += f"Почта: {user_email}\n"
    data_text += f"Самооценка:\n"
    for name in area_names:
        data_text += f"{name}: {self_ratings_obj[name]}\n"
    data_text += f"Тест:\n"
    for name in area_names:
        data_text += f"{name}: {test_scores_obj[name]}%\n"
    
    # Форматируем материалы
    materials_text = ""
    for area, items in materials.items():
        materials_text += f"\n### {area}\n"
        courses = [item for item in items if item['name'].startswith('[Курс]')][:3]
        articles = [item for item in items if item['name'].startswith('[Статья]')][:3]
        videos = [item for item in items if item['name'].startswith('[Видео]')][:3]
        
        if courses:
            materials_text += "**[Курсы]**\n"
            for c in courses:
                materials_text += f"• [{c['name']}]({c['url']})\n"
        if articles:
            materials_text += "**[Статьи]**\n"
            for a in articles:
                materials_text += f"• [{a['name']}]({a['url']})\n"
        if videos:
            materials_text += "**[Видео]**\n"
            for v in videos:
                materials_text += f"• [{v['name']}]({v['url']})\n"
    
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

### Данные пользователя:
{data_text}

### Доступные материалы:
{materials_text}

### ПРАВИЛА (ВЫПОЛНИ СТРОГО):

**Условие 1: Максимальные результаты**
Если самооценка по ВСЕМ областям равна 10 баллов И тест по ВСЕМ областям равен 100%, то напиши ТОЛЬКО это:
🎉 Поздравляем, {user_name}! Вы показали максимальные результаты по всем компетенциям CSM 2.0. Вы находитесь на экспертном уровне. 
Рекомендуем: 
* Выступать в роли наставника для коллег
* Делиться опытом
* Участвовать в развитии программы CSM 2.0
Если ищете направления для развития - обратитесь к руководителю для формирования ИПР.

**Условие 2: Есть области с тестом менее 100%**
Найди области, где тест МЕНЕЕ 100%. Отсортируй их по возрастанию процентов (сначала самые низкие). Выбери не больше 3 областей (самые низкие проценты). Для каждой выбранной области напиши рекомендации.

**Условие 3: Больше 3 областей с тестом менее 100%**
Если таких областей больше 3, выбери ТОЛЬКО 3 области с САМЫМИ НИЗКИМИ процентами теста. Остальные не упоминай.

**Условие 4: Названия областей**
Используй ТОЛЬКО исходные названия областей из списка выше. Не меняй, не сокращай, не добавляй нумерацию.

**Условие 5: Материалы**
Используй ТОЛЬКО те названия курсов, статей, видео и ссылки, которые даны в списке доступных материалов. НЕ ПРИДУМЫВАЙ свои.

**Условие 6: Формат вывода для каждой области**
**Название области**
📊 Результаты теста: Y%
📚 Рекомендуем изучить:
**[Курсы]**
• [Название курса](ссылка)
**[Статьи]**
• [Название статьи](ссылка)
**[Видео]**
• [Название видео](ссылка)

### ВАЖНО:
- Не добавляй никаких советов, заключений или "что делать дальше"
- Не пиши области, которые не подходят под условия
- Если для области нет какого-то типа материалов (курсы, статьи, видео), напиши "Нет в наличии"
- Ответ только на русском языке
"""
    return prompt

# ============================================================
# РАБОТА С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores, materials):
    print(f"\n📊 Данные: самооценка={self_ratings}, тест={test_scores}")
    
    prompt = build_prompt(user_name, self_ratings, test_scores, materials)
    
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
            print(f"✅ Ответ получен")
            return result
    except Exception as e:
        print(f"❌ Ошибка GigaChat: {e}")
        return get_fallback_recommendations()

def get_fallback_recommendations():
    return """
#### **Осознание**
📊 Результаты: самооценка — 7/10, тест — 50%
📚 Рекомендую изучить:
**[Курсы]**
• [Курс «ESG: выбирая будущее»](https://hr.sberbank.ru/...)
**[Статьи]**
• [Статья «Стратегия 2026»](https://hr.sberbank.ru/...)
**[Видео]**
• [Видео «ПСС: Ориентация на клиента»](https://hr.sberbank.ru/...)
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
        
        # Получаем данные в твоём формате (объекты с ключами "Область N. Название")
        self_ratings_dict = data.get('selfRatings', {})
        test_scores_dict = data.get('testScores', {})
        
        print(f"📊 Самооценка (сырые данные): {self_ratings_dict}")
        print(f"📊 Тест (сырые данные): {test_scores_dict}")
        
        # Список ключей в том порядке, в котором они приходят из index.html
        area_keys = [
            "Область 1. Осознание",
            "Область 2. Стратегия",
            "Область 3. Реинжиниринг процессов и оргструктуры",
            "Область 4. Проектирование и разработка решения",
            "Область 5. Внедрение и развитие решения",
            "Область 6. Общесистемные компетенции и методология проектов развития",
            "Область 7. Отраслевые компетенции",
            "Область 8. Soft skills"
        ]
        
        # Преобразуем в простые списки (8 значений)
        self_ratings = [self_ratings_dict.get(key, 0) for key in area_keys]
        test_scores = [test_scores_dict.get(key, 0) for key in area_keys]
        
        print(f"📊 Самооценка (список 8 значений): {self_ratings}")
        print(f"📊 Тест (список 8 значений): {test_scores}")
        
        materials = load_materials_from_sheets()
        recommendations = get_gigachat_recommendations(user_name, self_ratings, test_scores, materials)
        
        saved = save_recommendations_to_sheets(user_name, user_email, recommendations)
        
        if saved:
            return jsonify({"success": True, "message": "Рекомендации сохранены"})
        else:
            return jsonify({"success": False, "message": "Ошибка сохранения"}), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=5000, debug=True)
