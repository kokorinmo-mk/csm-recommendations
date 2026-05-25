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
    """Промпт с правилами 1-10 — НЕ МЕНЯТЬ БЕЗ СОГЛАСОВАНИЯ"""
    
    # self_ratings и test_scores — списки из 8 элементов
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
    
    # Формируем строку с данными
    data_text = ""
    for i, name in enumerate(area_names):
        self_val = self_ratings[i] if i < len(self_ratings) else 0
        test_val = test_scores[i] if i < len(test_scores) else 0
        data_text += f"{i+1}. {name} — самооценка: {self_val}/10, тест: {test_val}%\n"
    
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
    
    # Промпт
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

Пользователь: {user_name}

### Данные по 8 областям:

{data_text}

### Доступные материалы:
{materials_text}

### Твоя задача — выполнить правила (ничего не меняй, не добавляй от себя):

**ПРАВИЛО 1:**
Если тест по ВСЕМ 8 областям = 100% И самооценка по ВСЕМ 8 областям = 10, то напиши ТОЛЬКО это:
🎉 Поздравляем, {user_name}! Вы показали максимальные результаты по всем компетенциям CSM 2.0.
Вы находитесь на экспертном уровне. Рекомендуем:
• Выступать в роли наставника для коллег
• Делиться опытом на внутренних мероприятиях
• Участвовать в развитии программы CSM 2.0
Если вы хотите развиваться дальше, обратитесь к руководителю — вместе вы сможете сформировать индивидуальный план развития (ИПР).

**ПРАВИЛО 2:**
Если самооценка по ВСЕМ 8 областям = 10, НО есть ошибки в тесте (<100%), то выведи рекомендации ТОЛЬКО по областям, где тест <100%. Выбери не больше 3 областей с САМЫМИ НИЗКИМИ процентами теста.

**ПРАВИЛО 3:**
Если тест по ВСЕМ 8 областям = 100%, НО самооценка <10 хотя бы в одной области, то сначала напиши: "Несмотря на то, что тест пройден на 100%, обратите внимание на области, где вы оценили себя ниже 10 баллов." Затем выведи рекомендации ТОЛЬКО по областям, где самооценка <7. Выбери не больше 3 областей с САМЫМИ НИЗКИМИ баллами самооценки.

**ПРАВИЛО 4:**
Если пользователь ошибся в тесте во ВСЕХ 8 областях (<100% везде), выведи ТОП-3 области с САМЫМИ НИЗКИМИ процентами теста (самооценку не учитывай).

**ПРАВИЛО 5:**
Если ошибки в тесте есть, но не во всех областях, выбери области где тест <75% ИЛИ самооценка <7. Выбери ТОП-3 с САМЫМИ НИЗКИМИ процентами теста. Если проценты одинаковые — учитывай самооценку (чем ниже, тем приоритетнее).

**ФОРМАТ для каждой рекомендации:**
#### **Название области**
📊 Результаты: самооценка — X/10, тест — Y%
📚 Рекомендую изучить:
**[Курсы]**
• [Название курса](ссылка)
**[Статьи]**
• [Название статьи](ссылка)
**[Видео]**
• [Название видео](ссылка)

**ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:**
- ВЫБИРАЙ ТОЛЬКО 3 ОБЛАСТИ. НЕ БОЛЬШЕ.
- ДЛЯ КАЖДОЙ ОБЛАСТИ ОБЯЗАТЕЛЬНО ДОБАВЛЯЙ СТАТЬИ И ВИДЕО. ЕСЛИ ИХ НЕТ — НАПИШИ "— НЕТ В НАЛИЧИИ".
- НАЗВАНИЕ ОБЛАСТИ ВЫДЕЛЯЙ ЖИРНЫМ: **Название области**
- НЕ ПИШИ области, которые не подходят под правила
- НЕ ДОБАВЛЯЙ советы, заключения или "что делать дальше"
- Используй ТОЛЬКО ссылки из списка материалов
- Ответ только на русском языке
"""
    return prompt
    
# ============================================================
# РАБОТА С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores, materials):
    """Отправляет запрос к GigaChat и возвращает рекомендации"""
    
    prompt = build_prompt(user_name, self_ratings, test_scores, materials)
    
    print(f"\n{'='*80}")
    print(f"🔍 ПРОМПТ ДЛЯ GIGACHAT (полностью):")
    print(f"{'='*80}")
    print(prompt)
    print(f"{'='*80}\n")
    
    try:
        # Проверка наличия credentials
        if not GIGACHAT_CREDENTIALS.get("credentials"):
            print("❌ ОШИБКА: GIGACHAT_CREDENTIALS не найдены в переменных окружения")
            return get_fallback_recommendations()
        
        print(f"🔑 Используем credentials: {GIGACHAT_CREDENTIALS['credentials'][:20]}...")
        print(f"⏳ Отправляем запрос к GigaChat...")
        
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS["credentials"],
            scope=GIGACHAT_CREDENTIALS["scope"],
            verify_ssl_certs=False,
            model=GIGACHAT_CREDENTIALS["model"],
            timeout=120
        ) as giga:
            response = giga.chat(prompt, max_tokens=2000)
            result = response.choices[0].message.content
            
            print(f"\n{'='*80}")
            print(f"✅ ОТВЕТ GIGACHAT (успешно получен):")
            print(f"{'='*80}")
            print(result)
            print(f"{'='*80}\n")
            
            return result
            
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ ОШИБКА GIGACHAT:")
        print(f"   Тип ошибки: {type(e).__name__}")
        print(f"   Текст: {e}")
        print(f"{'='*80}\n")
        return get_fallback_recommendations()
        
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
