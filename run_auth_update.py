from db_connect import get_db_connection
import os


def execute_sql_file(cursor, sql_file_path):
    """Execute each SQL statement in a file."""
    with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
        sql_content = sql_file.read()

    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

    for statement in statements:
        try:
            cursor.execute(statement)
            print(f"Executed: {statement.splitlines()[0][:80]}...")
        except Exception as error:
            error_text = str(error)
            if 'Duplicate column name' in error_text:
                print(f"Skipped (already applied): {statement.splitlines()[0][:80]}...")
                continue
            raise


def main():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            print('Failed to connect to database.')
            return

        cursor = connection.cursor()
        sql_file_path = os.path.join(os.path.dirname(__file__), 'update_auth.sql')

        execute_sql_file(cursor, sql_file_path)
        connection.commit()

        print('Authentication schema update completed successfully.')

    except Exception as error:
        if connection:
            connection.rollback()
        print(f'Auth schema update failed: {error}')

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print('Database connection closed.')


if __name__ == '__main__':
    main()
