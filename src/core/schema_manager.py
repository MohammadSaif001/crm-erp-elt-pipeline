from pathlib import Path

from sqlalchemy import text


def execute_sql_file(engine, sql_file: str):
    sql_path = Path(sql_file)

    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file '{sql_file}' not found.")

    with open(sql_path, "r", encoding="utf-8") as SqlFile:
        SqlScript = SqlFile.read()

    with engine.begin() as connection:
        for statement in SqlScript.split(";"):
            statement = statement.strip()
            if statement:
                connection.execute(text(statement))
