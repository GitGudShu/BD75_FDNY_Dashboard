
import urllib.request
import json
import pandas as pd
import os
from pathlib import Path

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DATA_DIR / "weather_nyc.csv"

# NYC Coordinates (City Hall)
LAT = 40.7128
LON = -74.0060

# Date Range
START_DATE = "2022-01-01"
END_DATE = "2025-12-31"

URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_weather():
    print(f"Fetching weather data for NYC ({LAT}, {LON}) from {START_DATE} to {END_DATE}...")
    
    # Construct Query
    query = f"?latitude={LAT}&longitude={LON}&start_date={START_DATE}&end_date={END_DATE}"
    query += "&hourly=temperature_2m,precipitation,weathercode,windspeed_10m"
    query += "&timezone=America/New_York"
    query += "&temperature_unit=fahrenheit"
    query += "&precipitation_unit=inch"
    query += "&windspeed_unit=mph"
    
    full_url = URL + query
    
    try:
        with urllib.request.urlopen(full_url) as response:
            data = json.loads(response.read().decode())
        
        # Parse Hourly Data
        hourly = data.get("hourly", {})
        df = pd.DataFrame(hourly)
        
        # Save
        print(f"Saving {len(df)} records to {OUTPUT_FILE}...")
        df.to_csv(OUTPUT_FILE, index=False)
        print("Done.")
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")

if __name__ == "__main__":
    fetch_weather()
