import aiomysql
from aiomysql import Error as AiomysqlError, OperationalError, InterfaceError


def _query_returns_rows(query):
    return query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"))


class DatabaseManager:
    def __init__(self, host, user, password, db=None, minsize=1, maxsize=10):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.minsize = minsize
        self.maxsize = maxsize
        self.pool = None

    async def connect(self):
        """
        Создание пула подключений к базе данных.
        """
        if self.pool and not self.pool.closed:
            return

        try:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                minsize=self.minsize,
                maxsize=self.maxsize,
                autocommit=True,
                pool_recycle=3600,
            )
            print(f"Успешно создан пул подключений к базе данных {self.db} на {self.host}.")
        except AiomysqlError as e:
            print(f"Ошибка подключения к базе данных: {e}")
            self.pool = None

    async def close(self):
        """
        Закрытие пула подключений к базе данных.
        """
        if self.pool and not self.pool.closed:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            print(f"Пул подключений к базе данных {self.db} закрыт.")

    async def ensure_connection(self):
        """
        Убедитесь, что пул подключений активен, иначе создайте его.
        """
        if self.pool is None or self.pool.closed:
            await self.connect()

    async def _execute(self, query, params=None, return_lastrowid=False, retry=True):
        await self.ensure_connection()
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(query, params)
                    if not _query_returns_rows(query):
                        await connection.commit()
                    if return_lastrowid:
                        return cursor.lastrowid
                    return await cursor.fetchall()
        except (OperationalError, InterfaceError) as e:
            if retry:
                print(f"Потеря соединения: {e}. Повторная попытка...")
                await self.close()
                await self.connect()
                return await self._execute(query, params, return_lastrowid, retry=False)
            print(f"Повторная попытка не удалась: {e}")
            return None
        except AiomysqlError as e:
            print(f"Ошибка выполнения запроса: {e}")
            return None

    async def execute_insert(self, query, params=None):
        """
        Выполнение SQL-запроса INSERT и возврат ID вставленной записи.
        """
        return await self._execute(query, params, return_lastrowid=True)

    async def execute_query(self, query, params=None):
        """
        Выполнение SQL запроса и возврат результата с проверкой состояния соединения.
        """
        return await self._execute(query, params)
