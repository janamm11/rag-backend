from app.mysql_client import mysql_connection

print("MySQL connected:", mysql_connection.is_connected())