#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from gigachat import GigaChat
import os

app = Flask(__name__)
CORS(app)

GIGACHAT_CREDENTIALS = "MDE5ZDI0NDctNjhmMy03MjU5LTk1M2MtZTYwNzVjYjllNmI1OmU0ZjgyNjdmLTBlYjYtNDhjNC04MTJiLWFiNTJiYTlmM2VmMA=="

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
        
        area_names = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]
        
        scores_text = ""
        for i, name in enumerate(area_names):
            scores_text += f"{name}: {test_scores[i]}%\n"
        
        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

Данные пользователя:
Имя: {user_name}
Почта: {user_email}

Результаты теста:
{scores_text}

Проанализируй результаты. Найди области с результатом менее 70%. 
Дай персонализированные рекомендации по развитию слабых областей.
Будь конкретным и полезным. Ответ на русском языке.
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
