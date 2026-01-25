
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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
    # dimensions
    dim_time = pd.read_parquet(DATA_DIR / "Dim_Time.parquet")
    
    # facts (only load necessary columns)
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=["date_key", "nb_interventions", "hour"])
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=["date_key", "nb_interventions", "hour"])
    
    return dim_time, f_ems, f_fire

def analyze_and_plot(dim_time, f_ems, f_fire):
    print("Analyzing...")
    
    # Group by Date Key first to reduce size
    ems_daily = f_ems.groupby("date_key")["nb_interventions"].sum().reset_index()
    fire_daily = f_fire.groupby("date_key")["nb_interventions"].sum().reset_index()
    
    # Join with Time Dim
    ems_daily = ems_daily.merge(dim_time, on="date_key")
    fire_daily = fire_daily.merge(dim_time, on="date_key")
    
    # Add Source column
    ems_daily["Type"] = "EMS"
    fire_daily["Type"] = "Fire"
    
    combined = pd.concat([ems_daily, fire_daily])
    
    # 1. Yearly Trend
    print("Plotting Yearly Trend...")
    yearly = combined.groupby(["year", "Type"])["nb_interventions"].sum().reset_index()
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=yearly, x="year", y="nb_interventions", hue="Type", marker="o")
    plt.title("Total Incidents per Year")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.savefig(OUTPUT_FIG / "yearly_trend.png")
    plt.close()
    
    # 2. Monthly Seasonality (Average per month to normalize for incomplete years)
    print("Plotting Monthly Seasonality...")
    monthly = combined.groupby(["month", "Type"])["nb_interventions"].mean().reset_index()
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=monthly, x="month", y="nb_interventions", hue="Type", marker="o")
    plt.title("Average Incidents per Month (Seasonality)")
    plt.xticks(range(1, 13))
    plt.grid(True)
    plt.savefig(OUTPUT_FIG / "monthly_seasonality.png")
    plt.close()
    
    # 3. Day of Week
    print("Plotting Weekly Pattern...")
    daily_avg = combined.groupby(["day_name", "day_of_week", "Type"])["nb_interventions"].mean().reset_index()
    # Sort by day_of_week
    daily_avg = daily_avg.sort_values("day_of_week")
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=daily_avg, x="day_name", y="nb_interventions", hue="Type")
    plt.title("Average Daily Incidents by Day of Week")
    plt.grid(axis='y')
    plt.savefig(OUTPUT_FIG / "weekly_pattern.png")
    plt.close()
    
    # 4. Hourly Pattern
    print("Plotting Hourly Pattern...")
    # Aggregate from raw frames
    ems_h = f_ems.groupby("hour")["nb_interventions"].sum().reset_index()
    fire_h = f_fire.groupby("hour")["nb_interventions"].sum().reset_index()
    ems_h["Type"] = "EMS"
    fire_h["Type"] = "Fire"
    hourly_combined = pd.concat([ems_h, fire_h])
    
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=hourly_combined, x="hour", y="nb_interventions", hue="Type", marker="o")
    plt.title("Total Incidents by Hour of Day (All Years)")
    plt.xticks(range(0, 24))
    plt.grid(True)
    plt.savefig(OUTPUT_FIG / "hourly_pattern.png")
    plt.close()
    
    print("Analysis complete. Figures saved in", OUTPUT_FIG)
    
    return

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        print("Data processed directory not found.", DATA_DIR)
    else:
        dim_time, f_ems, f_fire = load_data()
        analyze_and_plot(dim_time, f_ems, f_fire)
