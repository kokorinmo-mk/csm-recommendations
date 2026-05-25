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
    
    # ============================================================
    # ВЫЧИСЛЯЕМ СРЕДНИЕ БАЛЛЫ ПО ОБЛАСТЯМ
    # ============================================================
    # Названия областей (строго 8 штук)
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
    
    # Количество вопросов в каждой области (4, 6, 7, 4, 2, 4, 3, 3)
    questions_per_area = [4, 6, 7, 4, 2, 4, 3, 3]
    
    # Вычисляем средние для самооценки
    self_avg = []
    idx = 0
    for q_count in questions_per_area:
        if idx + q_count <= len(self_ratings):
            area_ratings = self_ratings[idx:idx + q_count]
            avg = round(sum(area_ratings) / q_count, 1)
            self_avg.append(avg)
        else:
            self_avg.append(0)
        idx += q_count
    
    # Вычисляем средние для теста
    test_avg = []
    idx = 0
    for q_count in questions_per_area:
        if idx + q_count <= len(test_scores):
            area_scores = test_scores[idx:idx + q_count]
            avg = round(sum(area_scores) / q_count, 1)
            test_avg.append(avg)
        else:
            test_avg.append(0)
        idx += q_count
    
    # ============================================================
    # ФОРМАТИРУЕМ МАТЕРИАЛЫ
    # ============================================================
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
    
    # ============================================================
    # ФОРМИРУЕМ ПРОМПТ С УСРЕДНЁННЫМИ ДАННЫМИ
    # ============================================================
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

Пользователь: {user_name}

### Данные по 8 областям (средние значения):

1. Осознание — самооценка: {self_avg[0]}/10, тест: {test_avg[0]}%
2. Стратегия — самооценка: {self_avg[1]}/10, тест: {test_avg[1]}%
3. Реинжиниринг процессов и оргструктуры — самооценка: {self_avg[2]}/10, тест: {test_avg[2]}%
4. Проектирование и разработка решения — самооценка: {self_avg[3]}/10, тест: {test_avg[3]}%
5. Внедрение и развитие решения — самооценка: {self_avg[4]}/10, тест: {test_avg[4]}%
6. Общесистемные компетенции и методология проектов развития — самооценка: {self_avg[5]}/10, тест: {test_avg[5]}%
7. Отраслевые компетенции — самооценка: {self_avg[6]}/10, тест: {test_avg[6]}%
8. Soft skills — самооценка: {self_avg[7]}/10, тест: {test_avg[7]}%

### Доступные материалы:
{materials_text}

### ПРАВИЛА (ВЫПОЛНИ СТРОГО, НЕ НАРУШАЙ):

**ПРАВИЛО 1:**
Если тест по ВСЕМ областям = 100% И самооценка по ВСЕМ областям = 10, то напиши ТОЛЬКО это (без ссылок):
🎉 Поздравляем, {user_name}! Вы показали максимальные результаты по всем компетенциям CSM 2.0.
Вы находитесь на экспертном уровне. Рекомендуем:
• Выступать в роли наставника для коллег
• Делиться опытом на внутренних мероприятиях
• Участвовать в развитии программы CSM 2.0
Если вы хотите развиваться дальше, обратитесь к руководителю — вместе вы сможете сформировать индивидуальный план развития (ИПР).

**ПРАВИЛО 2:**
Если самооценка по ВСЕМ областям = 10, НО есть ошибки в тесте (<100%), то выведи рекомендации ТОЛЬКО по областям, где тест <100%. Выбери не больше 3 областей с САМЫМИ НИЗКИМИ процентами теста.

**ПРАВИЛО 3:**
Если тест по ВСЕМ областям = 100%, НО самооценка <10 хотя бы в одной области, то выведи сообщение: "Несмотря на то, что тест пройден на 100%, обратите внимание на области, где вы оценили себя ниже 10 баллов." Затем выведи рекомендации ТОЛЬКО по областям, где самооценка <7. Выбери не больше 3 областей с САМЫМИ НИЗКИМИ баллами самооценки.

