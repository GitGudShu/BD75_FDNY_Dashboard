
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import os

# Suppress warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"

# Columns to Load
DT_COLS_EMS = ["INCIDENT_DATETIME", "FIRST_ASSIGNMENT_DATETIME", "FIRST_ON_SCENE_DATETIME"]
DT_COLS_FIRE = ["INCIDENT_DATETIME"]

MEASURE_COLS_EMS = ["DISPATCH_RESPONSE_SECONDS_QY", "INCIDENT_RESPONSE_SECONDS_QY", "INCIDENT_TRAVEL_TM_SECONDS_QY"]
MEASURE_COLS_FIRE = ["TOTAL_INCIDENT_DURATION_SECONDS"] # Check if this exists, else calculate? 
# Note: Fire data in previous check didn't show response time columns in the generic list, 
# but previous script used 'DISPATCH_RESPONSE_SECONDS_QY' etc if available. 
# Let's check availability during load.

# --- HELPER FUNCTIONS ---

def norm_text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.upper()

def norm_borough(s: pd.Series) -> pd.Series:
    x = norm_text(s)
    return x.replace({
        "RICHMOND / STATEN ISLAND": "STATEN ISLAND",
        "RICHMOND": "STATEN ISLAND",
        "STATEN ISLAND": "STATEN ISLAND",
    })

def parse_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")

def get_fiscal_year(date: pd.Series) -> pd.Series:
    return np.where(date.dt.month >= 7, date.dt.year + 1, date.dt.year)

def get_season(date: pd.Series) -> pd.Series:
    month = date.dt.month
    conditions = [
        (month.isin([12, 1, 2])),
        (month.isin([3, 4, 5])),
        (month.isin([6, 7, 8])),
        (month.isin([9, 10, 11]))
    ]
    choices = ['Winter', 'Spring', 'Summer', 'Fall']
    return pd.Series(np.select(conditions, choices, default='Unknown'), index=date.index)

# --- ETL STEPS ---

def load_data():
    print("Loading Raw Data...")
    try:
        ems = pd.read_csv(DATA_RAW / 'EMS.csv', low_memory=False) # optimized load later if needed
        fire = pd.read_csv(DATA_RAW / 'FIRE.csv', low_memory=False)
        firehouse = pd.read_csv(DATA_RAW / 'Firehouse.csv')
        print(f"Loaded: EMS ({len(ems)}), FIRE ({len(fire)}), Firehouse ({len(firehouse)})")
        return ems, fire, firehouse
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None

def build_dim_time(ems, fire):
    print("Building Dim_Time...")
    # Clean Datetimes first
    dts_ems = parse_dt(ems["INCIDENT_DATETIME"])
    dts_fire = parse_dt(fire["INCIDENT_DATETIME"])
    
    all_dates = pd.concat([dts_ems, dts_fire]).dropna().dt.floor("D").drop_duplicates().sort_values()
    
    dim = pd.DataFrame({"date": all_dates})
    dim["date_key"] = (dim["date"].dt.year * 10000 + dim["date"].dt.month * 100 + dim["date"].dt.day).astype("int32")
    dim["year"] = dim["date"].dt.year.astype("int16")
    dim["month"] = dim["date"].dt.month.astype("int8")
    dim["day"] = dim["date"].dt.day.astype("int8")
    dim["day_of_week"] = dim["date"].dt.weekday + 1
    dim["day_name"] = dim["date"].dt.day_name()
    dim["is_weekend"] = dim["day_of_week"].isin([6, 7]).astype("int8")
    dim["quarter"] = dim["date"].dt.quarter.astype("int8")
    dim["fiscal_year"] = get_fiscal_year(dim["date"]).astype("int16")
    dim["season"] = get_season(dim["date"])
    
    # Store keys back to result for joining? No, we join on date or calculate key on the fly.
    return dim

