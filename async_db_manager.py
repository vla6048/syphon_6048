from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.engine import URL
import os



class AsyncSQLAlchemyManager:


    def __init__(self, host: str, user: str, password: str, db: str, echo: bool = False):
        self.DATABASE_URL = URL.create(
            "mysql+aiomysql",
            username=user,
            password=password,
            host=host,
            database=db,
        )
        self.engine = None
        self.SessionLocal = None
        self.echo = echo

    def connect(self):

        if self.engine is None:
            # 2. Создание асинхронного Engine
            self.engine = create_async_engine(
                self.DATABASE_URL,
                echo=self.echo,  # Вывод SQL-запросов в консоль
                pool_size=10,  # Размер пула соединений
                max_overflow=20,
                pool_pre_ping=True,
            )
            safe_url = self.DATABASE_URL.render_as_string(hide_password=True)
            print(f"Асинхронный Engine создан для базы данных {safe_url}.")

            # 3. Настройка фабрики асинхронных сессий
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
        else:
            print("Engine уже инициализирован.")

    async def close(self):
        """
        Закрытие Engine и освобождение ресурсов пула.
        Вызывается при завершении работы приложения.
        """
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
            print("🚫 Асинхронный Engine закрыт.")

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """
        Контекстный менеджер для получения асинхронной сессии.
        Используется в блоке 'async with'.
        """
        if self.SessionLocal is None:
            raise ConnectionError("Engine не инициализирован. Вызовите .connect() сначала.")

        # AsyncSession автоматически управляет транзакциями
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()  # Выполнение всех изменений
            except Exception as e:
                await session.rollback()  # Откат в случае ошибки
                raise e


# --- ПРИМЕР ИСПОЛЬЗОВАНИЯ ---
# Предположим, 'app_models.py' содержит класс User
# from .app_models import User
# (Если app_models находится в том же каталоге, что и этот файл)

async def run_example(user_model):
    """Пример использования менеджера с моделями."""

    # 1. Инициализация менеджера для одной из ваших БД
    db_manager = AsyncSQLAlchemyManager(
        host=os.getenv("MYSQL_HOST_LOCAL"),
        user=os.getenv("MYSQL_USER_LOCAL"),
        password=os.getenv("MYSQL_PASSWORD_LOCAL"),
        db=os.getenv("MYSQL_DB_LOCAL"),
        echo=True
    )
    db_manager.connect()

    # 2. Выполнение запроса с помощью контекстного менеджера
    try:
        async with db_manager.get_session() as session:
            # SQLAlchemy 2.0 style (предпочтительно):
            # 💡 Используйте автоматически сгенерированный класс User из app_models

            # Предполагается, что User - это ваш автоматически сгенерированный класс.
            result = await session.execute(
                select(user_model).where(user_model.id == 1)
            )

            # Получение первого объекта
            user = result.scalar_one_or_none()

            if user:
                print(f"\nНайдено: ID={user.id}, Имя={user.name}")
            else:
                print("\nПользователь не найден.")

    except Exception as e:
        print(f"\nПроизошла ошибка в запросе: {e}")

    finally:
        await db_manager.close()

# Для запуска примера в реальном асинхронном приложении:
# import asyncio
# from sqlalchemy import select
# asyncio.run(run_example(User))
