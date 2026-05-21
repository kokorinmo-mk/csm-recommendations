#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from gigachat import GigaChat
import json
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
CORS(app)

# ============================================================
# НАСТРОЙКИ - читаем из переменных окружения Render
# ============================================================
GIGACHAT_CREDENTIALS = {
    "credentials": os.environ.get("GIGACHAT_CREDENTIALS", ""),
    "scope": "GIGACHAT_API_PERS",
    "verify_ssl_certs": False,
    "model": "GigaChat"
}

# ============================================================
# ФУНКЦИЯ ДЛЯ ОТПРАВКИ EMAIL ЧЕРЕЗ SENDGRID
# ============================================================
def send_email(to_email, user_name, recommendations):
    """Отправляет письмо через Resend API"""
    try:
        resend_api_key = os.environ.get("RESEND_API_KEY")
        
        if not resend_api_key:
            print("❌ RESEND_API_KEY не найден в переменных окружения")
            return False
        
        import requests
        
        first_name = user_name.split()[0] if user_name else "Пользователь"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f9fafb; border-radius: 12px;">
            <div style="background: #1f6e8c; padding: 20px; border-radius: 12px 12px 0 0; color: white; text-align: center;">
                <h1 style="margin: 0;">CSM 2.0</h1>
                <p>Результаты оценки компетенций</p>
            </div>
            <div style="background: white; padding: 20px; border-radius: 0 0 12px 12px;">
                <h2 style="color: #1f6e8c;">Здравствуйте, {first_name}!</h2>
                <p>Вы недавно прошли самооценку и тест по компетенциям <strong>CSM 2.0</strong>.</p>
                <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #1f6e8c; margin-top: 0;">📋 Рекомендации:</h3>
                    <div style="line-height: 1.6;">
                        {recommendations.replace(chr(10), '<br>')}
                    </div>
                </div>
                <hr style="margin: 20px 0;">
                <p style="color: #6b7280; font-size: 12px; text-align: center;">
                    Это автоматическое сообщение, пожалуйста, не отвечайте на него.<br>
                    © CSM 2.0 — Программа развития компетенций
                </p>
            </div>
        </div>
        """
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "noreply@resend.dev",  # Бесплатный отправитель Resend
                "to": to_email,
                "subject": "📊 Результаты оценки компетенций CSM 2.0",
                "html": html_content
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Письмо отправлено на {to_email} через Resend")
            return True
        else:
            print(f"❌ Ошибка Resend: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")
        return False

# ============================================================
# ФУНКЦИЯ ДЛЯ РАБОТЫ С GigaChat
# ============================================================
def get_gigachat_recommendations(user_name, self_ratings, test_scores):
    """Отправляет запрос к GigaChat и возвращает рекомендации"""
    
    # Формируем промпт
    prompt = f"""
Ты — эксперт по компетенциям CSM 2.0. Пользователь прошёл самооценку и тест.

Данные пользователя:
- ФИО: {user_name}

Результаты самооценки (оценки от 1 до 10, где 1 — совсем не владею, 10 — эксперт):
{json.dumps(self_ratings, ensure_ascii=False, indent=2)}

Результаты теста (проценты правильных ответов):
{json.dumps(test_scores, ensure_ascii=False, indent=2)}

Сформируй ТОП-3 области компетенций, которые требуют развития.
Для каждой области напиши в формате:
N. [Название области] (Почему? На что обратить внимание? Какие материалы изучить?)

Будь конкретным, дружелюбным. Ответ только на русском языке.
"""

    try:
        # Подключаемся к GigaChat с увеличенным таймаутом
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
1. Область 1. Осознание (Рекомендуется изучить современные тренды: AI, Big Data, IoT, Cloud. Обратите внимание на архитектуру цифровой трансформации.)

2. Область 2. Стратегия (Развивайте стратегическое мышление, изучите Business Model Canvas и карту гипотез.)

3. Область 6. Общесистемные компетенции (Освойте инструменты CSM и генеративные модели вроде GigaChat для повышения эффективности.)
"""

# ============================================================
# ЭНДПОИНТЫ СЕРВЕРА
# ============================================================
@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "OK", "message": "Сервер CSM 2.0 работает!"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": str(__import__('datetime').datetime.now())})

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        print(f"📨 Получен запрос от: {data.get('userName')}")
        
        user_name = data.get('userName')
        user_email = data.get('userEmail')
        self_ratings = data.get('selfRatings', [])
        test_scores = data.get('testScores', [])
        
        # Получаем рекомендации от GigaChat
        recommendations = get_gigachat_recommendations(user_name, self_ratings, test_scores)
        print(f"💡 Рекомендации получены")
        
        # Отправляем email через SendGrid
        email_sent = send_email(user_email, user_name, recommendations)
        
        if email_sent:
            return jsonify({
                "success": True,
                "message": "Рекомендации отправлены на email"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Не удалось отправить email"
            }), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=5000, debug=True)
