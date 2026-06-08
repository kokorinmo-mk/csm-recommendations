#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests

app = Flask(__name__)
CORS(app)

# Ваш API-ключ OpenRouter (обязательно должен быть действительным!)
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
if not QWEN_API_KEY:
    QWEN_API_KEY = "ВАШ_API_КЛЮЧ_OPENROUTER"

QWEN_BASE_URL = "https://openrouter.ai/api/v1"

# --- СПИСОК БЕСПЛАТНЫХ МОДЕЛЕЙ ---
FREE_MODELS = [
    "nvidia/nemotron-3-super",
    "google/gemma-4-31b-it:free",
    "minimax/minimax-m2.5",
    "qwen/qwen3.6-plus-preview:free",
    "baidu/cobuddy",
    "nvidia/nemotron-nano-9b-v2",
    "openrouter/free",
]

client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

MATERIALS_URL = "https://script.google.com/macros/s/AKfycbzOlrBj4ZY5iqStx3gUiF3Duecu0W8X26BfFsvNWJ6CoRLU7Hf2B7jDHnLVX4qE9m9w/exec"

# Названия областей в правильном порядке
AREA_NAMES = ["Осознание", "Стратегия", "Реинжиниринг", "Проектирование", "Внедрение", "Методология", "Отраслевые", "Soft skills"]


def load_materials():
    """Загружает материалы из Google Apps Script (JSON)"""
    try:
        response = requests.get(MATERIALS_URL)
        data = response.json()
        result = []
        for area, items in data.items():
            result.append(f"\n### {area}")
            for item in items[:5]:
                result.append(f"{item['name']} | {item['url']}")
        print(f"✅ Загружено материалов: {len(result)}")
        return "\n".join(result)
    except Exception as e:
        print(f"❌ Ошибка загрузки материалов: {e}")
        return ""


def parse_scores(scores_list, is_test=True):
    """
    Преобразует список оценок в текстовый формат.
    Для теста: [100, 85, 45, ...] -> "Осознание: 100%\nСтратегия: 85%\n..."
    Для самооценки: [7.5, 8.0, 4.5, ...] -> "Осознание: 7.5/10\n..."
    """
    result = []
    for i, name in enumerate(AREA_NAMES):
        if i < len(scores_list):
            value = scores_list[i]
            if is_test:
                result.append(f"{name}: {value}%")
            else:
                result.append(f"{name}: {value}/10")
    return "\n".join(result)


def extract_first_name(full_name):
    """Извлекает имя из полного имени (фамилия + имя)"""
    if not full_name:
        return "Пользователь"
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[1]  # Берём вторую часть (после фамилии)
    return parts[0]  # Если только имя


def get_recommendations_from_model(model_id, prompt):
    """Пытается получить ответ от указанной модели."""
    print(f"   Пробую модель: {model_id}...")
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
            timeout=90
        )
        recommendations = response.choices[0].message.content
        print(f"   ✅ Модель {model_id} ответила успешно.")
        return recommendations
    except Exception as e:
        print(f"   ❌ Модель {model_id} не отвечает: {e}")
        return None


@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Сервер CSM 2.0 работает с несколькими бесплатными LLM"})


