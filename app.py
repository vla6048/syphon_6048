from quart import Quart, render_template, request, jsonify,redirect, url_for, send_file, flash, Blueprint
from quart_auth import QuartAuth, basic_auth_required
from sqlalchemy import select, and_
from docx import Document
from dotenv import load_dotenv
from num2words import num2words
from datetime import date, datetime
import os
import calendar
from io import BytesIO
import pandas as pd
import pdb
from db_manager import DatabaseManager

# Загрузка переменных окружения из .env файла
load_dotenv()


class MyApp:
    def __init__(self):
        # Создание экземпляра Quart
        self.app = Quart(__name__)
        QuartAuth(self.app)
        self.app.secret_key = os.urandom(24)
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

        bp = Blueprint('generate_protocols', __name__)
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

    def convert_to_currency_words(self, amount):
        hryvnia_part = int(amount)
        kopiyka_part = int(round((amount - hryvnia_part) * 100))
        hryvnia_words = num2words(hryvnia_part, lang='uk')
        kopiyka_words = num2words(kopiyka_part, lang='uk')
        return f"{hryvnia_words} гривень {kopiyka_words} копійок"

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

        @self.app.route('/llc_acts/<int:agreement_id>/generate_protocol', methods=['GET'])
        @basic_auth_required()
        async def generate_llc_protocol(agreement_id):
            # Получаем данные по договору и связанные данные для замены в шаблоне
            agreement_query = """
            SELECT la.id AS proto_num, la.agreement_name, la.agreement_date, 
                   lc.name AS llc_name, lc.in_persona, lc.address AS llc_address, lc.edrpou AS llc_edrpou, 
                   lc.iban AS llc_iban, lc.bank_account_detail AS bank_account_detail_llc, lc.inn AS llc_inn, lc.name_short AS llc_shortname,
                   ri.name AS ri_name, ri.inn AS ri_inn, ri.pidstava, ri.address AS ri_address, 
                   ri.iban AS ri_iban, ri.bank_account_detail AS bank_account_detail_ri, ri.name_short AS ri_shortname
            FROM credentials.llc_agreements AS la
            JOIN credentials.llc_credentials AS lc ON la.llc_id = lc.id
            JOIN credentials.ri_credentials AS ri ON la.ri_id = ri.id
            WHERE la.id = %s;
            """
            agreement_data = await self.local_db.execute_query(agreement_query, (agreement_id,))

            # Проверка, что данные по договору найдены
            if not agreement_data:
                return "Договор не найден", 404

            # Извлечение данных из результата
            agreement = agreement_data[0]
            for elements in agreement:
                print(f"{agreement.index(elements)}: {elements}")

            # Проверка ЕДРПОУ организации
            llc_edrpou = agreement[6]
            if llc_edrpou == "38736443":
                # Логика для случая, когда ЕДРПОУ == 38736443
                # (реализация будет позже)
                pass
            else:
                # Загружаем шаблон llc_proto.docx
                template_path = 'static/docs/llc_proto.docx'
                doc = Document(template_path)

                # Формируем номер протокола
                proto_num = f"{agreement[0]}_{agreement[2].strftime('%Y-%m-%d')}_{agreement[1]}"

                # Задаем значения для замены
                replacements = {
                    '@proto_num': proto_num,
                    '@agr_name': agreement[1],
                    '@agr_date': self.format_date(agreement[2])[0],
                    '@llc_name': agreement[3],
                    '@persona': agreement[4],
                    '@ri_name': agreement[11],
                    '@ri_inn': agreement[12],
                    '@pidstava': agreement[13],
                    '@llc_address': agreement[5],
                    '@llc_edrpou': llc_edrpou,
                    '@llc_iban': agreement[7],
                    '@bank_account_detail_llc': agreement[8],
                    '@llc_inn': agreement[9],
                    '@llc_shortname': agreement[10],
                    '@ri_address': agreement[14],
                    '@ri_iban': agreement[15],
                    '@bank_account_detail_ri': agreement[16],
                    '@ri_shortname': agreement[17]
                }

                # Замена текста в шаблоне
                self.replace_text_in_document(doc, replacements)
                self.replace_in_tables(doc.tables, replacements)

                # Сохранение документа
                doc_io = BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)

                # Формируем название файла
                file_name = f"{agreement[1]} Протокол.docx"

                # Отправка документа клиенту
                return await send_file(doc_io, as_attachment=True, attachment_filename=file_name)

        @self.app.route('/llc_acts/<int:agreement_id>/delete/<int:act_id>', methods=['POST'])
        @basic_auth_required()
        async def delete_act(agreement_id, act_id):
            # Удаление акта из базы данных
            delete_query = """
            UPDATE credentials.llc_acts SET act_state=0 
            where id = %s AND agreement = %s
            """
            await self.local_db.execute_query(delete_query, (act_id, agreement_id))

            # Перенаправление обратно на страницу актов
            return redirect(url_for('llc_acts', agreement_id=agreement_id))

        @self.app.route('/llc_acts/<int:agreement_id>', methods=['GET', 'POST'])
        @basic_auth_required()
        async def llc_acts(agreement_id):
            if request.method == 'POST':
                # Получение данных из формы
                act_date = (await request.form)['act_date']
                act_sum = (await request.form)['act_sum']

                # Вставка нового акта в базу данных
                insert_query = """
                INSERT INTO credentials.llc_acts (agreement, act_date, act_sum, act_state)
                VALUES (%s, %s, %s, 1);
                """
                await self.local_db.execute_query(insert_query, (agreement_id, act_date, act_sum))

                # Перезагрузка страницы после добавления акта
                return redirect(url_for('llc_acts', agreement_id=agreement_id))

            # Запрос данных по договору и связанных таблиц
            agreement_query = """
            SELECT la.agreement_name, lc.name AS organization_name, lc.edrpou, ri.name AS engineer_name
            FROM credentials.llc_agreements AS la
            JOIN credentials.llc_credentials AS lc ON la.llc_id = lc.id
            JOIN credentials.ri_credentials AS ri ON la.ri_id = ri.id
            WHERE la.id = %s;
            """
            agreement_data = await self.local_db.execute_query(agreement_query, (agreement_id,))

            # Проверка на случай отсутствия данных о договоре
            if not agreement_data:
                return "Договор не найден", 404

            # Извлечение данных о договоре из результата запроса
            agreement = {
                'agreement_name': agreement_data[0][0],
                'organization_name': agreement_data[0][1],
                'edrpou': agreement_data[0][2],
                'engineer_name': agreement_data[0][3]
            }

            # Запрос данных об актах, связанных с договором
            acts_query = """
            SELECT id, act_date, act_sum, act_state
            FROM credentials.llc_acts
            WHERE agreement = %s AND act_state = 1;
            """
            acts_data = await self.local_db.execute_query(acts_query, (agreement_id,))

            # Преобразование данных о актах в список словарей
            acts = [
                {
                    'id': act[0],
                    'act_date': act[1],
                    'act_sum': act[2],
                    'act_state': act[3]
                }
                for act in acts_data
            ]

            # Отображение страницы актов с информацией о договоре
            return await render_template('llc_acts.html', agreement=agreement, acts=acts, agreement_id=agreement_id)

        @self.app.route('/llc_agreements', methods=['GET'])
        @basic_auth_required()
        async def llc_agreements():
            # SQL-запрос для получения информации о всех договорах
            query = """
            SELECT la.id, la.agreement_name, la.agreement_date, llc.name AS llc_name, llc.canton AS canton, ri.name AS engineer_name
            FROM credentials.llc_agreements la
            JOIN credentials.llc_credentials llc ON la.llc_id = llc.id
            JOIN credentials.ri_credentials ri ON la.ri_id = ri.id;
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
                    'agreement_date': agreement[2],
                    'llc_name': agreement[3],
                    'canton': agreement[4],
                    'engineer_name': agreement[5],
                    'acts_by_year': {}
                }

                # Для каждого договора получаем данные по актам
                act_query = """
                SELECT YEAR(act_date) AS act_year, MONTH(act_date) AS act_month
                FROM credentials.llc_acts
                WHERE act_state = 1 AND agreement = %s
                ORDER BY act_year, act_month;
                """
                act_data = await self.local_db.execute_query(act_query, (agreement[0],))

                # Сортируем акты по годам
                for row in act_data:
                    year, month = row
                    if year not in agreement_dict['acts_by_year']:
                        agreement_dict['acts_by_year'][year] = []
                    agreement_dict['acts_by_year'][year].append(month)
                    all_years.add(year)

                agreements_list.append(agreement_dict)

            # Передаем все данные в шаблон, включая все уникальные годы
            return await render_template('llc_agreements.html', agreements=agreements_list, all_years=sorted(all_years))

        @self.app.route('/correct_agreement/<int:id>', methods=['POST'])
        @basic_auth_required()
        async def correct_agreement(id):
            try:
                # Получаем данные из таблицы protocols_missing_agreements по id
                missing_agreement_query = """
                    SELECT fop_inn, ri_inn, date_of_protocol, fop_change 
                    FROM credentials.protocols_missing_agreements 
                    WHERE id = %s;
                """
                missing_agreement = await self.local_db.execute_query(missing_agreement_query, (id,))

                if not missing_agreement:
                    await flash("Недостающий договор не найден.", "error")
                    return redirect(url_for('missing_agreements'))

                fop_inn, ri_inn, date_of_protocol, fop_change = missing_agreement[0]

                # Проверяем наличие договора в таблице agreements
                agreement_query = """
                    SELECT agreements.id 
                    FROM credentials.agreements AS agreements
                    JOIN credentials.fop_credentials AS fop ON agreements.master_id = fop.id
                    JOIN credentials.ri_credentials AS ri ON agreements.ri_id = ri.id
                    WHERE fop.inn = %s AND ri.inn = %s;
                """
                agreement_result = await self.local_db.execute_query(agreement_query, (fop_inn, ri_inn))
                agreement_id = agreement_result[0][0] if agreement_result else None

                if agreement_id:
                    # Вставляем данные в таблицу protocols_test
                    proto_sum_caps = self.convert_to_currency_words(fop_change)

                    insert_protocol_query = """
                        INSERT INTO credentials.protocols_test (agreement, proto_date, proto_sum, proto_sum_caps)
                        VALUES (%s, %s, %s, %s);
                    """
                    await self.local_db.execute_query(insert_protocol_query,
                                                      (agreement_id, date_of_protocol, fop_change, proto_sum_caps))

                    # Обновляем состояние в таблице protocols_missing_agreements
                    update_missing_agreement_query = """
                        UPDATE credentials.protocols_missing_agreements 
                        SET agreement_state = 1 
                        WHERE id = %s;
                    """
                    await self.local_db.execute_query(update_missing_agreement_query, (id,))

                    await flash("Договор успешно исправлен и протокол добавлен.", "success")
                    return redirect(url_for('missing_agreements'))
                else:
                    await flash("Договор не найден.", "error")
                    return redirect(url_for('missing_agreements'))

            except Exception as e:
                await flash(f"Ошибка при исправлении договора: {e}", "error")
                return redirect(url_for('missing_agreements'))

        @self.app.route('/missing_agreements', methods=['GET'])
        @basic_auth_required()
        async def missing_agreements():
            try:
                # Получаем записи с agreement_state = 0
                missing_agreements_query = """
                    SELECT id, clientId, description, fop_inn, fop_name, fop_in, fop_change, fop_expense, fop_out, 
                           type_agr, ri_inn, ri_name, date_of_protocol
                    FROM credentials.protocols_missing_agreements
                    WHERE agreement_state = 0;
                """
                agreements = await self.local_db.execute_query(missing_agreements_query)

                # Возвращаем HTML-страницу с данными
                return await render_template('missing_agreements.html', agreements=agreements)

            except Exception as e:
                await flash(f"Ошибка при загрузке недостающих договоров: {e}", "error")

        @self.app.route('/agreement_insertion', methods=['GET'])
        @basic_auth_required()
        async def agreement_insertion():
            # Загружаем всех инженеров для отображения в выпадающем списке
            engineers_query = "SELECT id, name FROM credentials.ri_credentials;"
            engineers = await self.local_db.execute_query(engineers_query)

            # Отправляем список инженеров на страницу
            return await render_template("agreement_insertion.html", engineers=engineers)

        @self.app.route('/search_masters', methods=['GET'])
        @basic_auth_required()
        async def search_masters():
            query = request.args.get("query", "")
            search_query = """
                SELECT id, name FROM credentials.fop_credentials 
                WHERE name LIKE %s LIMIT 10;
            """
            results = await self.local_db.execute_query(search_query, (f"%{query}%",))
            return jsonify([{"id": result[0], "name": result[1]} for result in results])

        @self.app.route('/submit_agreement', methods=['POST'])
        @basic_auth_required()
        async def submit_agreement():
            try:
                # Используем await перед request.form для корректного извлечения данных формы
                form_data = await request.form

                agreement_name = form_data.get('agreement_name')
                master_id = form_data.get('master_id')
                engineer_id = form_data.get('engineer')
                agreement_date = form_data.get('agreement_date')

                # Вставка данных в таблицу agreements
                insert_query = """
                    INSERT INTO credentials.agreements (agreement_name, master_id, ri_id, agreement_date)
                    VALUES (%s, %s, %s, %s);
                """
                await self.local_db.execute_query(insert_query,
                                                  (agreement_name, master_id, engineer_id, agreement_date))

                await flash("Новый договор успешно добавлен!", "success")
            except Exception as e:
                await flash(f"Ошибка при добавлении договора: {e}", "error")

            # Перенаправление на страницу добавления договора
            return redirect(url_for('agreement_insertion'))

        @self.app.route('/generate_protocols', methods=['POST'])
        @basic_auth_required()
        async def generate_protocols():
            try:
                # Получаем месяц и год из формы
                protocol_month = int((await request.form).get('protocol_month'))
                protocol_year = int((await request.form).get('protocol_year'))

                # Запрос только для записей с указанным месяцем и годом
                soft_estimates_query = """
                    SELECT id, clientId, description, fop_inn, fop_name, fop_in, fop_change, 
                           fop_expense, fop_out, type_agr, ri_inn, ri_name, date_of_protocol
                    FROM credentials.soft_estimates
                    WHERE MONTH(date_of_protocol) = %s AND YEAR(date_of_protocol) = %s;
                """

                # Выполняем запрос
                soft_estimates = await self.local_db.execute_query(soft_estimates_query,
                                                                   (protocol_month, protocol_year))
                print("Количество записей для генерации протоколов:", len(soft_estimates))

                if not soft_estimates:
                    await flash("Записей для указанного месяца и года не найдено.", "info")
                    return redirect(url_for('estimates_upload'))

                for record in soft_estimates:
                    (id, clientId, description, fop_inn, fop_name, fop_in, fop_change,
                     fop_expense, fop_out, type_agr, ri_inn, ri_name, date_of_protocol) = record

                    # Поиск соответствующего договора
                    agreement_query = """
                        SELECT agreements.id 
                        FROM credentials.agreements AS agreements
                        JOIN credentials.fop_credentials AS fop ON agreements.master_id = fop.id
                        JOIN credentials.ri_credentials AS ri ON agreements.ri_id = ri.id
                        WHERE fop.inn = %s AND ri.inn = %s;
                    """
                    agreement_result = await self.local_db.execute_query(agreement_query, (fop_inn, ri_inn))
                    agreement = agreement_result[0][0] if agreement_result else None
                    print("Договор найден:", agreement)

                    if agreement:
                        # Договор найден, вставляем данные в таблицу protocols
                        proto_sum_caps = self.convert_to_currency_words(fop_change)

                        insert_protocol_query = """
                            INSERT INTO credentials.protocols_test (agreement, proto_date, proto_sum, proto_sum_caps)
                            VALUES (%s, %s, %s, %s);
                        """
                        await self.local_db.execute_query(insert_protocol_query,
                                                          (agreement, date_of_protocol, fop_change, proto_sum_caps))
                        print(f"Протокол добавлен для договора {agreement} на сумму {fop_change}")
                    else:
                        # Договор не найден, копируем все данные в protocols_missing_agreements
                        insert_missing_agreement_query = """
                            INSERT INTO credentials.protocols_missing_agreements 
                            (clientId, description, fop_inn, fop_name, fop_in, fop_change, fop_expense, fop_out, 
                             type_agr, ri_inn, ri_name, date_of_protocol, agreement_state)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """
                        await self.local_db.execute_query(insert_missing_agreement_query,
                                                          (clientId, description, fop_inn, fop_name, fop_in, fop_change,
                                                           fop_expense, fop_out, type_agr, ri_inn, ri_name,
                                                           date_of_protocol, False))
                        print(
                            f"Протокол не добавлен, данные сохранены в таблицу protocols_missing_agreements для клиента {clientId}")

                await flash("Протоколы успешно сгенерированы и сохранены.", "success")

            except Exception as e:
                print(f"Ошибка при генерации протоколов: {e}")
                await flash(f"Ошибка при генерации протоколов: {e}", "error")

            # Перенаправляем пользователя на нужную страницу
            return redirect(url_for('estimates_upload'))

        @self.app.route('/estimates_upload', methods=['GET', 'POST'])
        @basic_auth_required()
        async def estimates_upload():
            # Обработка POST запроса для загрузки данных
            if request.method == 'POST':
                # Получение данных из формы с использованием await
                date_str = (await request.form).get('date')
                file = (await request.files).get('file')

                if not date_str or not file:
                    await flash("Пожалуйста, укажите дату и выберите файл.")
                    return redirect(url_for('estimates_upload'))

                # Преобразуем дату в нужный формат
                try:
                    date_of_protocol = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    await flash("Некорректный формат даты.")
                    return redirect(url_for('estimates_upload'))

                # Чтение данных из XLSX
                df = pd.read_excel(file)
                insert_query = """
                    INSERT INTO credentials.soft_estimates (
                        clientId, description, fop_inn, fop_name, fop_in,
                        fop_change, fop_expense, fop_out, type_agr, 
                        ri_inn, ri_name, date_of_protocol
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                # Обработка данных и вставка в базу
                records = [
                    (
                        int(row['ClientId']), str(row['Description']), int(row['OKPO']), str(row['Name']),
                        float(row['In']), float(row['Charge']), float(row['Expense']),
                        float(row['Out']), str(row['Type']), int(row['ContractOKPO']),
                        str(row['ContractName']), date_of_protocol
                    )
                    for _, row in df.iterrows()
                ]

                try:
                    # Выполнение вставки
                    await self.local_db.ensure_connection()
                    for record in records:
                        await self.local_db.execute_query(insert_query, record)
                    await flash("Данные успешно загружены.")
                except Exception as e:
                    await flash(f"Ошибка при загрузке данных: {e}")
                    print(f"Ошибка при загрузке данных: {e}")
                finally:
                    await self.local_db.close()

                return redirect(url_for('estimates_upload'))

            # Обработка GET запроса для отображения формы и уникальных дат
            select_dates_query = "SELECT DISTINCT date_of_protocol FROM credentials.soft_estimates"
            try:
                await self.local_db.ensure_connection()
                dates = await self.local_db.execute_query(select_dates_query)
            except Exception as e:
                print(f"Ошибка при получении дат: {e}")
                dates = []

            return await render_template('estimates_upload.html', dates=dates)


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
                # proto_sum_caps = (await request.form)['proto_sum_caps']
                proto_sum_caps = self.convert_to_currency_words(float(proto_sum))

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
            email = form_data.get('email')

            # Выбор таблицы в зависимости от позиции
            if position == 'Мастер':
                table = 'credentials.fop_credentials'
            elif position == 'Инженер':
                table = 'credentials.ri_credentials'
            else:
                return jsonify({"error": "Неверная позиция"}), 400

            # SQL-запрос для вставки данных
            insert_query = f"""
            INSERT INTO {table} (name, inn, pidstava, address, iban, bank_account_detail, name_short, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Вставка данных в базу
            try:
                await self.local_db.execute_query(insert_query,
                                                  (name, inn, pidstava, address, iban, bank_account_detail, name_short, email))
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