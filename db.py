import mysql.connector
import json
import os
from typing import List, Dict, Any

# --- CONFIGURATION & SIMULATION TOGGLE ---
USE_SIMULATION_MODE = False  # Set to True if MySQL is offline or for fallback testing

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "MySQL@2026",  # Replace with your local MySQL password
    "database": "aeroindex_db",
    "connect_timeout": 3
}

def get_db_connection():
    """Establishes connection to MySQL database."""
    return mysql.connector.connect(**MYSQL_CONFIG)

def get_latest_records(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches the most recent flight records from MySQL.
    Falls back to mock_data.json if USE_SIMULATION_MODE = True or DB connection fails.
    """
    if USE_SIMULATION_MODE:
        return _get_mock_fallback()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT airline, flight_number, origin, destination, departure_time, price, scraped_at
            FROM flight_prices
            ORDER BY id DESC
            LIMIT %s
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        for row in rows:
            row["price"] = float(row["price"])
            row["departure_time"] = str(row["departure_time"])
            row["scraped_at"] = str(row["scraped_at"])
            
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[Warning] MySQL fetch failed ({e}). Falling back to Simulation Mode.")
        return _get_mock_fallback()

def save_flight_records(records: List[Dict[str, Any]]):
    """Inserts clean flight records into MySQL."""
    if not records or USE_SIMULATION_MODE:
        return
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = '''
            INSERT INTO flight_prices (airline, flight_number, origin, destination, departure_time, price, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        
        data_tuples = [
            (
                r["airline"],
                r["flight_number"],
                r["origin"],
                r["destination"],
                r["departure_time"],
                float(r["price"]),
                r["scraped_at"]
            )
            for r in records
        ]
        
        cursor.executemany(insert_query, data_tuples)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Error] Failed to save flight records to MySQL: {e}")

def _get_mock_fallback() -> List[Dict[str, Any]]:
    """Loads mock_data.json as zero-latency fallback."""
    if os.path.exists("mock_data.json"):
        with open("mock_data.json", "r") as f:
            return json.load(f)
    return []
