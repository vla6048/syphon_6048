from quart import Quart, render_template, request, jsonify
from dotenv import load_dotenv
import os
import asyncio
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

from db_manager import DatabaseManager

# Загрузка переменных окружения из .env файла
load_dotenv()

class MyApp:
    def __init__(self):
        # Создание экземпляра Quart
        self.app = Quart(__name__)

        # Настройка подключения к базам данных
        self.local_db = DatabaseManager(
            host=os.getenv('MYSQL_HOST_LOCAL'),
            user=os.getenv('MYSQL_USER_LOCAL'),
            password=os.getenv('MYSQL_PASSWORD_LOCAL'),
            db=os.getenv('MYSQL_DB_LOCAL')
        )

        self.remote_db = DatabaseManager(
            host=os.getenv('MYSQL_HOST_REMOTE'),
            user=os.getenv('MYSQL_USER_REMOTE'),
            password=os.getenv('MYSQL_PASSWORD_REMOTE'),
            db=os.getenv('MYSQL_DB_REMOTE')
        )

        # Настройка маршрутов
        self.setup_routes()

    def setup_routes(self):

        @self.app.route('/')
        @self.app.route('/index')
        async def index():
            devices_query = "SELECT id, description FROM devices WHERE device_type = 'power_control';"
            devices = await self.local_db.execute_query(devices_query)
            return await render_template('index.html', devices=devices)

        @self.app.route('/generate-report', methods=['GET'])
        async def generate_report():
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            selected_device = request.args.get('device')

            if selected_device == 'all':
                devices_query = "SELECT id, description FROM devices WHERE device_type = 'power_control';"
                devices = await self.local_db.execute_query(devices_query)
            else:
                devices = [(selected_device, '')]

            plots = []
            table_data = []

            for device_id, description in devices:
                relations_query = """
                SELECT d1.ip_address AS power_ip, d2.ip_address AS generator_ip, l.start, l.stop, l.downtime
                FROM ntst_pinger_hosts_log AS l
                JOIN devices AS d1 ON l.ip = d1.ip_address
                JOIN device_relations AS r ON d1.id = r.power_control_id
                JOIN devices AS d2 ON r.generator_control_id = d2.id
                WHERE d1.id = %s AND l.start BETWEEN %s AND %s;
                """
                power_data = await self.local_db.execute_query(relations_query, (device_id, start_date, end_date))

                if not power_data:
                    continue

                power_downtime_total = 0
                generator_downtime_total = 0
                generator_uptime_during_power_downtime = 0

                plt.figure(figsize=(10, 4))
                for power_ip, generator_ip, start, stop, downtime in power_data:
                    plt.hlines(y=1, xmin=start, xmax=stop, colors='red' if downtime > 0 else 'green', linewidth=5)

                    power_downtime_total += downtime

                    generator_query = """
                    SELECT start, stop, downtime
                    FROM ntst_pinger_hosts_log
                    WHERE ip = %s AND start BETWEEN %s AND %s;
                    """
                    generator_data = await self.local_db.execute_query(generator_query, (generator_ip, start, stop))

                    for gen_start, gen_stop, gen_downtime in generator_data:
                        plt.hlines(y=2, xmin=gen_start, xmax=gen_stop, colors='red' if gen_downtime > 0 else 'green', linewidth=5)

                        generator_downtime_total += gen_downtime

                        if downtime > 0 and gen_downtime == 0:
                            generator_uptime_during_power_downtime += (min(stop, gen_stop) - max(start, gen_start)).total_seconds()

                plt.yticks([1, 2], ['Power Control', 'Generator Control'])
                plt.xlabel('Time')
                plt.ylabel('Device Status')
                plt.title(f'Device {description} - Power and Generator Control')
                plt.tight_layout()

                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                plot_url = base64.b64encode(img.getvalue()).decode()
                plt.close()

                plots.append({
                    'description': description,
                    'plot_url': f"data:image/png;base64,{plot_url}"
                })

                table_data.append({
                    'description': description,
                    'power_downtime_hours': round(power_downtime_total / 3600, 2),
                    'generator_downtime_hours': round(generator_downtime_total / 3600, 2),
                    'generator_uptime_during_power_downtime_hours': round(generator_uptime_during_power_downtime / 3600, 2)
                })

            return await render_template('report.html', plots=plots, table_data=table_data)
        # @self.app.route('/')
        # async def index():
        #     return jsonify({"message": "Добро пожаловать в Quart приложение!"})

        @self.app.route('/fetch-and-store', methods=['GET'])
        async def fetch_and_store():
            """
            Проверяет доступность удаленной базы данных, получает список IP-адресов из локальной базы,
            извлекает данные из удаленной базы для этих IP-адресов и сохраняет их в локальной базе данных.
            Возвращает количество новых записей, которые были добавлены.
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
                await self.remote_db.close()
                return jsonify({"error": "Не удалось получить IP-адреса из локальной базы данных."}), 500

            # Формируем список IP-адресов для SQL запроса
            ip_list = [ip[0] for ip in ip_addresses]
            formatted_ips = ','.join(f"'{ip}'" for ip in ip_list)

            # Получение всех ID из локальной базы данных
            local_ids_query = "SELECT id FROM ntst_pinger_hosts_log;"
            local_ids = await self.local_db.execute_query(local_ids_query)
            local_ids_list = [str(id[0]) for id in local_ids]
            formatted_ids = ','.join(local_ids_list)

            # Запрос данных из удаленной базы данных для полученных IP-адресов
            remote_query = f"""
            SELECT hl.ip, hl.start, hl.stop, hl.id
            FROM pinger.`HostLogs` AS hl
            WHERE hl.ip IN ({formatted_ips})
            AND hl.id NOT IN ({formatted_ids});
            """
            remote_data = await self.remote_db.execute_query(remote_query)

            # Закрытие соединения с удаленной базой данных
            await self.remote_db.close()

            if not remote_data:
                return jsonify({
                    "message": "Данные успешно получены, но новых данных нет.",
                    "new_data_count": 0
                }), 200

            # Подсчет количества новых данных
            new_data_count = len(remote_data)

            # Вставка данных в локальную базу данных
            insert_query = """
            INSERT IGNORE INTO ntst_pinger_hosts_log (id, ip, start, stop, downtime)
            VALUES (%s, %s, %s, %s, TIMESTAMPDIFF(SECOND, %s, %s))
            """

            for record in remote_data:
                await self.local_db.execute_query(
                    insert_query,
                    (record[3], record[0], record[1], record[2], record[1], record[2])
                )

            return jsonify({
                "message": "Данные успешно получены и сохранены в локальной базе данных.",
                "new_data_count": new_data_count
            })

    def run(self):
        # Запуск приложения на Quart
        self.app.run(debug=True)

if __name__ == '__main__':
    # Создание экземпляра приложения
    my_app = MyApp()

    # Запуск приложения
    my_app.run()
