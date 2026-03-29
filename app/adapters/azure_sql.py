"""Async MySQL connection pool helpers and background job CRUD."""

import ssl
from contextlib import asynccontextmanager

import aiomysql

from config.settings import settings


async def create_tables():
    """Create the database and tables if they don't exist (async)."""
    prompt_table_schema = """
    CREATE TABLE IF NOT EXISTS {table_name} (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        name VARCHAR(100) NOT NULL,
        version VARCHAR(20) NOT NULL,
        prompt TEXT NOT NULL,
        description VARCHAR(255),
        status VARCHAR(50) DEFAULT 'inactive',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_name_version (name, version)
    );
    """

    bg_jobs_table_schema = """
    CREATE TABLE IF NOT EXISTS background_jobs (
        job_id VARCHAR(255) PRIMARY KEY,
        index_id VARCHAR(255) NOT NULL,
        callback_url TEXT NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'queued',
        message TEXT,
        result TEXT,
        error TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_jobs_status (status),
        INDEX idx_jobs_created_at (created_at)
    );
    """

    prompt_tables = ["use_case_prompts"]

    # Connect without db= to create the database if it doesn't exist
    conn = await aiomysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        autocommit=True,
        ssl=ssl.create_default_context(),
    )
    async with conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DB}`")
            await cursor.execute(f"USE `{settings.MYSQL_DB}`")
            for table in prompt_tables:
                await cursor.execute(prompt_table_schema.format(table_name=table))
                print(f"Created or verified table: {table}")
            await cursor.execute(bg_jobs_table_schema)
            print("Created or verified table: background_jobs")


# Async MySQL connection
@asynccontextmanager
async def get_db_connection():
    """Yield a single aiomysql connection with SSL; closes it after the block."""
    ssl_context = ssl.create_default_context()
    conn = await aiomysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DB,
        autocommit=True,
        ssl=ssl_context,
    )
    try:
        yield conn
    finally:
        conn.close()


async def create_bg_job(
    *,
    job_id: str,
    index_id: str,
    callback_url: str,
    status: str = "queued",
    message: str = "Job queued for processing",
):
    """Insert a new background_jobs row."""
    query = (
        "INSERT INTO background_jobs (job_id, index_id, callback_url, status, message) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    job_id,
                    index_id,
                    callback_url,
                    status,
                    message,
                ),
            )


async def update_bg_job(
    *,
    job_id: str,
    status: str,
    message: str,
    result_text: str | None = None,
    error_text: str | None = None,
):
    """Update status, message, and optional result/error for a job."""
    fields = ["status = %s", "message = %s", "updated_at = CURRENT_TIMESTAMP"]
    values = [status, message]
    if result_text is not None:
        fields.append("result = %s")
        values.append(result_text)
    if error_text is not None:
        fields.append("error = %s")
        values.append(error_text)
    values.append(job_id)

    query = f"UPDATE background_jobs SET {', '.join(fields)} WHERE job_id = %s"
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, values)


async def get_bg_job(job_id: str):
    """Fetch one background job by id as a dict row or None."""
    query = (
        "SELECT job_id, index_id, callback_url, status, message, result, error, "
        "created_at, updated_at FROM background_jobs WHERE job_id = %s"
    )
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, (job_id,))
            row = await cursor.fetchone()
            return row


async def get_all_bg_jobs():
    """Return all background jobs as a list of dicts, ordered by created_at DESC."""
    query = """
        SELECT job_id,
               index_id,
               callback_url,
               status,
               message,
               result,
               error,
               created_at,
               updated_at
        FROM background_jobs
        ORDER BY created_at DESC
    """
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query)
            rows = await cursor.fetchall()
            return rows


async def clear_all_bg_jobs():
    """Delete all rows from background_jobs; return deleted row count."""
    query = "DELETE FROM background_jobs"
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query)
            rowcount = cursor.rowcount
            return rowcount
