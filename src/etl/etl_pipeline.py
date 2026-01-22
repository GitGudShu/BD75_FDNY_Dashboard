
import pandas as pd
import numpy as np
from pathlib import Path
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Constants
DT_COLS_COMMON = [
    "INCIDENT_DATETIME",
    "FIRST_ASSIGNMENT_DATETIME",
    "FIRST_ON_SCENE_DATETIME",
    "INCIDENT_CLOSE_DATETIME",
]
DT_COLS_EMS_EXTRA = [
    "FIRST_HOSP_ARRIVAL_DATETIME",
    "FIRST_TO_HOSP_DATETIME",
]
MEASURE_COLS_SHARED = [
    "DISPATCH_RESPONSE_SECONDS_QY",
    "INCIDENT_RESPONSE_SECONDS_QY",
    "INCIDENT_TRAVEL_TM_SECONDS_QY",
]
LOC_COLS = [
    "BOROUGH_NORM",
    "ZIPCODE",
    "POLICEPRECINCT",
    "CITYCOUNCILDISTRICT",
    "COMMUNITYDISTRICT",
    "COMMUNITYSCHOOLDISTRICT",
    "CONGRESSIONALDISTRICT",
]

# Determine project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "powerbi_parquet"

def norm_text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.upper()

def norm_borough(s: pd.Series) -> pd.Series:
    x = norm_text(s)
    return x.replace(
        {
            "RICHMOND / STATEN ISLAND": "STATEN ISLAND",
            "RICHMOND": "STATEN ISLAND",
            "STATEN ISLAND": "STATEN ISLAND",
        }
    )

