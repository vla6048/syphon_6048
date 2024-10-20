from quart import Quart, render_template, request, jsonify,redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
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

        @self.app.route('/protocols/<int:agreement_id>', methods=['GET', 'POST'])
        async def protocols(agreement_id):
            if request.method == 'POST':
                # Получение данных из формы
                proto_date = (await request.form)['proto_date']
                proto_sum = (await request.form)['proto_sum']
                proto_sum_caps = (await request.form)['proto_sum_caps']

                # Вставка данных протокола в базу данных
                insert_query = """
                INSERT INTO credentials.protocols (agreement, proto_date, proto_sum, proto_sum_caps)
                VALUES (%s, %s, %s, %s);
                """
                await self.local_db.execute_query(insert_query, (agreement_id, proto_date, proto_sum, proto_sum_caps))

                # Перезагрузка страницы после добавления данных без редиректа
                return redirect(url_for('protocols', agreement_id=agreement_id))

            # Запрос существующих протоколов по договору
            protocols_query = """
            SELECT p.proto_date, p.proto_sum, p.proto_sum_caps
            FROM credentials.protocols AS p
            WHERE p.agreement = %s;
            """
            protocols = await self.local_db.execute_query(protocols_query, (agreement_id,))

            # Запрос данных о договоре
            agreement_query = """
            SELECT a.agreement_name, f.name AS master_name, r.name AS ri_name
            FROM credentials.agreements AS a
            JOIN credentials.fop_credentials AS f ON a.master_id = f.id
            JOIN credentials.ri_credentials AS r ON a.ri_id = r.id
            WHERE a.id = %s;
            """
            agreement = await self.local_db.execute_query(agreement_query, (agreement_id,))

            # Проверка на наличие договора
            if not agreement:
                return "Договор не найден", 404  # Или можно сделать редирект на другую страницу

            return await render_template('protocols.html', protocols=protocols, agreement=agreement[0])

        @self.app.route('/agreements', methods=['GET'])
        async def agreements():
            # SQL-запрос для получения информации о всех договорах
            query = """
            SELECT a.id, a.agreement_name, fc.name AS master_name, rc.name AS engineer_name
            FROM credentials.agreements a
            JOIN credentials.fop_credentials fc ON a.master_id = fc.id
            JOIN credentials.ri_credentials rc ON a.ri_id = rc.id;
            """

            # Выполняем запрос и получаем данные
            agreements_data = await self.local_db.execute_query(query)

            # Передаем данные в шаблон
            return await render_template('agreements.html', agreements=agreements_data)

        @self.app.route('/fop-form')
        async def fop_form():
            # Отображение формы для внесения информации о ФОП
            return await render_template('fop_form.html')

        @self.app.route('/submit-fop', methods=['POST'])
        async def submit_fop():
            # Используем await для получения данных формы
            form_data = await request.form

            # Получаем значения полей из формы
            position = form_data.get('position')
            name = form_data.get('name')
            inn = form_data.get('inn')
            pidstava = form_data.get('pidstava')
            address = form_data.get('address')
            iban = form_data.get('iban')
            bank_account_detail = form_data.get('bank_account_detail')
            name_short = form_data.get('name_short')

            # Выбор таблицы в зависимости от позиции
            if position == 'Мастер':
                table = 'credentials.fop_credentials'
            elif position == 'Инженер':
                table = 'credentials.ri_credentials'
            else:
                return jsonify({"error": "Неверная позиция"}), 400

            # SQL-запрос для вставки данных
            insert_query = f"""
            INSERT INTO {table} (name, inn, pidstava, address, iban, bank_account_detail, name_short)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            # Вставка данных в базу
            try:
                await self.local_db.execute_query(insert_query,
                                                  (name, inn, pidstava, address, iban, bank_account_detail, name_short))
                return jsonify({"message": "Данные успешно добавлены"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

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

            # Получаем все связки устройств из таблицы device_relations
            relations_query = """
            SELECT d1.id AS power_id, d1.description AS power_desc, d2.id AS generator_id, d2.description AS generator_desc
            FROM device_relations AS r
            JOIN devices AS d1 ON r.power_control_id = d1.id
            JOIN devices AS d2 ON r.generator_control_id = d2.id;
            """
            relations_data = await self.local_db.execute_query(relations_query)

            table_data = []

            for relation in relations_data:
                power_id, power_desc, generator_id, generator_desc = relation

                # Запрос данных для power_control
                power_downtime_query = """
                SELECT SUM(downtime)
                FROM ntst_pinger_hosts_log
                WHERE ip = (SELECT ip_address FROM devices WHERE id = %s)
                AND start BETWEEN %s AND %s;
                """
                power_downtime_data = await self.local_db.execute_query(power_downtime_query,
                                                                        (power_id, start_date, end_date))
                total_power_downtime = power_downtime_data[0][0] if power_downtime_data[0][0] else 0

                # Запрос данных для generator_control
                generator_downtime_query = """
                SELECT SUM(downtime)
                FROM ntst_pinger_hosts_log
                WHERE ip = (SELECT ip_address FROM devices WHERE id = %s)
                AND start BETWEEN %s AND %s;
                """
                generator_downtime_data = await self.local_db.execute_query(generator_downtime_query,
                                                                            (generator_id, start_date, end_date))
                total_generator_downtime = generator_downtime_data[0][0] if generator_downtime_data[0][0] else 0

                # Рассчет uptime генератора во время простоя power_control
                generator_uptime_during_power_downtime = max(0,
                                                             (total_power_downtime - total_generator_downtime) / 3600)

                # Добавление строки в таблицу с округлением до 2 знаков после запятой
                table_data.append({
                    'description': f"{power_desc}",
                    'power_downtime_hours': round(total_power_downtime / 3600, 2),  # в часах
                    'generator_downtime_hours': round(total_generator_downtime / 3600, 2),  # в часах
                    'generator_uptime_during_power_downtime_hours': round(generator_uptime_during_power_downtime, 2)
                })

            # Дополнительный запрос для суммарного времени простоя всех устройств power_control
            total_downtime_query = """
            SELECT d.description, SUM(l.downtime) / 3600 AS total_downtime_hours
            FROM devices AS d
            LEFT JOIN ntst_pinger_hosts_log AS l ON d.ip_address = l.ip
            WHERE d.device_type = 'power_control'
            AND l.start BETWEEN %s AND %s
            GROUP BY d.description;
            """
            total_downtime_data = await self.local_db.execute_query(total_downtime_query, (start_date, end_date))

            # Передача данных в шаблон
            return await render_template('report.html',
                                         table_data=table_data,
                                         total_downtime_data=total_downtime_data,
                                         start_date=start_date,
                                         end_date=end_date
                                         )

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
            FROM pinger.HostLogs AS hl
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