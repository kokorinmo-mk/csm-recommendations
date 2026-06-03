#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from gigachat import GigaChat
import requests
import os

app = Flask(__name__)
CORS(app)

GIGACHAT_CREDENTIALS = "MDE5ZDI0NDctNjhmMy03MjU5LTk1M2MtZTYwNzVjYjllNmI1OmU0ZjgyNjdmLTBlYjYtNDhjNC04MTJiLWFiNTJiYTlmM2VmMA=="

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
            for item in items:
                result.append(f"{item['name']} | {item['url']}")
        
        return "\n".join(result)
    except Exception as e:
        print(f"Ошибка загрузки материалов: {e}")
        return ""

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Сервер CSM 2.0 работает"})

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'GET':
        return jsonify({"status": "ok", "message": "Send POST request with userName, userEmail, testScores"})
    
    try:
        data = request.get_json()
        print(f"📨 Получен запрос от: {data.get('userName')}")
        
        user_name = data.get('userName')
        user_email = data.get('userEmail')
        test_scores = data.get('testScores', [])
        
        if not test_scores or len(test_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные теста"}), 400
        
        materials_csv = load_materials()
        
        area_names = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]
        
        scores_text = ""
        for i, name in enumerate(area_names):
            scores_text += f"{name}: {test_scores[i]}%\n"
        
        prompt = f"""

Ты — эксперт по компетенциям CSM 2.0.

### ВХОДНЫЕ ДАННЫЕ:
- Имя пользователя: {user_name}
- Почта пользователя: {user_email}
- Результаты теста: {scores_text}
- Список материалов (курсы, статьи, видео со ссылками):
{materials_csv}

### АЛГОРИТМ:
1. Найди области с результатом < 100%
2. Отсортируй их по возрастанию процента
3. Возьми первые 3 области (самые слабые)
4. Для КАЖДОЙ из этих 3 областей выбери из списка материалов:
   - 3 курса
   - 3 статьи
   - 3 видео

### ШАБЛОН ОТВЕТА (ТОЛЬКО ДЛЯ СЛАБЫХ ОБЛАСТЕЙ, НЕ БОЛЬШЕ 3):

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
... (то же самое: 3 курса, 3 статьи, 3 видео)

**[Название области 3]**
... (то же самое)

### ЖЁСТКИЕ ПРАВИЛА:
- НЕ ВЫДУМЫВАЙ ССЫЛКИ — ТОЛЬКО ИЗ СПИСКА
- НЕ ИСПОЛЬЗУЙ [ссылка] — ВСТАВЛЯЙ ПОЛНЫЙ URL
- ТОЛЬКО 3 ОБЛАСТИ, ТОЛЬКО 3 КУРСА, 3 СТАТЬИ, 3 ВИДЕО
- НИКАКИХ ЛИШНИХ СЛОВ И СОВЕТОВ
- ОТВЕТ ТОЛЬКО НА РУССКОМ
"""
        
        print("🤖 Отправляю запрос в GigaChat...")
        
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            model="GigaChat",
            timeout=120
        ) as giga:
            response = giga.chat(prompt)
            recommendations = response.choices[0].message.content
            print("✅ Рекомендации получены")
            
            return jsonify({
                "success": True,
                "recommendations": recommendations
            })
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
