"""Database backup utility for prompts."""

import asyncio
import os
from datetime import datetime
from app.adapters.azure_sql import get_db_connection

# Where backups will be stored
BACKUP_DIR = "db_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Tables to dump
TABLES = [
    "use_case_prompts",
]

async def dump_all_tables():
    """Dump all prompt tables to SQL file."""
    # Date prefix for backup file
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"{date_prefix}_prompts_backup.sql")

    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            with open(backup_file, "w", encoding="utf-8") as f:
                for table in TABLES:
                    await cursor.execute(f"SELECT * FROM {table}")
                    rows = await cursor.fetchall()
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

    print(f"All tables dumped into {backup_file}")

if __name__ == "__main__":
    asyncio.run(dump_all_tables())
