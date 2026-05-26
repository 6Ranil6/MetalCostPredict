FROM python:3.12

# системные зависимости
RUN apt-get update && apt-get install -y \
    libgomp1 \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

    # libgomp1 <- CatBoost
# build-essential <- psycopg2

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app_db.py ./
COPY models/ ./models/

ENV DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
ENV PYTHONUNBUFFERED=1
ENV PORT=5111

EXPOSE 5111

CMD ["python", "-u", "app.py"]
