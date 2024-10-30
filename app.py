from quart import Quart, render_template, request, jsonify,redirect, url_for, send_file
from quart_auth import QuartAuth, basic_auth_required
from docx import Document
from dotenv import load_dotenv
from datetime import date
import os
import calendar
from io import BytesIO
import pdb
from db_manager import DatabaseManager

# Загрузка переменных окружения из .env файла
load_dotenv()


class MyApp:
    def __init__(self):
        # Создание экземпляра Quart
        self.app = Quart(__name__)
        QuartAuth(self.app)
        self.app.secret_key = os.getenv('SECRET_KEY')
        self.app.config["QUART_AUTH_BASIC_USERNAME"] = os.getenv('BUSERNAME')
        self.app.config["QUART_AUTH_BASIC_PASSWORD"] = os.getenv('BPASSWD')

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

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

    #функции для роутов
    def replace_text_in_document(self, doc, replacements):
        # Заміна у всіх параграфах документа
        for paragraph in doc.paragraphs:
            for key, value in replacements.items():
                if key in paragraph.text:
                    paragraph.text = paragraph.text.replace(key, str(value))

    def replace_in_tables(self, tables, replacements):
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in replacements.items():
                        if key in cell.text:
                            cell.text = cell.text.replace(key, str(value))
                    # Перевірка на вкладені таблиці та рекурсивний виклик
                    if cell.tables:
                        self.replace_in_tables(cell.tables, replacements)

    def format_date(self, date):
        months_ukr = {
            1: 'січня', 2: 'лютого', 3: 'березня', 4: 'квітня', 5: 'травня', 6: 'червня',
            7: 'липня', 8: 'серпня', 9: 'вересня', 10: 'жовтня', 11: 'листопада', 12: 'грудня'
        }
        day = date.strftime("%d")
        month = months_ukr[date.month]
        year = date.strftime("%Y")
        return f"{day} {month} {year} року", month, year, day

    def amount_to_time(self, protocol_amount):
        work_hours = protocol_amount/1000
        hours = int(work_hours)
        minutes = int((work_hours-hours)*60)
        return f"{hours} годин {minutes} хвилин"

    def setup_routes(self):



        @self.app.route('/protocols/<int:agreement_id>/generate_docx/<int:protocol_id>', methods=['GET'])
        @basic_auth_required()
        async def generate_docx(agreement_id,protocol_id):
            # Получаем информацию по договору и протоколу
            agreement_query = """
            SELECT a.agreement_name, a.agreement_date, f.name AS fop_name, f.inn AS inn_fop, f.pidstava AS pidstava_fop, 
                   f.address AS fop_address, f.iban AS fop_iban, f.bank_account_detail AS bank_account_detail_fop, f.name_short AS fop_name_short,
                   r.name AS ri_name, r.inn AS inn_ri, r.pidstava AS pidstava_ri, r.address AS ri_address, r.iban AS ri_iban, r.bank_account_detail AS bank_account_detail_ri, r.name_short AS ri_name_short
            FROM credentials.agreements AS a
            JOIN credentials.fop_credentials AS f ON a.master_id = f.id
            JOIN credentials.ri_credentials AS r ON a.ri_id = r.id
            WHERE a.id = %s;
            """
            agreement_data = await self.local_db.execute_query(agreement_query, (agreement_id,))
            agreement = agreement_data[0]  # Мы получаем первый элемент, чтобы передать данные как строку, а не кортеж.

            protocol_query = """
                        SELECT proto_date, proto_sum, proto_sum_caps
                        FROM credentials.protocols
                        WHERE agreement = %s and id = %s;
                        """
            protocol_data = await self.local_db.execute_query(protocol_query, (agreement_id, protocol_id))
            protocol = protocol_data[0]  # Тоже получаем первый элемент из протоколов

            if not agreement_data or not protocol_data:
                return "Договор или протокол не найден", 404

            # Преобразуем данные и форматируем дату
            agreement_date_str, month_ukr_name, year, _ = self.format_date(agreement[1])
            proto_date_str, proto_month_ukr_name, proto_year, last_day_of_the_month  = self.format_date(protocol[0])
            template_month = calendar.monthrange(int(protocol[0].strftime("%Y")), int(protocol[0].month))
            last_day_of_the_month = str(template_month[1])

            # Загрузка шаблона
            template_path = 'static/docs/M-RI_protocol.docx'
            doc = Document(template_path)

            # Замена маркеров
            replacements = {
                '@agr_num': agreement[0],
                '@agr_date': agreement_date_str,
                '@proto_date': proto_date_str,
                '@fop_name': agreement[2],
                '@inn_fop': agreement[3],
                '@pidstava_fop': agreement[4],
                '@ri_name': agreement[9],
                '@inn_ri': agreement[10],
                '@pidstava_ri': agreement[11],
                '@month_ukr_name': proto_month_ukr_name,
                '@year': proto_year,
                '@last_day_of_the_month': last_day_of_the_month,
                '@agr_sum': f"{protocol[1]:,.2f}",
                '@agrsum_handwriting_sample': protocol[2],
                '@fop_address': agreement[5],
                '@fop_iban': agreement[6],
                '@bank_account_detail_fop': agreement[7],
                '@fopname_short': agreement[8],
                '@ri_address': agreement[12],
                '@ri_iban': agreement[13],
                '@bank_account_detail_ri': agreement[14],
                '@riname_short': agreement[15]
            }


            # Замена текста в шаблоне
            self.replace_text_in_document(doc, replacements)
            self.replace_in_tables(doc.tables, replacements)


            # Сохранение документа в память
            doc_io = BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)

            # Формируем название файла
            file_name = f"{agreement[0]}_протокол_{proto_month_ukr_name}_{proto_year}.docx"

            # Отправка документа клиенту
            return await send_file(doc_io, as_attachment=True, attachment_filename=file_name)

        @self.app.route('/protocols/<int:agreement_id>/generate_act_docx/<int:protocol_id>', methods=['GET'])
        @basic_auth_required()
        async def generate_act_docx(agreement_id,protocol_id):
            # Получаем информацию по договору и протоколу
            agreement_query = """
            SELECT a.agreement_name, a.agreement_date, f.name AS fop_name, f.inn AS inn_fop, f.pidstava AS pidstava_fop, 
                   f.address AS fop_address, f.iban AS fop_iban, f.bank_account_detail AS bank_account_detail_fop, f.name_short AS fop_name_short,
                   r.name AS ri_name, r.inn AS inn_ri, r.pidstava AS pidstava_ri, r.address AS ri_address, r.iban AS ri_iban, r.bank_account_detail AS bank_account_detail_ri, r.name_short AS ri_name_short
            FROM credentials.agreements AS a
            JOIN credentials.fop_credentials AS f ON a.master_id = f.id
            JOIN credentials.ri_credentials AS r ON a.ri_id = r.id
            WHERE a.id = %s;
            """
            agreement_data = await self.local_db.execute_query(agreement_query, (agreement_id,))
            agreement = agreement_data[0]  # Мы получаем первый элемент, чтобы передать данные как строку, а не кортеж.

            protocol_query = """
            SELECT proto_date, proto_sum, proto_sum_caps
            FROM credentials.protocols
            WHERE agreement = %s and id = %s;
            """
            protocol_data = await self.local_db.execute_query(protocol_query, (agreement_id,protocol_id))
            protocol = protocol_data[0]  # Тоже получаем первый элемент из протоколов

            if not agreement_data or not protocol_data:
                return "Договор или протокол не найден", 404

            # Преобразуем данные и форматируем дату
            agreement_date_str, month_ukr_name, year, _ = self.format_date(agreement[1])
            proto_date_str, proto_month_ukr_name, proto_year, last_day_of_the_month = self.format_date(protocol[0])
            template_month = calendar.monthrange(int(protocol[0].strftime("%Y")), int(protocol[0].month))
            last_day_of_the_month = str(template_month[1])

            # Загрузка шаблона
            template_path = 'static/docs/M-RI_act.docx'
            doc = Document(template_path)

            # Замена маркеров
            replacements = {
                '@agr_num': agreement[0],
                '@agr_date': agreement_date_str,
                '@proto_date': proto_date_str,
                '@fop_name': agreement[2],
                '@inn_fop': agreement[3],
                '@pidstava_fop': agreement[4],
                '@ri_name': agreement[9],
                '@inn_ri': agreement[10],
                '@pidstava_ri': agreement[11],
                '@month_ukr_name': proto_month_ukr_name,
                '@year': proto_year,
                '@last_day_of_the_month': last_day_of_the_month,
                '@agr_sum': f"{protocol[1]:,.2f}",
                '@agrsum_handwriting_sample': protocol[2],
                '@fop_address': agreement[5],
                '@fop_iban': agreement[6],
                '@bank_account_detail_fop': agreement[7],
                '@fopname_short': agreement[8],
                '@ri_address': agreement[12],
                '@ri_iban': agreement[13],
                '@bank_account_detail_ri': agreement[14],
                '@riname_short': agreement[15],
                '@today': self.format_date(date.today())[0],
                '@act_nubmer': f'{protocol_id}/{agreement[0]}',
                '@act_hours': self.amount_to_time(float(protocol[1]))
            }

            # Замена текста в шаблоне
            print(self.amount_to_time(float(protocol[1])))
            self.replace_text_in_document(doc, replacements)
            self.replace_in_tables(doc.tables, replacements)


            # Сохранение документа в память
            doc_io = BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)

            # Формируем название файла
            file_name = f"{agreement[0]}_акт_{proto_month_ukr_name}_{proto_year}.docx"

            # Отправка документа клиенту
            return await send_file(doc_io, as_attachment=True, attachment_filename=file_name)

        @self.app.route('/protocols/<int:agreement_id>', methods=['GET', 'POST'])
        @basic_auth_required()
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

                # Перезагрузка страницы после добавления данных
                return redirect(url_for('protocols', agreement_id=agreement_id))

            # Запрос существующих протоколов с proto_state = 1
            protocols_query = """
            SELECT p.proto_date, p.proto_sum, p.proto_sum_caps, p.proto_state, p.id
            FROM credentials.protocols AS p
            WHERE p.agreement = %s AND p.proto_state = 1;
            """
            protocols_data = await self.local_db.execute_query(protocols_query, (agreement_id,))

            # Проверка на пустой результат запроса
            if protocols_data is None:
                protocols_data = []

            # Преобразование кортежей в словари
            protocols = [
                {
                    'proto_date': protocol[0],
                    'proto_sum': protocol[1],
                    'proto_sum_caps': protocol[2],
                    'proto_state': protocol[3],
                    'id': protocol[4]
                }
                for protocol in protocols_data
            ]

            # Запрос данных о договоре
            agreement_query = """
            SELECT a.agreement_name, f.name AS master_name, r.name AS ri_name, a.id
            FROM credentials.agreements AS a
            JOIN credentials.fop_credentials AS f ON a.master_id = f.id
            JOIN credentials.ri_credentials AS r ON a.ri_id = r.id
            WHERE a.id = %s;
            """
            agreement = await self.local_db.execute_query(agreement_query, (agreement_id,))

            if not agreement:
                return "Договор не найден", 404  # Или можно сделать редирект на другую страницу

            # Отображение страницы протоколов
            return await render_template('protocols.html', protocols=protocols, agreement=agreement[0],
                                         agreement_id=agreement_id)

        @self.app.route('/protocols/<int:agreement_id>/delete/<int:protocol_id>', methods=['POST'])
        @basic_auth_required()
        async def delete_protocol(agreement_id, protocol_id):
            update_query = """
            UPDATE credentials.protocols 
            SET proto_state = 0 
            WHERE id = %s
            """
            await self.local_db.execute_query(update_query, (protocol_id,))

            # Перезагрузка страницы после удаления
            return redirect(url_for('protocols', agreement_id=agreement_id))

        @self.app.route('/agreements', methods=['GET'])
        @basic_auth_required()
        async def agreements():
            # SQL-запрос для получения информации о всех договорах
            query = """
            SELECT a.id, a.agreement_name, fc.name AS master_name, rc.name AS engineer_name
            FROM credentials.agreements a
            JOIN credentials.fop_credentials fc ON a.master_id = fc.id
            JOIN credentials.ri_credentials rc ON a.ri_id = rc.id;
            """

            # Выполняем запрос и получаем данные по договорам
            agreements_data = await self.local_db.execute_query(query)

            all_years = set()
            agreements_list = []

            # Преобразуем каждый кортеж в словарь
            for agreement in agreements_data:
                agreement_dict = {
                    'id': agreement[0],
                    'agreement_name': agreement[1],
                    'master_name': agreement[2],
                    'engineer_name': agreement[3],
                    'protocols_by_year': {}
                }

                # Для каждого договора получаем данные по протоколам
                proto_query = """
                SELECT YEAR(proto_date) AS proto_year, MONTH(proto_date) AS proto_month
                FROM credentials.protocols
                WHERE proto_state = 1 AND agreement = %s
                ORDER BY proto_year, proto_month;
                """
                proto_data = await self.local_db.execute_query(proto_query, (agreement[0],))

                # Сортируем протоколы по годам
                for row in proto_data:
                    year, month = row
                    if year not in agreement_dict['protocols_by_year']:
                        agreement_dict['protocols_by_year'][year] = []
                    agreement_dict['protocols_by_year'][year].append(month)
                    all_years.add(year)

                agreements_list.append(agreement_dict)

            # Передаем все данные в шаблон, включая все уникальные годы
            return await render_template('agreements.html', agreements=agreements_list, all_years=sorted(all_years))

        @self.app.route('/fop-form')
        @basic_auth_required()
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
        @basic_auth_required()
        async def index():
            return await render_template('index.html')

        @self.app.route('/device_report')
        @basic_auth_required()
        async def device_report():
            devices_query = "SELECT id, description FROM devices WHERE device_type = 'power_control';"
            devices = await self.local_db.execute_query(devices_query)
            return await render_template('dev-report.html', devices=devices)

        @self.app.route('/generate-report', methods=['GET'])
        @basic_auth_required()
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
            INSERT IGNORE INTO dbsyphon.ntst_pinger_hosts_log (id, ip, start, stop, downtime)
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

app = MyApp()
asgi_app = app.app



if __name__ == '__main__':
    asgi_app.run()