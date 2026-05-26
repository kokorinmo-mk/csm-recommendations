#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"
SAVE_TO_SHEETS_URL = "https://script.google.com/macros/s/AKfycbw23tamPZcP3VTYP6nHIJacjGChp6XryrRXGPY_ogU3ww1n5AiEqa2G0V5P0SNZO4KGkw/exec"

# Resend API ключ (должен быть в переменных окружения Render)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# ============================================================
# ЗАГРУЗКА МАТЕРИАЛОВ
# ============================================================
def load_materials_from_sheets():
    try:
        response = requests.get(MATERIALS_URL, timeout=30)
        if response.status_code == 200:
            materials = response.json()
            print(f"✅ Загружено {len(materials)} областей")
            return materials
        else:
            print(f"❌ Ошибка загрузки материалов: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Ошибка при загрузке материалов: {e}")
        return {}

# ============================================================
# СОХРАНЕНИЕ РЕКОМЕНДАЦИЙ В GOOGLE SHEETS И ОТПРАВКА EMAIL
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
# ОТПРАВКА EMAIL ЧЕРЕЗ RESEND
# ============================================================
def send_email(to_email, user_name, recommendations):
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY не настроен")
        return False
    
    try:
        first_name = user_name.split(" ")[0] if user_name else "Пользователь"
        
        # Преобразуем переносы строк в <br>
        html_content = recommendations.replace("\n", "<br>")
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "CSM 2.0 <noreply@resend.dev>",
                "to": to_email,
                "subject": "📊 Результаты оценки компетенций CSM 2.0",
                "html": f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2>Здравствуйте, {first_name}!</h2>
    <p>Вы прошли самооценку и тест CSM 2.0.</p>
    <div style="background: #e8f4f8; padding: 15px; border-radius: 8px;">
        {html_content}
    </div>
    <hr>
    <p style="color: #666; font-size: 12px;">© CSM 2.0</p>
</div>
"""
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Письмо отправлено на {to_email}")
            return True
        else:
            print(f"❌ Ошибка Resend: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

# ============================================================
# ГЕНЕРАЦИЯ РЕКОМЕНДАЦИЙ (БЕЗ GigaChat)
# ============================================================
def generate_recommendations(user_name, test_scores, materials):
    """Генерирует рекомендации на основе процентов теста"""
    
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
    
    # Собираем области с процентом теста
    areas_with_scores = []
    for i, name in enumerate(area_names):
        score = test_scores[i] if i < len(test_scores) else 0
        areas_with_scores.append({"name": name, "score": score})
    
    # Сортируем по проценту (самые низкие первые)
    areas_with_scores.sort(key=lambda x: x["score"])
    
    # Берём ТОП-3 области с ошибками (<100%)
    low_areas = [a for a in areas_with_scores if a["score"] < 100][:3]
    
    # Если нет областей с ошибками — значит всё 100%
    if not low_areas:
        return f"""
🎉 Поздравляем, {user_name}! Вы показали максимальные результаты по всем компетенциям CSM 2.0. Вы находитесь на экспертном уровне. 
Рекомендуем: 
* Выступать в роли наставника для коллег
* Делиться опытом
* Участвовать в развитии программы CSM 2.0
Если ищете направления для развития - обратитесь к руководителю для формирования ИПР.
"""
    
    # Формируем рекомендации для каждой области
    result = ""
    for area in low_areas:
        area_name = area["name"]
        score = area["score"]
        
        result += f"**{area_name}**\n"
        result += f"📊 Результаты теста: {score}%\n"
        result += "📚 Рекомендуем изучить:\n"
        
        # Ищем материалы для этой области
        area_materials = materials.get(area_name, [])
        
        # Курсы
        courses = [item for item in area_materials if item['name'].startswith('[Курс]')][:3]
        result += "**[Курсы]**\n"
        if courses:
            for c in courses:
                result += f"• [{c['name']}]({c['url']})\n"
        else:
            result += "• Нет в наличии\n"
        
        # Статьи
        articles = [item for item in area_materials if item['name'].startswith('[Статья]')][:3]
        result += "**[Статьи]**\n"
        if articles:
            for a in articles:
                result += f"• [{a['name']}]({a['url']})\n"
        else:
            result += "• Нет в наличии\n"
        
        # Видео
        videos = [item for item in area_materials if item['name'].startswith('[Видео]')][:3]
        result += "**[Видео]**\n"
        if videos:
            for v in videos:
                result += f"• [{v['name']}]({v['url']})\n"
        else:
            result += "• Нет в наличии\n"
        
        result += "\n"
    
    return result

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
        
        # Получаем данные
        self_ratings = data.get('selfRatings', [])
        test_scores = data.get('testScores', [])
        
        print(f"📊 Самооценка: {self_ratings}")
        print(f"📊 Тест: {test_scores}")
        
        # Загружаем материалы
        materials = load_materials_from_sheets()
        
        # Генерируем рекомендации (без GigaChat)
        recommendations = generate_recommendations(user_name, test_scores, materials)
        print(f"💡 Рекомендации сгенерированы")
        
        # Сохраняем в Google Sheets
        saved = save_recommendations_to_sheets(user_name, user_email, recommendations)
        
        # Отправляем email
        email_sent = send_email(user_email, user_name, recommendations)
        
        if saved and email_sent:
            return jsonify({"success": True, "message": "Рекомендации сохранены и отправлены"})
        else:
            return jsonify({"success": False, "message": "Частичная ошибка"}), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=5000, debug=True)