def clean_seconds(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    x = x.mask(x < 0, np.nan)
    x = x.mask(x >= 999, np.nan)
    return x

def parse_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")

def date_key_from_dt(s: pd.Series) -> pd.Series:
    d = s.dt.floor("D")
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int32")

def get_fiscal_year(date: pd.Series) -> pd.Series:
    # NYC Fiscal Year starts July 1st.
    # If month >= 7, FY = Year + 1, else FY = Year
    return np.where(date.dt.month >= 7, date.dt.year + 1, date.dt.year)

def get_season(date: pd.Series) -> pd.Series:
    # Northern Hemisphere seasons
    # Winter: Dec, Jan, Feb
    # Spring: Mar, Apr, May
    # Summer: Jun, Jul, Aug
    # Fall: Sep, Oct, Nov
    month = date.dt.month
    conditions = [
        (month.isin([12, 1, 2])),
        (month.isin([3, 4, 5])),
        (month.isin([6, 7, 8])),
        (month.isin([9, 10, 11]))
    ]
    choices = ['Winter', 'Spring', 'Summer', 'Fall']
    return pd.Series(np.select(conditions, choices, default='Unknown'), index=date.index)

def load_data():
    print("Loading data...")
    try:
        ems = pd.read_csv(DATA_RAW / 'EMS.csv')
        fire = pd.read_csv(DATA_RAW / 'FIRE.csv')
        fire_stations = pd.read_csv(DATA_RAW / 'Firehouse.csv')
        print(f"Loaded: EMS ({len(ems)} rows), FIRE ({len(fire)} rows), Firehouse ({len(fire_stations)} rows)")
        return ems, fire, fire_stations
    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure CSV files are in the data/raw directory.")
        return None, None, None

def make_staging(ems, fire):
    print("Creating staging tables...")
    ems_c = ems.copy()
    fire_c = fire.copy()

    # Normalize Boroughs
    ems_c["BOROUGH_NORM"] = norm_borough(ems_c["BOROUGH"]) if "BOROUGH" in ems_c.columns else pd.NA
    fire_c["BOROUGH_NORM"] = norm_borough(fire_c["INCIDENT_BOROUGH"]) if "INCIDENT_BOROUGH" in fire_c.columns else pd.NA

    # Parse Datetimes
    print("Parsing datetimes...")
    for c in DT_COLS_COMMON + DT_COLS_EMS_EXTRA:
        if c in ems_c.columns:
            ems_c[c] = parse_dt(ems_c[c])
    for c in DT_COLS_COMMON:
        if c in fire_c.columns:
            fire_c[c] = parse_dt(fire_c[c])

    # Clean Measures
    print("Cleaning measures...")
    for c in MEASURE_COLS_SHARED:
        if c in ems_c.columns:
            ems_c[c + "_CLEAN"] = clean_seconds(ems_c[c])
        if c in fire_c.columns:
            fire_c[c + "_CLEAN"] = clean_seconds(fire_c[c])
            
    return ems_c, fire_c

def build_dim_time(ems_c, fire_c, datetime_cols):
    print("Building Dim_Time...")
    dts = []
    for df in (ems_c, fire_c):
        for c in datetime_cols:
            if c in df.columns:
                dts.append(df[c])

    all_dt = (
        pd.concat(dts, ignore_index=True)
        .dropna()
        .dt.floor("D")
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    dim = pd.DataFrame({"date": all_dt})
    dim["date_key"] = (dim["date"].dt.year * 10000 + dim["date"].dt.month * 100 + dim["date"].dt.day).astype("int32")
    dim["year"] = dim["date"].dt.year.astype("int16")
    dim["month"] = dim["date"].dt.month.astype("int8")
    dim["day"] = dim["date"].dt.day.astype("int8")
    dim["day_of_week"] = dim["date"].dt.weekday + 1 # 1=Mon, 7=Sun
    dim["day_name"] = dim["date"].dt.day_name()
    dim["is_weekend"] = dim["day_of_week"].isin([6, 7]).astype("int8")
    dim["week"] = dim["date"].dt.isocalendar().week.astype("int16")
    dim["quarter"] = dim["date"].dt.quarter.astype("int8")
    dim["fiscal_year"] = get_fiscal_year(dim["date"]).astype("int16")
    dim["season"] = get_season(dim["date"])
    
    return dim

def build_dim_location(ems_c, fire_c, loc_cols=LOC_COLS):
    print("Building Dim_Location...")
    parts = []
    for df in (ems_c, fire_c):
        use = [c for c in loc_cols if c in df.columns]
        parts.append(df[use].copy())

    dim = pd.concat(parts, ignore_index=True).drop_duplicates()

    for c in dim.columns:
        if c != "BOROUGH_NORM":
            dim[c] = pd.to_numeric(dim[c], errors="coerce").astype("Int64")
        else:
            dim[c] = dim[c].astype("string")

    dim = dim.sort_values(dim.columns.tolist(), na_position="last").reset_index(drop=True)
    dim.insert(0, "location_key", (np.arange(len(dim)) + 1).astype("int32"))
    return dim

def build_dim_firehouse(firehouses):
    print("Building Dim_Firehouse...")
    fh = firehouses.copy()
    if "Borough" in fh.columns:
        fh["Borough_Norm"] = norm_borough(fh["Borough"])
    
    # Ensure Postcode is string for joining
    if "Postcode" in fh.columns:
         fh["Postcode"] = pd.to_numeric(fh["Postcode"], errors='coerce').astype("Int64")

    dim = fh.drop_duplicates().reset_index(drop=True)
    dim.insert(0, "firehouse_key", (np.arange(len(dim)) + 1).astype("int32"))
    return dim

def build_bridge_zip_firehouse(dim_firehouse):
    print("Building Bridge_Zip_Firehouse...")
    # This bridge links Zipcodes (from Incidents) to Firehouses.
    # Multiple firehouses can share a Zipcode.
    # Incidents in that zipcode will map to these firehouses.
    
    bridge = dim_firehouse[["firehouse_key", "Postcode", "Borough_Norm"]].dropna(subset=["Postcode"]).copy()
    bridge.rename(columns={"Postcode": "ZIPCODE", "Borough_Norm": "BOROUGH_NORM"}, inplace=True)
    
    # We want unique pairs of Firehouse -> Zip
    bridge = bridge.drop_duplicates().reset_index(drop=True)
    
    return bridge

def build_small_dims(ems_c, fire_c):
    print("Building Small Dims...")
    dims = {}

    def build_one(df, col, key_name):
        if col not in df.columns: return None
        dim = pd.DataFrame({col: norm_text(df[col])}).dropna().drop_duplicates().sort_values(col).reset_index(drop=True)
        dim.insert(0, key_name, (np.arange(len(dim)) + 1).astype("int32"))
        return dim

    # EMS Dims
    dims["dim_ems_initial_call_type"] = build_one(ems_c, "INITIAL_CALL_TYPE", "ems_initial_call_type_key")
    dims["dim_ems_final_call_type"] = build_one(ems_c, "FINAL_CALL_TYPE", "ems_final_call_type_key")
    dims["dim_ems_initial_severity"] = build_one(ems_c, "INITIAL_SEVERITY_LEVEL_CODE", "ems_initial_severity_key")
    dims["dim_ems_final_severity"] = build_one(ems_c, "FINAL_SEVERITY_LEVEL_CODE", "ems_final_severity_key")
    dims["dim_ems_disposition"] = build_one(ems_c, "INCIDENT_DISPOSITION_CODE", "ems_disposition_key")

    # Fire Dims
    dims["dim_fire_class_group"] = build_one(fire_c, "INCIDENT_CLASSIFICATION_GROUP", "fire_class_group_key")
    dims["dim_fire_class"] = build_one(fire_c, "INCIDENT_CLASSIFICATION", "fire_class_key")
    dims["dim_fire_alarm_source"] = build_one(fire_c, "ALARM_SOURCE_DESCRIPTION_TX", "fire_alarm_source_key")
    dims["dim_fire_alarm_level"] = build_one(fire_c, "ALARM_LEVEL_INDEX_DESCRIPTION", "fire_alarm_level_key")

    return {k: v for k, v in dims.items() if v is not None}

def attach_location_key(df, dim_location, loc_cols=LOC_COLS):
    use = [c for c in loc_cols if c in df.columns]
    left = df[use].copy()
    for c in left.columns:
        if c != "BOROUGH_NORM":
            left[c] = pd.to_numeric(left[c], errors="coerce").astype("Int64")
        else:
            left[c] = left[c].astype("string")
            
    right_cols = [c for c in loc_cols if c in dim_location.columns]
    right = dim_location[right_cols + ["location_key"]].copy()
    on_cols = [c for c in right_cols if c in left.columns]
    
    merged = left.merge(right, on=on_cols, how="left")
    return merged["location_key"]

def attach_dim_key(df, dim, col, key_col):
    if dim is None or col not in df.columns:
        return pd.Series(pd.array([pd.NA] * len(df), dtype="Int32"))
    tmp = pd.DataFrame({col: norm_text(df[col])})
    return tmp.merge(dim[[col, key_col]], on=col, how="left")[key_col].astype("Int32")

def build_fact_ems(ems_c, dim_location, dims_other):
    print("Building Fact_Incident_EMS...")
    fact = pd.DataFrame({
        "ems_incident_id": ems_c["CAD_INCIDENT_ID"].astype("int64"),
        "incident_datetime": ems_c["INCIDENT_DATETIME"],
        "incident_date_key": date_key_from_dt(ems_c["INCIDENT_DATETIME"]),
    })
    
    print("  Attaching Location Keys...")
    fact["location_key"] = attach_location_key(ems_c, dim_location)

    # Measures
    for c in MEASURE_COLS_SHARED:
        cc = c + "_CLEAN"
        if cc in ems_c.columns:
            fact[c.lower() + "_seconds"] = ems_c[cc]

    # Keys to small dims
    print("  Attaching Small Dim Keys...")
    fact["ems_initial_call_type_key"] = attach_dim_key(ems_c, dims_other.get("dim_ems_initial_call_type"), "INITIAL_CALL_TYPE", "ems_initial_call_type_key")
    fact["ems_final_call_type_key"] = attach_dim_key(ems_c, dims_other.get("dim_ems_final_call_type"), "FINAL_CALL_TYPE", "ems_final_call_type_key")
    fact["ems_initial_severity_key"] = attach_dim_key(ems_c, dims_other.get("dim_ems_initial_severity"), "INITIAL_SEVERITY_LEVEL_CODE", "ems_initial_severity_key")
    fact["ems_final_severity_key"] = attach_dim_key(ems_c, dims_other.get("dim_ems_final_severity"), "FINAL_SEVERITY_LEVEL_CODE", "ems_final_severity_key")
    fact["ems_disposition_key"] = attach_dim_key(ems_c, dims_other.get("dim_ems_disposition"), "INCIDENT_DISPOSITION_CODE", "ems_disposition_key")

    # Flags
    for flag in ["HELD_INDICATOR", "REOPEN_INDICATOR", "SPECIAL_EVENT_INDICATOR", "STANDBY_INDICATOR", "TRANSFER_INDICATOR"]:
        if flag in ems_c.columns:
            fact[flag.lower()] = norm_text(ems_c[flag]).replace({"TRUE": "1", "FALSE": "0", "Y": "1", "N": "0"}).astype("string")

    return fact

def build_fact_fire(fire_c, dim_location, dims_other):
    print("Building Fact_Incident_FIRE...")
    fact = pd.DataFrame({
        "fire_incident_id": fire_c["STARFIRE_INCIDENT_ID"].astype("string"),
        "incident_datetime": fire_c["INCIDENT_DATETIME"],
        "incident_date_key": date_key_from_dt(fire_c["INCIDENT_DATETIME"]),
    })

    print("  Attaching Location Keys...")
    fact["location_key"] = attach_location_key(fire_c, dim_location)

    # Measures
    for c in MEASURE_COLS_SHARED:
        cc = c + "_CLEAN"
        if cc in fire_c.columns:
            fact[c.lower() + "_seconds"] = fire_c[cc]

    for c in ["ENGINES_ASSIGNED_QUANTITY", "LADDERS_ASSIGNED_QUANTITY", "OTHER_UNITS_ASSIGNED_QUANTITY"]:
        if c in fire_c.columns:
            fact[c.lower()] = pd.to_numeric(fire_c[c], errors="coerce")

    # Keys to small dims
    print("  Attaching Small Dim Keys...")
    fact["fire_class_group_key"] = attach_dim_key(fire_c, dims_other.get("dim_fire_class_group"), "INCIDENT_CLASSIFICATION_GROUP", "fire_class_group_key")
    fact["fire_class_key"] = attach_dim_key(fire_c, dims_other.get("dim_fire_class"), "INCIDENT_CLASSIFICATION", "fire_class_key")
    fact["fire_alarm_source_key"] = attach_dim_key(fire_c, dims_other.get("dim_fire_alarm_source"), "ALARM_SOURCE_DESCRIPTION_TX", "fire_alarm_source_key")
    fact["fire_alarm_level_key"] = attach_dim_key(fire_c, dims_other.get("dim_fire_alarm_level"), "ALARM_LEVEL_INDEX_DESCRIPTION", "fire_alarm_level_key")

    # Degenerate attrs
    for c in ["ALARM_BOX_NUMBER", "ALARM_BOX_LOCATION", "ALARM_BOX_BOROUGH", "HIGHEST_ALARM_LEVEL"]:
        if c in fire_c.columns:
            fact[c.lower()] = fire_c[c]

    return fact

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    ems, fire, fire_stations = load_data()
    if ems is None: return

    # 2. Stage Data
    ems_c, fire_c = make_staging(ems, fire)

    # 3. Build Dimensions
    dim_time = build_dim_time(ems_c, fire_c, list(set(DT_COLS_COMMON + DT_COLS_EMS_EXTRA)))
    dim_location = build_dim_location(ems_c, fire_c)
    dim_firehouse = build_dim_firehouse(fire_stations)
    
    # 4. Build Bridge (Firehouse <-> Zip)
    bridge_zip_firehouse = build_bridge_zip_firehouse(dim_firehouse)
    
    # 5. Build Small Dims
    dims_other = build_small_dims(ems_c, fire_c)

    # 6. Build Facts
    fact_ems = build_fact_ems(ems_c, dim_location, dims_other)
    fact_fire = build_fact_fire(fire_c, dim_location, dims_other)

    # 7. Export to Parquet
    print("Exporting to Parquet...")
    
    tables = {
        "dim_time": dim_time,
        "dim_location": dim_location,
        "dim_firehouse": dim_firehouse,
        "bridge_zip_firehouse": bridge_zip_firehouse,
        "fact_incident_ems": fact_ems,
        "fact_incident_fire": fact_fire,
        **dims_other
    }

    for name, df in tables.items():
        print(f"  Saving {name}.parquet...")
        df.to_parquet(OUTPUT_DIR / f"{name}.parquet", index=False)
        
    print("Done! All files saved to powerbi_parquet/")

if __name__ == "__main__":
    main()
