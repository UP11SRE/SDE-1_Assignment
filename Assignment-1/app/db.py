# app/db.py
import asyncpg
import logging
from app.config import DATABASE_URL  

pool = None

async def init_db_pool():

    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    logging.info("Database connection pool created.")

async def close_db_pool():

    global pool
    await pool.close()
    print("Database connection pool closed.")

async def execute_query(query: str, *args):

    async with pool.acquire() as connection:
        return await connection.execute(query, *args)

async def fetch_query(query: str, *args):

    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)
    
# app/db.py additions

async def create_tables():
    create_table_query = """
    CREATE TABLE IF NOT EXISTS processing_requests (
      request_id       TEXT PRIMARY KEY,
      status           TEXT,
      processed_images TEXT,
      error            TEXT,
      webhook_url      TEXT
    );
    """
    async with pool.acquire() as connection:
        await connection.execute(create_table_query)
print("Tables ensured to exist.")
