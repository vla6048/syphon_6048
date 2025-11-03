import aiomysql
from aiomysql import Error as AiomysqlError, OperationalError, InterfaceError


class DatabaseManager:
    # ⚠️ Удален pool_recycle, так как aiomysql.connect не использует его напрямую.
    # Для управления циклом жизни соединений лучше использовать aiomysql.create_pool.
    def __init__(self, host, user, password, db):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.connection = None

    async def connect(self):
        """
        Подключение к базе данных.
        """
        try:
            # 💡 Используем aiomysql.connect
            self.connection = await aiomysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                # 💡 autocommit=True подходит для простого приложения, но
                # для безопасности данных явные транзакции лучше. Оставим True,
                # но предупредим о необходимости явного commit для INSERT/UPDATE/DELETE.
                autocommit=True
            )
            print(f"Успешное подключение к базе данных {self.db} на {self.host}.")
        except AiomysqlError as e:
            print(f"Ошибка подключения к базе данных: {e}")
            self.connection = None  # Убедимся, что connection сброшено

    async def close(self):
        """
        Закрытие соединения с базой данных.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None
            print(f"Соединение с базой данных {self.db} закрыто.")

    async def ensure_connection(self):
        """
        Убедитесь, что соединение активно и не закрыто, иначе переподключитесь.
        """
        # 🟢 ИСПРАВЛЕНИЕ: Проверяем, существует ли соединение И закрыто ли оно.
        # aiomysql.Connection.closed - это атрибут (булево значение), а не метод.
        is_closed = self.connection is None or self.connection.closed
        if is_closed:
            await self.connect()
        # ⚠️ Дополнительная проверка на активность (ping) требует явного try/except
        # и может быть ресурсозатратной. Для простого приложения достаточно проверки .closed.

    async def execute_insert(self, query, params=None):
        """
        Выполнение SQL-запроса INSERT и возврат ID вставленной записи.
        """
        await self.ensure_connection()
        if self.connection:
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(query, params)
                    # 💡 autocommit=True, но явный commit не помешает, если мы не уверены.
                    # Для INSERT можно полагаться на autocommit.
                    return cursor.lastrowid
                except (OperationalError, InterfaceError) as e:
                    # Повторная попытка после разрыва соединения
                    print(f"Потеря соединения (INSERT): {e}. Повторная попытка...")
                    await self.connect()
                    return await self.execute_insert(query, params)  # Рекурсивный вызов
                except AiomysqlError as e:
                    print(f"Ошибка выполнения INSERT-запроса: {e}")
                    return None

    async def execute_query(self, query, params=None):
        """
        Выполнение SQL запроса и возврат результата с проверкой состояния соединения.
        """
        await self.ensure_connection()
        if self.connection:
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(query, params)

                    # 💡 Для запросов, которые меняют данные (не SELECT), делаем commit.
                    # Проверяем, является ли запрос SELECT. Это простая эвристика.
                    if not query.strip().upper().startswith("SELECT"):
                        await self.connection.commit()

                    result = await cursor.fetchall()
                    return result
                except (OperationalError, InterfaceError) as e:
                    # Повторная попытка после разрыва соединения
                    print(f"Потеря соединения: {e}. Повторная попытка...")
                    await self.connect()
                    return await self.execute_query(query, params)  # Рекурсивный вызов
                except AiomysqlError as e:
                    print(f"Ошибка выполнения запроса: {e}")
                    return None