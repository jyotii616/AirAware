import json
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from processing import (
    clean_data,
    detect_anomalies,
    filter_anomalies,
    daily_route_averages,
    calculate_laspeyres_index,
    log_scraper_run,
    scraper_health_summary
)
from master_scraper import scrape_all_flights
import db

app = FastAPI(title="AeroIndex MoSPI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent anomaly streak tracking across runs
ANOMALY_STREAKS = {}

@app.get("/api/v1/metrics/latest")
def get_latest_metrics():
    """
    Fetches latest records from MySQL (or mock data if simulation/offline),
    runs anomaly detection, and calculates the Laspeyres index.
    """
    raw_records = db.get_latest_records(limit=100)
    
    # 1. Pipeline Processing
    cleaned = clean_data(raw_records)
    flagged = detect_anomalies(cleaned)
    valid_records = filter_anomalies(flagged)
    
    # 2. Compute Route Averages & Laspeyres Index
    current_avg_prices = daily_route_averages(valid_records)
    
    # Base period benchmark prices
    base_prices = {
        "DEL-BOM": 4500.0,
        "BLR-DEL": 5200.0,
        "MAA-DEL": 3800.0
    }
    
    index_result = calculate_laspeyres_index(
        current_prices_dict=current_avg_prices,
        base_prices_dict=base_prices
    )
    
    return {
        "status": "success",
        "is_simulation": db.USE_SIMULATION_MODE,
        "total_records": len(flagged),
        "airfare_index": index_result.get("overall_index", 100.0),
        "index_breakdown": index_result.get("per_route", {}),
        "data": flagged
    }

def execute_live_scrape_pipeline(origin: str = "DEL", destination: str = "BOM"):
    """Background task to run scrapers, clean records, save to MySQL, and log health."""
    # 1. Scrape
    result = scrape_all_flights(origin=origin, destination=destination, days_ahead=7, headless=True)
    raw_flights = result.get("flights", [])
    
    # 2. Log Health
    for airline, err in result.get("errors", {}).items():
        log_entry = log_scraper_run(f"{origin}-{destination}", "fail", 0, error_message=err)
        # db.save_scraper_log(log_entry)
        
    if raw_flights:
        log_entry = log_scraper_run(f"{origin}-{destination}", "success", len(raw_flights))
        # db.save_scraper_log(log_entry)

    # 3. Clean & Save
    cleaned = clean_data(raw_flights)
    if cleaned:
        db.save_flight_records(cleaned)

@app.post("/api/v1/scrape/trigger")
def trigger_scrape(background_tasks: BackgroundTasks, origin: str = "DEL", destination: str = "BOM"):
    """Triggers a live scrape in the background without timing out the API response."""
    background_tasks.add_task(execute_live_scrape_pipeline, origin, destination)
    
    return {
        "status": "success",
        "message": f"Live scrape initiated for {origin}-{destination}. Database will update shortly."
    }