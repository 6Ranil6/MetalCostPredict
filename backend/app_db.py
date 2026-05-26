"""
Модуль для работы с PostgreSQL БД.
Содержит инициализацию таблиц, управление пулом соединений и утилиты для запросов.
"""

import os
import asyncio
import hashlib
import psycopg2
import psycopg2.extras
from psycopg2 import pool

PG_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


def hash_password(password: str) -> str:
    """Хеширует пароль с использованием SHA256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_db_sync():
    """Синхронная инициализация таблиц БД (выполняется один раз при запуске)."""
    conn = psycopg2.connect(dsn=PG_DSN)
    try:
        with conn.cursor() as cur:
            # таблица ролей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT
                )
            """)

            # таблица пользователей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(64) NOT NULL,
                    role_id INTEGER REFERENCES roles(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # таблица сообщений обратной связи
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback_messages (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    subject VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # таблица истории прогнозов
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    input_data TEXT NOT NULL,
                    predicted_price NUMERIC(15, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # дефолтные роли
            cur.execute("""
                INSERT INTO roles (id, name, description) VALUES 
                (1, 'user', 'Пользователь'),
                (2, 'pro', 'Пользователь Pro'),
                (3, 'admin', 'Администратор')
                ON CONFLICT (id) DO NOTHING
            """)

            # сброс последовательности генерации ID для роли
            cur.execute("""
                SELECT setval(pg_get_serial_sequence('roles', 'id'), coalesce(max(id), 1)) FROM roles;
            """)
            conn.commit()
    finally:
        conn.close()


def sync_execute(db_pool, query, params):
    """Синхронное выполнение SQL запроса на изменение (INSERT, UPDATE, DELETE)."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    finally:
        db_pool.putconn(conn)


def sync_fetchrow(db_pool, query, params):
    """Синхронное получение одной строки в виде словаря."""
    conn = db_pool.getconn()
    try:
        # RealDictCursor для получения результатов в виде dict
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()
    finally:
        db_pool.putconn(conn)


# АСИНХРОННЫЕ ОБЕРТКИ НАД СИНХРОННЫМИ ЗАПРОСАМИ

async def init_db(app):
    """Инициализация пула соединений при запуске приложения."""
    await asyncio.to_thread(init_db_sync)
    
    # создаем пул соединений
    app['db_pool'] = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=20, dsn=PG_DSN)
    print("База данных PostgreSQL (psycopg2) успешно инициализирована.")


async def close_db(app):
    """Закрытие пула соединений при выключении приложения."""
    if 'db_pool' in app:
        app['db_pool'].closeall()
        print("Пул соединений PostgreSQL (psycopg2) закрыт.")


async def run_execute(app, query, *params):
    """Асинхронное выполнение SQL запроса на изменение."""
    return await asyncio.to_thread(sync_execute, app['db_pool'], query, params)


async def run_fetchrow(app, query, *params):
    """Асинхронное получение одной строки."""
    return await asyncio.to_thread(sync_fetchrow, app['db_pool'], query, params)
