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

# URL таблицы со ссылками
MATERIALS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQgRTJT7A9uBDdCNuqobPEI9-PRHqv2o2zcIJtx0wi4iFy4BGwSte5-kSZMhp8zJiI-MpMKZ80T6BKP/pub?output=csv"

def load_materials():
    """Загружает материалы из Google Sheets"""
    try:
        response = requests.get(MATERIALS_URL)
        response.encoding = 'utf-8'
        lines = response.text.split('\n')
        materials_text = ""
        for line in lines[1:]:  # пропускаем заголовок
            if line.strip():
                materials_text += line + "\n"
        return materials_text
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
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
        
        # Загружаем материалы
        materials_csv = load_materials()
        
        area_names = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]
        
        scores_text = ""
        for i, name in enumerate(area_names):
            scores_text += f"{name}: {test_scores[i]}%\n"
        
        # ТВОЙ ОРИГИНАЛЬНЫЙ ПРОМПТ + ДОБАВЛЕНА ТАБЛИЦА
        prompt = f"""

Ты — эксперт по компетенциям CSM 2.0.

### ВХОДНЫЕ ДАННЫЕ:
- Имя пользователя: {user_name}
- Почта пользователя: {user_email}
- Результаты теста: {scores_text} (содержит 8 областей и процент по каждой)
- Список материалов (курсы, статьи, видео со ссылками):
{materials_csv}

### ЧТО ТЫ ДЕЛАЕШЬ ВНУТРИ СЕБЯ (алгоритм):
1. Проверяешь: каждая ли из 8 областей имеет 100%?
   - Если ДА → переходишь к п.6
   - Если НЕТ → продолжаешь
2. Отбираешь области, где процент < 100%
3. Сортируешь их по возрастанию процента (от худшего к лучшему)
4. Берёшь первые 3 области из отсортированного списка
5. Для каждой из 3 областей подбираешь из списка материалов:
   - 3 курса (с названиями и ссылками)
   - 3 статьи (с названиями и ссылками)
   - 3 видео (с названиями и ссылками)
6. Формируешь выходные данные по шаблону (см. ниже)

### ВЫХОДНЫЕ ДАННЫЕ (что выводишь пользователю):

**Если все 8 областей = 100%:**
{user_name}, поздравляем! Вы набрали 100% по всем компетенциям CSM 2.0. Отличный результат!

**Если есть области с <100% (выводишь ТОЛЬКО 3 самые слабые области):**

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
... (то же самое: 3 курса, 3 статьи, 3 видео)

**[Название области 3]**
📊 Результат: X%
📚 Рекомендуем изучить:
... (то же самое)

### ЖЁСТКИЕ ОГРАНИЧЕНИЯ:
- Не выводишь никаких областей, кроме трёх самых слабых
- Не выводишь советы, выводы, «что делать дальше»
- Не выводишь свой внутренний ход мыслей
- Не добавляешь фраз вроде «нет материалов» — используешь только те ссылки, что есть в списке
- Ответ строго на русском языке
"""        
        print("🤖 Отправляю запрос в GigaChat...")
        
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            model="GigaChat",
            timeout=60
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
