from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "OK", "message": "Сервер CSM 2.0 работает!"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": "2026-05-25 13:00:00"})

@app.route('/recommend', methods=['POST', 'OPTIONS'])
def recommend():
    print("✅ Получен запрос на /recommend")
    try:
        data = request.get_json()
        print(f"📨 Данные: {data}")
        return jsonify({
            "success": True,
            "message": "Тестовый ответ от сервера",
            "received": data
        })
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск тестового сервера CSM 2.0...")
    app.run(host='0.0.0.0', port=10000)
