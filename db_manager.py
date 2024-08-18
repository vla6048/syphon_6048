import aiomysql
import asyncio

class DatabaseManager:
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
            self.connection = await aiomysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db
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

    async def execute_query(self, query, params=None):
        """
        Выполнение SQL запроса и возврат результата.
        """
        if not self.connection:
            await self.connect()
        if self.connection:
            async with self.connection.cursor() as cursor:
                try:
                    await cursor.execute(query, params)
                    result = await cursor.fetchall()
                    await self.connection.commit()
                    return result
                except aiomysql.Error as e:
                    print(f"Ошибка выполнения запроса: {e}")
                    return None
