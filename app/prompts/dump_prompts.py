import mysql.connector
from config.settings import settings
import os
from datetime import datetime

# Where backups will be stored
BACKUP_DIR = "db_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Tables to dump
TABLES = [
    "main_prompts",
    "use_case_prompts",
    "role_prompts",
    "discipline_prompts"
]

def get_connection():
    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        port=settings.MYSQL_PORT
    )

def dump_all_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Date prefix for backup file
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"{date_prefix}_prompts_backup.sql")

    with open(backup_file, "w", encoding="utf-8") as f:
        for table in TABLES:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            f.write(f"-- Dumping table `{table}`\n")
            for row in rows:
                values = []
                for val in row:
                    if val is None:
                        values.append("NULL")
                    else:
                        safe_val = str(val).replace("'", "''")
                        values.append(f"'{safe_val}'")
                insert_stmt = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                f.write(insert_stmt)
            f.write("\n\n")
            print(f"Dumped {len(rows)} rows from {table}")

    cursor.close()
    conn.close()
    print(f"All tables dumped into {backup_file}")

if __name__ == "__main__":
    dump_all_tables()