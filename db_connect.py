import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """
    Establish and return a MySQL database connection.
    
    Returns:
        mysql.connector.connection.MySQLConnection: Database connection object if successful
        None: If connection fails
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        
        if connection.is_connected():
            print("Successfully connected to MySQL Server")
            return connection
            
    except Error as e:
        print(f"Error: Could not connect to MySQL Server - {e}")
        return None