@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        print(f"📨 Запрос от: {data.get('userName')}")

        user_name = data.get('userName')
        user_email = data.get('userEmail')
        test_scores = data.get('testScores', [])
        self_scores = data.get('selfScores', [])  # <-- ДОБАВЛЕНО: получаем самооценку

        # Валидация данных
        if not test_scores or len(test_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные теста"}), 400

        if not self_scores or len(self_scores) != 8:
            return jsonify({"success": False, "error": "Некорректные данные самооценки"}), 400

        # Преобразуем оценки в текстовый формат
        scores_text = parse_scores(test_scores, is_test=True)
        self_scores_text = parse_scores(self_scores, is_test=False)

        # Извлекаем только имя
        first_name = extract_first_name(user_name)

        # Загружаем материалы
        materials_text = load_materials()

        # Формируем промпт
        prompt = f"""
Ты — эксперт по компетенциям CSM 2.0.

### ВХОДНЫЕ ДАННЫЕ:
- Имя пользователя: {first_name}
- Почта пользователя: {user_email}
- Результаты теста:
{scores_text}
- Результаты самооценки:
{self_scores_text}
- Материалы для рекомендаций:
{materials_text}

### АЛГОРИТМ:
1. Найди области с результатом теста < 100%
2. Отсортируй их по возрастанию (худшие первые)
3. Возьми все найденные области (но не более 3)
4. Для каждой области выбери 3 курса, 3 статьи, 3 видео из файла с материалами
5. Для каждой слабой области рассчитай расхождение между тестом и самооценкой:
   - Самооценка в % = (self_score / 10) × 100
   - Расхождение = |Тест - Самооценка_в_%|
   - Тип расхождения:
     * Расхождение ≤ 10% → «Адекватная оценка»
     * Расхождение > 10% и тест < самооценка → «Завышенная самооценка»
     * Расхождение > 10% и тест > самооценка → «Заниженная самооценка»

### ОБРАБОТКА КРАЙНИХ СЛУЧАЕВ:
- Если найдено 0 областей с результатом < 100% → вывести поздравительное сообщение (без рекомендаций и без совета)
- Если найдено 1 или 2 области → вывести рекомендации только для них
- Если найдено 3 и более области → вывести первые 3 (самые слабые)

### ВЫХОДНЫЕ ДАННЫЕ:

**Если есть области с результатом < 100%:**

{first_name}, ваши результаты теста CSM 2.0:

**[Название области 1]**
📊 Результат теста: X%
📝 Самооценка: X/10
⚖️ Расхождение: X% (тип расхождения)
📚 Рекомендуем изучить:
**[Курсы]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)
**[Статьи]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)
**[Видео]**
• [Название](ссылка)
• [Название](ссылка)
• [Название](ссылка)

**[Название области 2]** (если есть)
... (то же самое)

**[Название области 3]** (если есть)
... (то же самое)

**📊 Анализ самооценки:**
(общий вывод по всем слабым областям)

В самом конце добавь совет в зависимости от типа расхождения:
- Если есть завышенная самооценка → 💡 Совет: Обратите внимание на зоны роста. Результаты теста показывают, что эти навыки требуют усиления. Доверьтесь объективной оценке и начните с рекомендованных материалов.
- Если есть заниженная самооценка → 💡 Совет: Ваш результат лучше, чем вы думаете! Не обесценивайте свои навыки. Рекомендуемые материалы помогут закрепить успех и выйти на 100%.
- Если все расхождения ≤ 10% → 💡 Совет: Регулярно возвращайтесь к этим материалам и отслеживайте свой прогресс. Маленькие шаги каждый день приводят к большим результатам!

---

**Если нет областей с результатом < 100%:**

{first_name}, ваши результаты теста CSM 2.0:

🎉 Поздравляем! Вы показали максимальные результаты по всем компетенциям CSM 2.0. Вы находитесь на экспертном уровне.

Рекомендации:
• Выступать в роли наставника для коллег
• Делиться опытом
• Участвовать в развитии программы CSM 2.0

💡 Совет: Если хотите уточнить направления для дальнейшего развития, рекомендуем обратиться к вашему руководителю для формирования индивидуальной программы развития (ИПР).

Так держать!

### ПРАВИЛА:
- При обращении к пользователю используй только имя (уже передано как {first_name})
- Только ссылки из файла (если есть рекомендации)
- Формат ссылок: [Название](URL)
- Без лишних советов (кроме указанного выше)
- Только русский язык
"""

        if not QWEN_API_KEY:
            return jsonify({"success": False, "error": "QWEN_API_KEY не настроен"}), 500

        print("🤖 Отправляю запросы к моделям...")
        recommendations = None
        for model in FREE_MODELS:
            recommendations = get_recommendations_from_model(model, prompt)
            if recommendations:
                break

        if not recommendations:
            print("❌ Ни одна модель не смогла ответить.")
            return jsonify({"success": False, "error": "Сервис временно недоступен. Попробуйте позже."}), 503

        print("✅ Рекомендации успешно получены.")
        return jsonify({"success": True, "recommendations": recommendations})

    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