**ПРАВИЛО 4:**
Если пользователь ошибся в тесте во ВСЕХ областях (<100% везде), выведи ТОП-3 области с САМЫМИ НИЗКИМИ процентами теста (самооценку не учитывай).

**ПРАВИЛО 5:**
Если тест = 100% по всем областям, а самооценка = 10 по всем областям — используй ПРАВИЛО 1.

**ПРАВИЛО 6:**
Если ошибки в тесте есть, но не во всех областях, выбери области где тест <75% ИЛИ самооценка <7. Выбери ТОП-3 с САМЫМИ НИЗКИМИ процентами теста (при равных процентах — учитывай самооценку).

**ПРАВИЛО 7:**
Формат для каждой рекомендации:
#### **Название области**
📊 Результаты: самооценка — X/10, тест — Y%
📚 Рекомендую изучить:
**[Курсы]**
• [Название](ссылка)
**[Статьи]**
• [Название](ссылка)
**[Видео]**
• [Название](ссылка)

**ПРАВИЛО 8:**
ВЫБИРАЙ ТОЛЬКО 3 ОБЛАСТИ. НЕ 4, НЕ 2, А 3. ЕСЛИ ПОДХОДЯТ БОЛЬШЕ 3 — ВОЗЬМИ 3 С САМЫМИ НИЗКИМИ ПРОЦЕНТАМИ ТЕСТА.

**ПРАВИЛО 9:**
ДЛЯ КАЖДОЙ ВЫБРАННОЙ ОБЛАСТИ ОБЯЗАТЕЛЬНО ДОБАВЛЯЙ СТАТЬИ И ВИДЕО ИЗ СПИСКА МАТЕРИАЛОВ. ЕСЛИ ИХ НЕТ — НАПИШИ "— НЕТ В НАЛИЧИИ".

**ПРАВИЛО 10:**
НАЗВАНИЕ КАЖДОЙ ОБЛАСТИ В РЕКОМЕНДАЦИИ ВЫДЕЛЯЙ ЖИРНЫМ: **Название области**

### ВАЖНО:
- Названия областей пиши в точности как в списке выше (первая буква заглавная, остальные строчные)
- Не добавляй никаких советов, заключений или блоков "что делать дальше"
- Не пиши области, которые не подходят под правила
- Используй ТОЛЬКО ссылки из списка материалов
- Ответ только на русском языке
"""
    return prompt
# ============================================================
# РАБОТА С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores, materials):
    """Отправляет запрос к GigaChat и возвращает рекомендации"""
    
    # ============================================================
    # ДИАГНОСТИКА — ПОСМОТРИМ, ЧТО РЕАЛЬНО ПРИХОДИТ
    # ============================================================
    print(f"\n{'='*60}")
    print(f"🔍 ДИАГНОСТИКА ПЕРЕД ОТПРАВКОЙ В GigaChat:")
    print(f"   - user_name: {user_name}")
    print(f"   - self_ratings (длина {len(self_ratings)}): {self_ratings}")
    print(f"   - test_scores (длина {len(test_scores)}): {test_scores}")
    print(f"{'='*60}\n")
    
    # Формируем промпт
    prompt = build_prompt(user_name, self_ratings, test_scores, materials)
    
    # Сохраняем промпт в лог (первые 1000 символов)
    print(f"📝 ПРОМПТ (первые 1000 символов):\n{prompt[:1000]}...\n")
    
    try:
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS["credentials"],
            scope=GIGACHAT_CREDENTIALS["scope"],
            verify_ssl_certs=False,
            model=GIGACHAT_CREDENTIALS["model"],
            timeout=120
        ) as giga:
            response = giga.chat(prompt, max_tokens=2000)
            result = response.choices[0].message.content
            
            print(f"💡 ОТВЕТ GigaChat (длина {len(result)} символов):")
            print(f"{result[:500]}...\n")
            
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
