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
    """Формирует промпт с жёсткой структурой письма"""
    
    # Форматируем материалы для промпта
    materials_text = ""
    for area, items in materials.items():
        materials_text += f"\n### {area}\n"
        courses = [item for item in items if item['name'].startswith('[Курс]')]
        articles = [item for item in items if item['name'].startswith('[Статья]')]
        videos = [item for item in items if item['name'].startswith('[Видео]')]
        
        if courses:
            materials_text += "**Курсы:**\n"
            for c in courses[:5]:
                materials_text += f"  - {c['name']} | {c['url']} | {c['description']}\n"
        if articles:
            materials_text += "**Статьи:**\n"
            for a in articles[:5]:
                materials_text += f"  - {a['name']} | {a['url']} | {a['description']}\n"
        if videos:
            materials_text += "**Видео:**\n"
            for v in videos[:5]:
                materials_text += f"  - {v['name']} | {v['url']} | {v['description']}\n"
    
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0. Пользователь прошёл самооценку и тест.

Данные пользователя:
- ФИО: {user_name}

Результаты самооценки (оценки от 1 до 10):
{json.dumps(self_ratings, ensure_ascii=False, indent=2)}

Результаты теста (проценты правильных ответов):
{json.dumps(test_scores, ensure_ascii=False, indent=2)}

### Доступные обучающие материалы (бери строго из этого списка):
{materials_text}

### Твоя задача:

#### Шаг 0. Проверь, не достиг ли пользователь максимальных результатов
Если ВСЕ оценки самооценки = 10 И ВСЕ результаты теста = 100, то напиши:

🎉 **Поздравляем, {user_name}!** Вы показали максимальные результаты по всем компетенциям CSM 2.0.

Вы находитесь на экспертном уровне. Рекомендуем:
• Выступать в роли наставника для коллег
• Делиться опытом на внутренних мероприятиях
• Участвовать в развитии программы CSM 2.0

Если вы хотите развиваться дальше, обратитесь к руководителю — вместе вы сможете сформировать индивидуальный план развития (ИПР) с фокусом на углублённые компетенции и лидерские качества.

📌 **Что делать дальше?**
Обсудите эти результаты с руководителем. Вместе вы сможете сформировать индивидуальный план развития (ИПР).

(НА ЭТОМ ОСТАНОВИСЬ, НЕ ПИШИ БОЛЬШЕ НИЧЕГО)

#### Шаг 1. Если НЕ все 10 и НЕ все 100%, то определи ТОП-3 области с самыми низкими результатами
(где самооценка < 7 ИЛИ тест < 75%)

#### Шаг 2. Для КАЖДОЙ области напиши в точном формате:

**N. [Название области]**

📊 **Результаты:** самооценка — X/10, тест — Y%

📚 **Рекомендации:**

**Курсы:**
• [Название курса](ссылка) — краткое описание
• [Название курса](ссылка) — краткое описание

**Статьи:**
• [Название статьи](ссылка) — краткое описание
• [Название статьи](ссылка) — краткое описание

**Видео:**
• [Название видео](ссылка) — краткое описание
• [Название видео](ссылка) — краткое описание

#### Шаг 3. В конце письма добавь блок:

📌 **Что делать дальше?**
Обсудите эти результаты с руководителем. Вместе вы сможете сформировать индивидуальный план развития (ИПР).

### Правила:
- Используй ТОЛЬКО материалы из предоставленного списка
- Для каждой области выбери 2-3 курса, 2-3 статьи, 2-3 видео (если есть)
- Если в списке нет нужного типа материалов для области, напиши "— нет в наличии"
- Ответ ТОЛЬКО на русском языке
- Не добавляй лишних пояснений, только указанный формат
- Не перечисляй области, которые не попали в ТОП-3
"""
    return prompt

# ============================================================
# РАБОТА С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores, materials):
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
            return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Ошибка GigaChat: {e}")
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
