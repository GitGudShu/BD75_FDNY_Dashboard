
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "temporal"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    print("Loading data...")
    dim_time = pd.read_parquet(DATA_DIR / "Dim_Time.parquet")
    dim_incident_type = pd.read_parquet(DATA_DIR / "Dim_IncidentType.parquet")
    dim_weather = pd.read_parquet(DATA_DIR / "Dim_Weather.parquet")
    
    # Load Facts (Calculated Columns needed: count, travel_time, dispatch_time, weather_key)
    cols_ems = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time"]
    cols_fire = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time"]
    
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    
    # Add Type Label
    f_ems["Source"] = "EMS"
    f_fire["Source"] = "Fire"
    
    return dim_time, dim_incident_type, dim_weather, f_ems, f_fire

def analyze_gridlock(combined):
    print("Running Gridlock Analysis (Volume vs Speed)...")
    
    # Group by Hour
    # Volume: Sum nb_interventions
    # Speed: Mean travel_time
    agg = combined.groupby("hour").agg({
        "nb_interventions": "sum",
        "travel_time": "mean"
    }).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Bar (Volume)
    sns.barplot(data=agg, x="hour", y="nb_interventions", color="lightblue", alpha=0.6, ax=ax1, label="Incident Volume")
    ax1.set_ylabel("Total Incidents")
    ax1.set_xlabel("Hour of Day")
    
    # Line (Speed)
    ax2 = ax1.twinx()
    sns.lineplot(data=agg, x="hour", y="travel_time", color="red", marker="o", linewidth=2.5, ax=ax2, label="Avg Travel Time")
    ax2.set_ylabel("Travel Time (Seconds)")
    
    # Grid & Legend
    ax1.grid(axis='x')
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")
    
    plt.title("The Gridlock: Incident Volume vs Travel Time")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "gridlock_analysis.png")
    plt.close()

def analyze_risk_heatmap(combined, dim_type):
    print("Running Risk Heatmap...")
    
    # Join with Type Dim
    # We use 'category' if available, or 'incident_type_desc'
    # ETL built Dim_IncidentType with 'category'
    merged = combined.merge(dim_type, on="incident_type_key")
    
    # Pivot: Index=Hour, Col=Category (Top 10?), Value=Count
    # EMS and Fire categories might be different. Let's do one shared heatmap or valid categories.
    
    # Focus on major categories to avoid sparse matrix
    # Get top 8 categories by volume
    top_cats = merged["category"].value_counts().nlargest(10).index.tolist()
    
    filtered = merged[merged["category"].isin(top_cats)]
    
    pivot = filtered.pivot_table(index="hour", columns="category", values="nb_interventions", aggfunc="sum", fill_value=0)
    
    # Normalize by column (share of day) or raw count? Raw count shows peak times.
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot, cmap="inferno", annot=False, fmt="d", linewidths=.5)
    plt.title("Risk Heatmap: Incident Intensity by Hour & Type")
    plt.ylabel("Hour of Day")
    plt.xlabel("Incident Category")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "risk_heatmap.png")
    plt.close()

def analyze_shift_change(combined):
    print("Running Shift Change Analysis...")
    
    # Group by Hour, Mean Dispatch Time
    agg = combined.groupby("hour")["dispatch_time"].mean().reset_index()
    
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=agg, x="hour", y="dispatch_time", marker="o", color="purple", linewidth=2)
    
    # Highlight Shift Changes (09:00, 18:00 typical)
    plt.axvline(9, color="orange", linestyle="--", label="Shift Change (9 AM)")
    plt.axvline(18, color="green", linestyle="--", label="Shift Change (6 PM)")
    
    plt.title("Shift Change Vulnerability: Dispatch Time by Hour")
    plt.ylabel("Avg Dispatch Time (Seconds)")
    plt.xlabel("Hour of Day")
    plt.xticks(range(0, 24))
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "shift_change.png")
    plt.close()

def analyze_weather(combined, dim_weather):
    print("Running Weather Analysis...")
    
    # Join with Weather
    # Weather Key was added to Fact.
    merged = combined.merge(dim_weather, on="weather_key")
    
    # Aggregate Volume by Temp buckets
    # Create temp bins
    merged["temp_bin"] = pd.cut(merged["temp_f"], bins=range(0, 110, 5))
    
    agg = merged.groupby("temp_bin")["nb_interventions"].sum().reset_index()
    agg["temp_mid"] = agg["temp_bin"].apply(lambda x: x.mid)
    
    plt.figure(figsize=(10, 6))
    sns.regplot(data=agg, x="temp_mid", y="nb_interventions", scatter_kws={'s': 50}, line_kws={'color': 'red'})
    
    plt.title("Weather Impact: Temperature vs Incident Volume")
    plt.xlabel("Temperature (°F)")
    plt.ylabel("Total Incidents")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "weather_volume.png")
    plt.close()

def main():
    if not os.path.exists(DATA_DIR / "Dim_Weather.parquet"):
        print("Data not ready. Ensure ETL has run with weather.")
        return

    dim_time, dim_type, dim_weather, f_ems, f_fire = load_data()
    
    # Combine Facts for global analysis
    # Ensure columns match
    common_cols = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time", "Source"]
    combined = pd.concat([f_ems[common_cols], f_fire[common_cols]])
    
    analyze_gridlock(combined)
    analyze_risk_heatmap(combined, dim_type)
    analyze_shift_change(combined)
    analyze_weather(combined, dim_weather)
    
    print("V2 Analysis Complete. Figures in", OUTPUT_FIG)

if __name__ == "__main__":
    main()
