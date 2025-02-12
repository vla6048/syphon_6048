import aiomysql
import pymysql

class DatabaseManager:
    def __init__(self, host, user, password, db, pool_recycle=3600):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.pool_recycle = pool_recycle
        self.connection = None

    async def execute_insert(self, query, params=None):
        """
        Выполнение SQL-запроса INSERT и возврат ID вставленной записи.
        """
        await self.ensure_connection()
        if self.connection:
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(query, params)
                    await self.connection.commit()
                    return cursor.lastrowid  # Возвращаем ID вставленной записи
                except aiomysql.Error as e:
                    print(f"Ошибка выполнения INSERT-запроса: {e}")
                    return None

    async def connect(self):
        """
        Подключение к базе данных с использованием параметра pool_recycle.
        """
        try:
            self.connection = await aiomysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                autocommit=True  # это обеспечит автоматическое выполнение commit
            )
            print(f"Успешное подключение к базе данных {self.db} на {self.host}.")
        except aiomysql.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")

    async def close(self):
        """
        Закрытие соединения с базой данных.
        """
        if self.connection:
            self.connection.close()
            print(f"Соединение с базой данных {self.db} закрыто.")

    async def ensure_connection(self):
        """
        Убедитесь, что соединение активно, иначе переподключитесь.
        """
        try:
            if not self.connection or self.connection.close:
                await self.connect()
        except pymysql.err.InterfaceError:
            await self.connect()

    async def execute_query(self, query, params=None):
        """
        Выполнение SQL запроса и возврат результата с проверкой состояния соединения.
        """
        await self.ensure_connection()  # Проверяем соединение перед выполнением запроса
        if self.connection:
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(query, params)
                    result = await cursor.fetchall()
                    return result
                except aiomysql.Error as e:
                    print(f"Ошибка выполнения запроса: {e}")
                    return None
