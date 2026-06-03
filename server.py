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

GIGACHAT_CREDENTIALS = "MDE5ZDI0NDctNjhmMy03MjU5LTk1M2MtZTYwNzVjYjllNmI1OmU0ZjgyNjdmLTBlYjYtNDhjNC04MTJiLWFiNTJiYTlmM2VmMA=="

# URL твоего Google Apps Script
MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

def load_materials():
    """Загружает материалы из Google Apps Script (JSON)"""
    try:
        response = requests.get(MATERIALS_URL)
        data = response.json()
        
        materials_text = ""
        for area, items in data.items():
            materials_text += f"\n### {area}\n"
            for item in items:
                materials_text += f"{item['name']} | {item['url']}\n"
        
        return materials_text
    except Exception as e:
        print(f"❌ Ошибка загрузки материалов: {e}")
        return ""

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        print(f"📨 Получен запрос от: {data.get('userName')}")

        user_name = data.get('userName')
        user_email = data.get('userEmail')
        test_scores = data.get('testScores', [])

        if not test_scores or len(test_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные теста"}), 400

        area_names = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]

        scores_text = ""
        for i, name in enumerate(area_names):
            scores_text += f"{name}: {test_scores[i]}%\n"

        # Загружаем материалы
        materials_text = load_materials()

        data_text = f"""
- Имя пользователя: {user_name}
- Почта пользователя: {user_email}
- Результаты теста (Тест):
{scores_text}
"""

        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

### Данные пользователя:
{data_text}

### Доступные материалы:
{materials_text}

### ИНСТРУКЦИЯ (ВЫПОЛНИ ПОШАГОВО, НЕ ПРОПУСКАЙ):

ШАГ 1. Проверь, выполняется ли УСЛОВИЕ А:
- Посмотри на значения "Тест" для всех 8 областей.
- Если КАЖДАЯ область имеет 100%, переходи к ШАГУ 2.
- Если хотя бы одна область имеет НЕ 100%, переходи к ШАГУ 3.

ШАГ 2. (УСЛОВИЕ А выполняется)
Напиши ТОЧНО следующий текст, ничего не добавляя:
🎉 Поздравляем, {user_name}! Вы показали максимальные результаты по всем компетенциям CSM 2.0. Вы находитесь на экспертном уровне. 
Рекомендуем: 
* Выступать в роли наставника для коллег
* Делиться опытом
* Участвовать в развитии программы CSM 2.0
Если ищете направления для развития - обратитесь к руководителю для формирования ИПР.
И ОСТАНОВИСЬ. НЕ ПИШИ БОЛЬШЕ НИЧЕГО.

ШАГ 3. (УСЛОВИЕ А НЕ выполняется)
3.1. Найди области, где тест НЕ РАВЕН 100%.
3.2. Отсортируй эти области по возрастанию процентов (самые низкие первые).
3.3. Выбери ТОЛЬКО 3 области с самыми низкими процентами.
3.4. Для каждой выбранной области напиши по три курса, по три статьи, по три видео:

**Название области**
📊 Результаты теста: Y%
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

### ЗАПРЕЩЕНО:
- Не пиши области, которые не выбрал
- Не добавляй "Нет в наличии", если материалы есть
- Не пиши "вы показали отличные результаты", если есть области с тестом не 100%
- Не пиши никаких советов, заключений или "что делать дальше"
- Используй ТОЛЬКО ссылки из списка материалов
- Ответ только на русском языке

### ПОВТОРИ ПРАВИЛА (ПРОВЕРЬ СЕБЯ):
1. Я выбрал ТОЛЬКО области с тестом МЕНЕЕ 100%
2. Я отсортировал их по возрастанию процентов
3. Я взял НЕ БОЛЬШЕ 3 областей
4. Я использовал ТОЛЬКО ссылки из списка материалов
5. Я НЕ добавлял советов и "что делать дальше"
6. Я НЕ писал области, которые не подходят под условия
7. Я добавил курсы и ссылки на них
8. Я добавил статьи и ссылки на них
9. Я добавил видео и ссылки на них
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
