from quart import Quart, render_template, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from dotenv import load_dotenv
import os
import asyncio

from db_manager import DatabaseManager

# Загрузка переменных окружения из .env файла
load_dotenv()


# Класс пользователя
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# Создание экземпляра Quart
app = Quart(__name__)
app.secret_key = 'your_secret_key'

# Настройка LoginManager для Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Настройка базы данных (вынесено за класс MyApp)
local_db = DatabaseManager(
    host=os.getenv('MYSQL_HOST_LOCAL'),
    user=os.getenv('MYSQL_USER_LOCAL'),
    password=os.getenv('MYSQL_PASSWORD_LOCAL'),
    db=os.getenv('MYSQL_DB_LOCAL')
)

remote_db = DatabaseManager(
    host=os.getenv('MYSQL_HOST_REMOTE'),
    user=os.getenv('MYSQL_USER_REMOTE'),
    password=os.getenv('MYSQL_PASSWORD_REMOTE'),
    db=os.getenv('MYSQL_DB_REMOTE')
)


# Функция для загрузки пользователя по ID (асинхронно)
@login_manager.user_loader
async def load_user(user_id):
    # Здесь можно реализовать загрузку пользователя из базы данных
    # Например:
    query = "SELECT id, username, password FROM users WHERE id = %s"
    user_data = await local_db.execute_query(query, (user_id,))

    if user_data:
        return User(user_data[0][0], user_data[0][1], user_data[0][2])
    return None


# Настройка маршрутов
@app.route('/')
@app.route('/index')
async def index():
    devices_query = "SELECT id, description FROM devices WHERE device_type = 'power_control';"
    devices = await local_db.execute_query(devices_query)
    return await render_template('dev-report.html', devices=devices)


# Маршрут для логина
@app.route('/login', methods=['POST'])
async def login():
    form = await request.form
    username = form.get('username')
    password = form.get('password')

    # Поиск пользователя в базе данных
    query = "SELECT id, username, password FROM users WHERE username = %s AND password = %s"
    user_data = await local_db.execute_query(query, (username, password))

    if user_data:
        user = User(user_data[0][0], user_data[0][1], user_data[0][2])
        login_user(user)
        return jsonify({"message": "Logged in successfully!"})

    return jsonify({"error": "Invalid credentials!"}), 401


# Маршрут для выхода
@app.route('/logout')
@login_required
async def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully!"})


# Пример защищенного маршрута
@app.route('/protected')
@login_required
async def protected():
    return jsonify({"message": f"Logged in as: {current_user.username}"})


if __name__ == '__main__':
    app.run(debug=True)
