import mysql.connector
from config.settings import settings

def get_connection():
    """Return a MySQL connection."""
    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        port=settings.MYSQL_PORT
    )

def create_tables():
    """Create the prompt tables and huddle jobs table if they don't exist."""
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

    # Huddle jobs table schema
    huddle_jobs_table_schema = """
    CREATE TABLE IF NOT EXISTS huddle_jobs (
        job_id VARCHAR(255) PRIMARY KEY,
        sequence_id INT NOT NULL,
        provider_id VARCHAR(255) NOT NULL,
        ccn VARCHAR(255) NOT NULL,
        branch_id INT NOT NULL,
        user_id INT NOT NULL,
        callback_url TEXT NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'queued',
        message TEXT,
        result JSON,
        error TEXT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        INDEX idx_huddle_jobs_status (status),
        INDEX idx_huddle_jobs_created_at (created_at)
    );
    """

    prompt_tables = [
        "main_prompts",
        "use_case_prompts",
        "role_prompts",
        "discipline_prompts"
    ]

    conn = get_connection()
    cursor = conn.cursor()
    
    # Create prompt tables
    for table in prompt_tables:
        cursor.execute(prompt_table_schema.format(table_name=table))
        print(f"Created or verified table: {table}")
    
    # Create huddle jobs table
    cursor.execute(huddle_jobs_table_schema)
    print("Created or verified table: huddle_jobs")
    
    cursor.close()
    conn.close()