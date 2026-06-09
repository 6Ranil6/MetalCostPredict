FROM python:3.12-slim

# системные зависимости
RUN apt-get update && apt-get install -y \
    libgomp1 \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# libgomp1 <- CatBoost
# build-essential <- psycopg2
# curl <- healthcheck

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app_db.py config.py model.py data_validation.py ./
COPY handlers/ ./handlers/
COPY models/ ./models/

ENV DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
ENV PYTHONUNBUFFERED=1
ENV PORT=5111
ENV OLLAMA_URL=http://ollama:11434

EXPOSE 5111

# Добавляем небольшую задержку для инициализации моделей
CMD ["python", "-u", "app.py"]
