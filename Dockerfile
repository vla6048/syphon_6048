# Используйте официальный образ Python в качестве базового
FROM python:3.10-slim

# Установите необходимые библиотеки
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установите зависимости вашего приложения
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Указываем команду для запуска приложения
CMD ["uvicorn", "wsgi:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]