from db_manager import DatabaseManager
import asyncio
import os
from dotenv import load_dotenv


load_dotenv()

class Calculator:
    def __init__(self):
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

    async def get_put_info(self):
        logs_data = await self.remote_db.execute_query('''select log.id, log.datetime, log.ip, sw.canton, sw.model, sw.rank
                                                            from command_logs.logs log
                                                            join mrtg.switches sw on log.ip = sw.ip
                                                            where sw.canton in (
                                                            'Минский',
                                                            'Оболонский',
                                                            'Голосеевский',
                                                            'Виноградарский',
                                                            'Лукьяновский',
                                                            'Святошинский',
                                                            'Бощаговский',
                                                            'Теремковский'
                                                            )''')
        await self.remote_db.close()
        return logs_data

async def main():
    calculator = Calculator()
    logs_data = await calculator.get_put_info()
    print(logs_data)

if __name__ == '__main__':
    asyncio.run(main())
