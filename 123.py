# app.py

from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import asyncio

from db_manager import DatabaseManager

# Загрузка переменных окружения из .env файла
load_dotenv()

class MyApp:
    def __init__(self):
        self.app = Flask(__name__)

        # Настройка подключения к базам данных
        self.local_db = DatabaseManager(
            host=os.getenv('LOCAL_DB_HOST'),
            user=os.getenv('LOCAL_DB_USER'),
            password=os.getenv('LOCAL_DB_PASSWORD'),
            db=os.getenv('LOCAL_DB_NAME')
        )

        self.remote_db = DatabaseManager(
            host=os.getenv('REMOTE_DB_HOST'),
            user=os.getenv('REMOTE_DB_USER'),
            password=os.getenv('REMOTE_DB_PASSWORD'),
            db=os.getenv('REMOTE_DB_NAME')
        )

        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/fetch-and-store', methods=['GET'])
        async def fetch_and_store():
            """
            Проверяет доступность удаленной базы данных, получает список IP-адресов из локальной базы,
            и извлекает данные из удаленной базы для этих IP-адресов.
            """
            # Проверка доступности удаленной базы данных
            try:
                await self.remote_db.connect()
            except Exception as e:
                return jsonify({"error": "Удаленная база данных недоступна, попробуйте позже."}), 503

            # Получение списка IP-адресов из локальной базы данных
            ip_query = "SELECT ip_address FROM dbsyphon.devices;"
            ip_addresses = await self.local_db.execute_query(ip_query)

            if not ip_addresses:
                return jsonify({"error": "Не удалось получить IP-адреса из локальной базы данных."}), 500

            # Формируем список IP-адресов для SQL запроса
            ip_list = [ip[0] for ip in ip_addresses]
            formatted_ips = ','.join(f"'{ip}'" for ip in ip_list)

            # Запрос данных из удаленной базы данных для полученных IP-адресов
            remote_query = f"""
            SELECT hl.ip, hl.start, hl.stop, hl.id
            FROM pinger.`HostLogs` AS hl
            WHERE hl.ip IN ({formatted_ips});
            """
            remote_data = await self.remote_db.execute_query(remote_query)

            if not remote_data:
                return jsonify({"error": "Не удалось получить данные из удаленной базы данных."}), 500

            # Здесь вы можете сохранить полученные данные в локальную базу или вернуть их как ответ
            return jsonify({"message": "Данные успешно получены и обработаны.", "data": remote_data})

    def run(self):
        self.app.run(debug=True)

if __name__ == '__main__':
    my_app = MyApp()
    my_app.run()
