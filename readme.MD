4. Настройте переменные окружения:

    Проект требует следующих переменных окружения для работы:

    - `MYSQL_HOST_LOCAL`: Локальный хост базы данных MySQL
    - `MYSQL_USER_LOCAL`: Имя пользователя локальной базы данных MySQL.
    - `MYSQL_PASSWORD_LOCAL`: Пароль локальной базы данных MySQL.
    - `MYSQL_DB_LOCAL`: Имя локальной базы данных MySQL.
    - `MYSQL_HOST_REMOTE`: Хост Netstat
    - `MYSQL_USER_REMOTE`: Имя пользователя Netstat
    - `MYSQL_PASSWORD_REMOTE`: Пароль Netstat

    Вы можете установить эти переменные, используя терминал (пример для Unix-based систем):

    ```bash
    export MYSQL_HOST_LOCAL=localhost
    export MYSQL_USER_LOCAL=your_username
    export MYSQL_PASSWORD_LOCAL=your_password
    export MYSQL_DB_LOCAL=your_database
    export MYSQL_HOST_REMOTE=ntst_host
    export MYSQL_USER_REMOTE=ntst_username
    export MYSQL_PASSWORD_REMOTE=ntst_password
    ```