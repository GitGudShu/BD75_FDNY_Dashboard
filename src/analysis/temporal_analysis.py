
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "temporal"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    """
    Loads temporal and weather datasets for analysis.
    
    This function reads parquet files for time, incident type, and weather dimensions, as well as 
    EMS and Fire incident facts. It adds a 'Source' column to distinguish between EMS and Fire data
    before returning them.
    
    Parameters:
        None
        
    Returns:
        tuple: A tuple containing:
            - dim_time (pd.DataFrame): Time dimension data.
            - dim_incident_type (pd.DataFrame): Incident type dimensions.
            - dim_weather (pd.DataFrame): Weather dimension data.
            - f_ems (pd.DataFrame): EMS incident facts.
            - f_fire (pd.DataFrame): Fire incident facts.
    """
    print("Loading data...")
    dim_time = pd.read_parquet(DATA_DIR / "Dim_Time.parquet")
    dim_incident_type = pd.read_parquet(DATA_DIR / "Dim_IncidentType.parquet")
    dim_weather = pd.read_parquet(DATA_DIR / "Dim_Weather.parquet")
    
    cols_ems = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time"]
    cols_fire = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time"]
    
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    
    f_ems["Source"] = "EMS"
    f_fire["Source"] = "Fire"
    
    return dim_time, dim_incident_type, dim_weather, f_ems, f_fire

def analyze_gridlock(combined):
    """
    Analyzes the relationship between time of day, incident volume, and traffic speed.
    
    This method aggregates data by hour of the day to compare total incident volume against
    average travel time. It generates a dual-axis chart with bars for volume and a line for 
    travel time, highlighting "Gridlock" conditions where high volume meets slow travel speeds.
    
    Parameters:
        combined (pd.DataFrame): Combined EMS and Fire incident data.
        
    Returns:
        None: Saves the generated figure 'gridlock_analysis.png' to the output directory.
    """
    print("Running Gridlock Analysis (Volume vs Speed)...")
    
    agg = combined.groupby("hour").agg({
        "nb_interventions": "sum",
        "travel_time": "mean"
    }).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(12, 6))

    sns.barplot(data=agg, x="hour", y="nb_interventions", color="lightblue", alpha=0.6, ax=ax1, label="Incident Volume")
    ax1.set_ylabel("Total Incidents")
    ax1.set_xlabel("Hour of Day")
    
    ax2 = ax1.twinx()
    sns.lineplot(data=agg, x="hour", y="travel_time", color="red", marker="o", linewidth=2.5, ax=ax2, label="Avg Travel Time")
    ax2.set_ylabel("Travel Time (Seconds)")
    
    ax1.grid(axis='x')
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")
    
    plt.title("The Gridlock: Incident Volume vs Travel Time")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "gridlock_analysis.png")
    plt.close()

def analyze_risk_heatmap(combined, dim_type):
    """
    Creates a heatmap showing incident intensity by hour and category.
    
    This function joins incident data with type dimensions to categorize incidents. It creates a
    pivot table of the top 10 incident categories by volume against the hour of the day. The
    resulting heatmap visualizes when specific types of risks are most prevalent.
    
    Parameters:
        combined (pd.DataFrame): Combined EMS and Fire incident data.
        dim_type (pd.DataFrame): Incident type dimension data.
        
    Returns:
        None: Saves the generated figure 'risk_heatmap.png' to the output directory.
    """
    print("Running Risk Heatmap...")
    
    merged = combined.merge(dim_type, on="incident_type_key")
    
    top_cats = merged["category"].value_counts().nlargest(10).index.tolist()
    
    filtered = merged[merged["category"].isin(top_cats)]
    
    pivot = filtered.pivot_table(index="hour", columns="category", values="nb_interventions", aggfunc="sum", fill_value=0)
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot, cmap="inferno", annot=False, fmt="d", linewidths=.5)
    plt.title("Risk Heatmap: Incident Intensity by Hour & Type")
    plt.ylabel("Hour of Day")
    plt.xlabel("Incident Category")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "risk_heatmap.png")
    plt.close()

def analyze_shift_change(combined):
    """
    Investigates performance vulnerabilities during shift changes.
    
    This analysis tracks average dispatch time by hour, specifically marking typical shift change
    times (09:00 and 18:00). It aims to identify any spikes in delay that correlate with the 
    handover between shifts.
    
    Parameters:
        combined (pd.DataFrame): Combined EMS and Fire incident data.
        
    Returns:
        None: Saves the generated figure 'shift_change.png' to the output directory.
    """
    print("Running Shift Change Analysis...")
    
    agg = combined.groupby("hour")["dispatch_time"].mean().reset_index()
    
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=agg, x="hour", y="dispatch_time", marker="o", color="purple", linewidth=2)
    
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
    """
    Analyzes the impact of temperature on incident volume.
    
    This function groups temperature data into 5-degree buckets and sums the number of incidents
    within each bucket. A regression plot is generated to visualize the correlation between 
    temperature and incident frequency.
    
    Parameters:
        combined (pd.DataFrame): Combined EMS and Fire incident data.
        dim_weather (pd.DataFrame): Weather dimension data.
        
    Returns:
        None: Saves the generated figure 'weather_volume.png' to the output directory.
    """
    print("Running Weather Analysis...")
    
    merged = combined.merge(dim_weather, on="weather_key")
    
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
    """
    Main entry point for the temporal analysis script.
    
    Orchestrates the loading of data and execution of four primary analyses:
    Gridlock (Volume vs Speed), Risk Heatmap (Time vs Type), Shift Change Vulnerability, 
    and Weather Impact. It combines EMS and Fire data for a holistic view.
    """
    if not os.path.exists(DATA_DIR / "Dim_Weather.parquet"):
        print("Data not ready. Ensure ETL has run with weather.")
        return

    dim_time, dim_type, dim_weather, f_ems, f_fire = load_data()
    
    common_cols = ["date_key", "hour", "nb_interventions", "incident_type_key", "weather_key", "travel_time", "dispatch_time", "Source"]
    combined = pd.concat([f_ems[common_cols], f_fire[common_cols]])
    
    analyze_gridlock(combined)
    analyze_risk_heatmap(combined, dim_type)
    analyze_shift_change(combined)
    analyze_weather(combined, dim_weather)
    
    print("V2 Analysis Complete. Figures in", OUTPUT_FIG)

if __name__ == "__main__":
    main()
