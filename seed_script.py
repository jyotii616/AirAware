import mysql.connector
from datetime import datetime, timedelta
import random
import sys

MYSQL_CONFIG = {
    "host": "127.0.0.1",  # Use 127.0.0.1 instead of localhost to avoid IPv6 resolution delays
    "user": "root",
    "password": "YOUR_ACTUAL_MYSQL_PASSWORD",  # Make sure this matches your MySQL Workbench password!
    "database": "aeroindex_db",
    "connect_timeout": 5
}

AIRLINES = ["IndiGo", "Air India", "Vistara", "SpiceJet"]
ROUTES = [
    ("DEL", "BOM"),
    ("BOM", "DEL"),
    ("BLR", "DEL"),
    ("DEL", "BLR")
]

BASE_PRICES = {
    "DEL-BOM": 4500.0,
    "BOM-DEL": 4400.0,
    "BLR-DEL": 5200.0,
    "DEL-BLR": 5100.0
}

def generate_30_day_seed():
    print("Attempting to connect to MySQL database...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        print("Connected successfully! Generating historical data...")
        
        records = []
        now = datetime.now()
        
        for day_offset in range(30, -1, -1):
            scrape_date = now - timedelta(days=day_offset)
            
            for origin, dest in ROUTES:
                route_key = f"{origin}-{dest}"
                base_fare = BASE_PRICES.get(route_key, 4500.0)
                
                for airline in AIRLINES:
                    price_variation = random.uniform(0.85, 1.15)
                    price = round(base_fare * price_variation, 2)
                    
                    flight_num = f"{airline[:2].upper()}-{random.randint(100, 999)}"
                    dep_time = scrape_date + timedelta(days=7, hours=random.randint(6, 22))
                    
                    records.append((
                        airline,
                        flight_num,
                        origin,
                        dest,
                        dep_time.strftime("%Y-%m-%d %H:%M:%S"),
                        price,
                        scrape_date.strftime("%Y-%m-%d %H:%M:%S")
                    ))

        query = """
            INSERT INTO flight_prices 
            (airline, flight_number, origin, destination, departure_time, price, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(query, records)
        conn.commit()
        print(f"Success! Inserted {len(records)} records into flight_prices.")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"MySQL Connection Error: {err}")
        sys.exit(1)

if __name__ == "__main__":
    generate_30_day_seed()