def build_dim_location(ems, fire):
    print("Building Dim_Location...")
    # Extract unique locations (Zip, Borough, etc)
    # EMS: BOROUGH, ZIPCODE
    # FIRE: INCIDENT_BOROUGH, ZIPCODE
    
    locs_ems = pd.DataFrame({
        "zipcode": pd.to_numeric(ems["ZIPCODE"], errors='coerce').dropna().astype("Int64"),
        "borough": norm_borough(ems["BOROUGH"])
    })
    
    locs_fire = pd.DataFrame({
        "zipcode": pd.to_numeric(fire["ZIPCODE"], errors='coerce').dropna().astype("Int64"),
        "borough": norm_borough(fire["INCIDENT_BOROUGH"])
    })
    
    # Union
    all_locs = pd.concat([locs_ems, locs_fire]).drop_duplicates().dropna(subset=["zipcode"])
    
    # Sort and Key
    all_locs = all_locs.sort_values(["borough", "zipcode"]).reset_index(drop=True)
    all_locs.insert(0, "location_key", (np.arange(len(all_locs)) + 1).astype("int32"))
    
    return all_locs

def build_dim_firehouse(firehouse):
    print("Building Dim_Firehouse...")
    df = firehouse.copy()
    if "FacilityName" in df.columns:
        df["firehouse_name"] = df["FacilityName"]
    if "Postcode" in df.columns:
        df["zipcode"] = pd.to_numeric(df["Postcode"], errors='coerce').astype("Int64")
    if "Borough" in df.columns:
        df["borough"] = norm_borough(df["Borough"])
        
    cols = ["firehouse_name", "zipcode", "borough", "FacilityAddress", "Latitude", "Longitude"]
    cols = [c for c in cols if c in df.columns]
    
    dim = df[cols].drop_duplicates().reset_index(drop=True)
    dim.insert(0, "firehouse_key", (np.arange(len(dim)) + 1).astype("int32"))
    return dim

def build_dim_incident_type(ems, fire):
    print("Building Dim_IncidentType...")
    # Combine Types from EMS and Fire? 
    # Usually better to have separate dims if they are very different, OR a unified one.
    # PROJET.MD implies a generic "Dim_IncidentType".
    # EMS: INITIAL_CALL_TYPE, FINAL_CALL_TYPE
    # FIRE: INCIDENT_CLASSIFICATION, INCIDENT_CLASSIFICATION_GROUP
    
    # Let's build a unified list or separate?
    # Given they are distinct codes, maybe a single table with "Source_System" column?
    # Or just "incident_type_code" and "description".
    
    # For simplicity/robustness in Power BI, separate dimensions are often cleaner if no overlap.
    # But user asked for Galaxy. Let's try to unify `incident_type_desc`.
    
    # EMS Types
    types_ems = ems[["FINAL_CALL_TYPE"]].dropna().drop_duplicates()
    types_ems.columns = ["type_code"]
    types_ems["source"] = "EMS"
    types_ems["category"] = "Medical" # simplified
    
    # Fire Types
    types_fire = fire[["INCIDENT_CLASSIFICATION", "INCIDENT_CLASSIFICATION_GROUP"]].dropna().drop_duplicates()
    types_fire.columns = ["type_code", "category"]
    types_fire["source"] = "FIRE"
    
    # Union
    dim = pd.concat([types_ems, types_fire], ignore_index=True).drop_duplicates(subset=["type_code", "source"])
    dim = dim.sort_values(["source", "type_code"]).reset_index(drop=True)
    dim.insert(0, "incident_type_key", (np.arange(len(dim)) + 1).astype("int32"))
    
    return dim

def build_facts(ems, fire, dim_time, dim_location, dim_type):
    print("Building Facts...")
    
    # --- FACT EMS ---
    print("  Processing EMS...")
    f_ems = ems.copy()
    
def build_dim_weather(weather_df):
    print("Building Dim_Weather...")
    w = weather_df.copy()
    w["dt"] = pd.to_datetime(w["time"])
    w["date_key"] = (w["dt"].dt.year * 10000 + w["dt"].dt.month * 100 + w["dt"].dt.day).astype("int32")
    w["hour"] = w["dt"].dt.hour.astype("int8")
    
    # Rename cols
    w.rename(columns={
        "temperature_2m": "temp_f",
        "precipitation": "precip_in",
        "weathercode": "weather_code",
        "windspeed_10m": "wind_mph"
    }, inplace=True)
    
    # Add Flags
    w["is_raining"] = (w["precip_in"] > 0).astype("int8")
    w["is_hot"] = (w["temp_f"] > 90).astype("int8")
    w["is_cold"] = (w["temp_f"] < 32).astype("int8")
    
    # Surrogate Key
    w = w.sort_values(["date_key", "hour"]).reset_index(drop=True)
    w.insert(0, "weather_key", (np.arange(len(w)) + 1).astype("int32"))
    
    # Keep only relevant cols
    cols = ["weather_key", "date_key", "hour", "temp_f", "precip_in", "wind_mph", "weather_code", "is_raining", "is_hot", "is_cold"]
    return w[cols]

