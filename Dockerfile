# Используем базовое изображение с Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код в контейнер
COPY . .

# Указываем переменные среды для Quart
ENV QUART_APP=app:asgi_app
ENV QUART_ENV=development

# Устанавливаем Hypercorn (ASGI сервер)
RUN pip install hypercorn

# Указываем команду запуска Hypercorn в режиме ASGI
CMD ["hypercorn", "--reload", "-b", "0.0.0.0:5000", "app:asgi_app"]