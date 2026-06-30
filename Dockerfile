# Используем базовое изображение с Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем LibreOffice для конвертации DOCX/XLSX в PDF
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код в контейнер
COPY . .

# Указываем переменные среды для Quart
ENV QUART_APP=app:asgi_app
ENV QUART_ENV=development

# Указываем команду запуска Hypercorn в режиме ASGI
CMD ["hypercorn", "--reload", "-b", "0.0.0.0:5000", "app:asgi_app"]