def build_facts(ems, fire, dim_time, dim_location, dim_type, dim_weather):
    print("Building Facts...")
    
    # Efficiency: Convert dim_weather to dictionary map for faster lookup? 
    # Or just merge. Merge is fine for this size (~30k hours).
    weather_lookup = dim_weather[["date_key", "hour", "weather_key"]]
    
    # --- FACT EMS ---
    print("  Processing EMS...")
    f_ems = ems.copy()
    
    # Dates
    f_ems["dt"] = parse_dt(f_ems["INCIDENT_DATETIME"])
    f_ems["date_key"] = (f_ems["dt"].dt.year * 10000 + f_ems["dt"].dt.month * 100 + f_ems["dt"].dt.day).astype("Int32")
    f_ems["hour"] = f_ems["dt"].dt.hour.astype("Int8")
    
    # Location Key
    f_ems["zipcode_num"] = pd.to_numeric(f_ems["ZIPCODE"], errors='coerce').astype("Int64")
    f_ems["borough_n"] = norm_borough(f_ems["BOROUGH"])
    
    f_ems = f_ems.merge(dim_location, left_on=["zipcode_num", "borough_n"], right_on=["zipcode", "borough"], how="left")
    f_ems.rename(columns={"location_key": "location_key_fk"}, inplace=True)
    
    # Type Key
    f_ems = f_ems.merge(dim_type[dim_type["source"]=="EMS"], left_on="FINAL_CALL_TYPE", right_on="type_code", how="left")
    
    # Weather Key
    f_ems = f_ems.merge(weather_lookup, on=["date_key", "hour"], how="left")
    
    # Select Cols - CLEANED per user request
    fact_ems_out = pd.DataFrame()
    fact_ems_out["incident_id"] = f_ems["CAD_INCIDENT_ID"]
    fact_ems_out["date_key"] = f_ems["date_key"]
    fact_ems_out["hour"] = f_ems["hour"]
    fact_ems_out["location_key"] = f_ems["location_key_fk"]
    fact_ems_out["incident_type_key"] = f_ems["incident_type_key"]
    fact_ems_out["weather_key"] = f_ems["weather_key"].astype("Int32")
    
    # Measures
    # Keep only critical ones for analysis (Gridlock, Shift Change)
    kp_cols = {
        "DISPATCH_RESPONSE_SECONDS_QY": "dispatch_time",
        "INCIDENT_TRAVEL_TM_SECONDS_QY": "travel_time",
        "INCIDENT_RESPONSE_SECONDS_QY": "response_time"
    }
    for old, new in kp_cols.items():
        if old in f_ems.columns:
            fact_ems_out[new] = pd.to_numeric(f_ems[old], errors='coerce')
            
    fact_ems_out["nb_interventions"] = 1
    
    # ADDED FOR SANKEY ANALYSIS
    if "INITIAL_CALL_TYPE" in f_ems.columns:
        fact_ems_out["initial_call_type"] = f_ems["INITIAL_CALL_TYPE"]
    if "FINAL_CALL_TYPE" in f_ems.columns:
        fact_ems_out["final_call_type"] = f_ems["FINAL_CALL_TYPE"]
    
    # --- FACT FIRE ---
    print("  Processing FIRE...")
    f_fire = fire.copy()
    
    f_fire["dt"] = parse_dt(f_fire["INCIDENT_DATETIME"])
    f_fire["date_key"] = (f_fire["dt"].dt.year * 10000 + f_fire["dt"].dt.month * 100 + f_fire["dt"].dt.day).astype("Int32")
    f_fire["hour"] = f_fire["dt"].dt.hour.astype("Int8")
    
    f_fire["zipcode_num"] = pd.to_numeric(f_fire["ZIPCODE"], errors='coerce').astype("Int64")
    f_fire["borough_n"] = norm_borough(f_fire["INCIDENT_BOROUGH"])
    
    f_fire = f_fire.merge(dim_location, left_on=["zipcode_num", "borough_n"], right_on=["zipcode", "borough"], how="left")
    f_fire.rename(columns={"location_key": "location_key_fk"}, inplace=True)
    
    # Type Key
    f_fire = f_fire.merge(dim_type[dim_type["source"]=="FIRE"], left_on="INCIDENT_CLASSIFICATION", right_on="type_code", how="left")

    # Weather Key
    f_fire = f_fire.merge(weather_lookup, on=["date_key", "hour"], how="left")

    fact_fire_out = pd.DataFrame()
    fact_fire_out["incident_id"] = f_fire["STARFIRE_INCIDENT_ID"]
    fact_fire_out["date_key"] = f_fire["date_key"]
    fact_fire_out["hour"] = f_fire["hour"]
    fact_fire_out["location_key"] = f_fire["location_key_fk"]
    fact_fire_out["incident_type_key"] = f_fire["incident_type_key"]
    fact_fire_out["weather_key"] = f_fire["weather_key"].astype("Int32")
    
    # Measures (Units)
    for c in ["ENGINES_ASSIGNED_QUANTITY", "LADDERS_ASSIGNED_QUANTITY", "OTHER_UNITS_ASSIGNED_QUANTITY"]:
        if c in f_fire.columns:
            fact_fire_out[c.lower()] = pd.to_numeric(f_fire[c], errors="coerce").fillna(0).astype("int16")
            
    # Pre-calculate Total Units
    fact_fire_out["total_units"] = (fact_fire_out["engines_assigned_quantity"] + 
                                    fact_fire_out["ladders_assigned_quantity"] + 
                                    fact_fire_out["other_units_assigned_quantity"])
            
    # Measures (Time) - Normalized names
    # Fire might calculate fields differently or have different names?
    # Previous check showed they share generic names if standardized.
    # We will look for generic Measure Cols or specific ones.
    # FIRE.csv usually has keys like 'DispatchTime' etc?
    # Based on previous generic list: DISPATCH_RESPONSE_SECONDS_QY etc.
    for old, new in kp_cols.items():
        if old in f_fire.columns:
            fact_fire_out[new] = pd.to_numeric(f_fire[old], errors='coerce')

    if "TOTAL_INCIDENT_DURATION_SECONDS" in f_fire.columns:
         fact_fire_out["total_duration"] = pd.to_numeric(f_fire["TOTAL_INCIDENT_DURATION_SECONDS"], errors="coerce")
         
    fact_fire_out["nb_interventions"] = 1
    
    return fact_ems_out, fact_fire_out

