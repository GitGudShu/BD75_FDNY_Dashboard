
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "geographic"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    print("Loading data...")
    dim_location = pd.read_parquet(DATA_DIR / "Dim_Location.parquet")
    dim_firehouse = pd.read_parquet(DATA_DIR / "Dim_Firehouse.parquet")
    
    # Load Facts
    # Need: location_key, dispatch_time, travel_time
    cols_ems = ["location_key", "nb_interventions", "dispatch_time", "travel_time"]
    cols_fire = ["location_key", "nb_interventions", "dispatch_time", "travel_time"] 
    # Fire might not have dispatch/travel populated in ETL?
    # Checked ETL: Fire uses 'DISPATCH_RESPONSE_SECONDS_QY' -> 'dispatch_time' logic map.
    
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    
    f_ems["Source"] = "EMS"
    f_fire["Source"] = "Fire"
    
    return dim_location, dim_firehouse, f_ems, f_fire

def analyze_borough_performance(combined, dim_location):
    print("Analyzing Borough Performance...")
    
    merged = combined.merge(dim_location, left_on="location_key", right_on="location_key", how="left")
    
    # Aggregate
    agg = merged.groupby(["borough", "Source"]).agg({
        "nb_interventions": "sum",
        "dispatch_time": "mean",
        "travel_time": "mean"
    }).reset_index()
    
    # 1. Volume by Borough
    plt.figure(figsize=(10, 6))
    sns.barplot(data=agg, x="borough", y="nb_interventions", hue="Source")
    plt.title("Total Incidents by Borough")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "borough_volume.png")
    plt.close()
    
    # 2. Travel Time by Borough
    plt.figure(figsize=(10, 6))
    sns.barplot(data=agg, x="borough", y="travel_time", hue="Source")
    plt.title("Avg Travel Time by Borough")
    plt.ylabel("Seconds")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "borough_travel_time.png")
    plt.close()

def analyze_zipcode_hotspots(combined, dim_location):
    print("Analyzing Zipcode Hotspots...")
    
    merged = combined.merge(dim_location, left_on="location_key", right_on="location_key", how="left")
    
    # Top 20 Busiest Zipcodes
    agg = merged.groupby("zipcode")["nb_interventions"].sum().reset_index()
    top_20 = agg.nlargest(20, "nb_interventions")
    
    # Map back to Borough for color
    # Dim Location has unique zip-borough pairs usually, or duplicates. 
    # Let's drop dupes for coloring
    zip_boro = dim_location[["zipcode", "borough"]].drop_duplicates("zipcode")
    top_20 = top_20.merge(zip_boro, on="zipcode", how="left")
    
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_20, x="zipcode", y="nb_interventions", hue="borough", dodge=False)
    plt.title("Top 20 Busiest Zipcodes")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "zipcode_hotspots.png")
    plt.close()

def analyze_firehouse_map(dim_firehouse):
    print("Plotting Firehouse Locations...")
    
    # Just a scatter plot of lat/lon
    # Ideally size by volume, but connecting Fact_Fire to Dim_Firehouse is tricky.
    # The Galaxy schema links Fact -> Dim_Location (Zip/Boro).
    # It does NOT link Fact -> Dim_Firehouse directly (no 'firehouse_id' in raw data easily).
    # So we visualize static locations.
    
    plt.figure(figsize=(10, 10))
    sns.scatterplot(data=dim_firehouse, x="Longitude", y="Latitude", hue="borough", style="borough", s=50)
    plt.title("Firehouse Locations")
    plt.axis("equal") # Preserve map aspect ratio
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "firehouse_map.png")
    plt.close()

def main():
    dim_location, dim_firehouse, f_ems, f_fire = load_data()
    
    combined = pd.concat([f_ems, f_fire])
    
    analyze_borough_performance(combined, dim_location)
    analyze_zipcode_hotspots(combined, dim_location)
    analyze_firehouse_map(dim_firehouse)
    
    print("Geographic Analysis Complete. Figures in", OUTPUT_FIG)

if __name__ == "__main__":
    main()
