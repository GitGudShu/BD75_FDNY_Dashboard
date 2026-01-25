
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "operational"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    print("Loading data...")
    dim_incident_type = pd.read_parquet(DATA_DIR / "Dim_IncidentType.parquet")
    
    # Load Facts
    # Need: dispatch_time, travel_time, units columns, date/hour
    # Fire typically has unit counts. EMS might just be incident counts.
    
    cols_fire = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time", 
                 "engines_assigned_quantity", "ladders_assigned_quantity", "other_units_assigned_quantity"]
    
    cols_ems = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time"]
    
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    
    f_fire["Source"] = "Fire"
    f_ems["Source"] = "EMS"
    
    # Calc Total Units for Fire
    # Fillna 0 just in case
    f_fire["total_units"] = (f_fire["engines_assigned_quantity"].fillna(0) + 
                             f_fire["ladders_assigned_quantity"].fillna(0) + 
                             f_fire["other_units_assigned_quantity"].fillna(0))
    
    # For EMS, we assume 1 unit per incident if mostly 1-1 mapping, 
    # but strictly we don't have vehicle count in basic EMS data usually.
    # We will focus "Heavy Lifting" (Resource Matching) on FIRE where we have explicit unit counts.
    # We will include EMS in "Anatomy of Delay" (Time).
    
    return dim_incident_type, f_fire, f_ems

def analyze_anatomy_of_delay(f_fire, f_ems):
    print("Running Anatomy of Delay...")
    
    combined = pd.concat([f_fire[["hour", "dispatch_time", "travel_time", "Source"]], 
                          f_ems[["hour", "dispatch_time", "travel_time", "Source"]]])
    
    # Filter reasonable times (e.g. < 3600s) to remove outliers affecting mean
    combined = combined[(combined["dispatch_time"] < 1200) & (combined["travel_time"] < 3600)]
    
    # Agg by Hour
    agg = combined.groupby("hour").agg({
        "dispatch_time": "mean",
        "travel_time": "mean"
    }).reset_index()
    
    # Stacked Bar Plot
    plt.figure(figsize=(10, 6))
    
    # Bottom bar = Dispatch
    plt.bar(agg["hour"], agg["dispatch_time"], label="Dispatch (Process)", color="#9b59b6")
    
    # Top bar = Travel (stacked on dispatch)
    plt.bar(agg["hour"], agg["travel_time"], bottom=agg["dispatch_time"], label="Travel (Traffic)", color="#34495e")
    
    plt.title("Anatomy of Delay: Dispatch vs Travel Time by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("Time (Seconds)")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "anatomy_of_delay.png")
    plt.close()

def analyze_resource_matching(f_fire, dim_incident_type):
    print("Running Heavy Lifting (Resource Matching)...")
    
    # Join Fire facts with Type to get Category/Severity
    # We need 'incident_type_desc' or 'category'
    merged = f_fire.merge(dim_incident_type, on="incident_type_key")
    
    # Box plot of Total Units by Category
    # Filter to top 5-10 categories to keep it readable
    top_cats = merged["category"].value_counts().nlargest(8).index.tolist()
    filtered = merged[merged["category"].isin(top_cats)]
    
    # Remove outliers for plot clarity (e.g. > 20 units)
    filtered = filtered[filtered["total_units"] <= 20]
    
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=filtered, x="category", y="total_units", palette="Set2")
    
    plt.title("The Heavy Lifting: Units Assigned by Incident Category")
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Total Units Assigned")
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "resource_matching.png")
    plt.close()

def analyze_saturation_point(f_fire, f_ems):
    print("Running Saturation Point Analysis...")
    
    # We want to see if High System Load -> Slower Dispatch
    # Metric: Hourly Total Incidents (or Units) vs Avg Dispatch Time
    
    # 1. Aggregate Fire (since we have units)
    # Group by Date+Hour
    fire_agg = f_fire.groupby(["date_key", "hour"]).agg({
        "total_units": "sum",
        "dispatch_time": "mean"
    }).reset_index()
    
    # 2. Aggregate EMS (Volume)
    ems_agg = f_ems.groupby(["date_key", "hour"]).agg({
        "incident_type_key": "count", # Volume proxy
        "dispatch_time": "mean"
    }).rename(columns={"incident_type_key": "ems_volume"}).reset_index()
    
    # Let's focus on FIRE Saturation first as "Units" is clear constraint
    # Plot: X=Total Units Deployed in that Hour, Y=Avg Dispatch Time
    
    # Filter outliers
    fire_agg = fire_agg[fire_agg["dispatch_time"] < 300] # Cap at 5 min avg to ignore catastrophes
    
    plt.figure(figsize=(10, 6))
    # Scatter with regression
    # Alpha low to show density
    sns.regplot(data=fire_agg, x="total_units", y="dispatch_time", scatter_kws={'alpha': 0.1, 'color': 'orange'}, line_kws={'color': 'red'})
    
    plt.title("Saturation Point: Fire Unit Load vs Dispatch Speed")
    plt.xlabel("Total Units Deployed (Hourly Sum)")
    plt.ylabel("Avg Dispatch Time (Seconds)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "saturation_point.png")
    plt.close()

def main():
    try:
        dim_incident_type, f_fire, f_ems = load_data()
        
        analyze_anatomy_of_delay(f_fire, f_ems)
        analyze_resource_matching(f_fire, dim_incident_type)
        analyze_saturation_point(f_fire, f_ems)
        
        print("Operational Analysis Complete. Figures in", OUTPUT_FIG)
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
