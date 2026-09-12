import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

mysql_connection = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
)

def get_cursor():
    if not mysql_connection.is_connected():
        mysql_connection.reconnect()
    return mysql_connection.cursor()