def main():
    print("Starting Galaxy ETL...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    ems, fire, firehouse = load_data()
    if ems is None: return

    # Load Weather
    weather_path = DATA_RAW / "weather_nyc.csv"
    if weather_path.exists():
        weather_df = pd.read_csv(weather_path)
        dim_weather = build_dim_weather(weather_df)
    else:
        print("Warning: Weather data not found. Creating dummy Dim_Weather.")
        dim_weather = pd.DataFrame(columns=["weather_key", "date_key", "hour", "temp_f"])

    dim_time = build_dim_time(ems, fire)
    dim_location = build_dim_location(ems, fire)
    dim_firehouse = build_dim_firehouse(firehouse)
    dim_type = build_dim_incident_type(ems, fire)
    
    fact_ems, fact_fire = build_facts(ems, fire, dim_time, dim_location, dim_type, dim_weather)
    
    # Export
    print("Exporting...")
    dim_time.to_parquet(OUTPUT_DIR / "Dim_Time.parquet", index=False)
    dim_location.to_parquet(OUTPUT_DIR / "Dim_Location.parquet", index=False)
    dim_firehouse.to_parquet(OUTPUT_DIR / "Dim_Firehouse.parquet", index=False)
    dim_type.to_parquet(OUTPUT_DIR / "Dim_IncidentType.parquet", index=False)
    dim_weather.to_parquet(OUTPUT_DIR / "Dim_Weather.parquet", index=False)
    
    fact_ems.to_parquet(OUTPUT_DIR / "Fact_Incidents_EMS.parquet", index=False)
    fact_fire.to_parquet(OUTPUT_DIR / "Fact_Incidents_Fire.parquet", index=False)
    
    print(f"Done. Files saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
