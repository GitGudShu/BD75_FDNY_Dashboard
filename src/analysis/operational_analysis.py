import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
import os
from pathlib import Path

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "operational" # Updated folder name
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

# Set global style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150

def load_data():
    print("Loading data...")
    dim_incident_type = pd.read_parquet(DATA_DIR / "Dim_IncidentType.parquet")
    
    cols_fire = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time", 
                 "engines_assigned_quantity", "other_units_assigned_quantity", "ladders_assigned_quantity", "total_units"]
    
    # Load EMS with new columns
    cols_ems = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time", "initial_call_type", "final_call_type"]
    
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    
    # Calculate Total Units for Fire (Main resource drain)
    # f_fire["total_units"] is now pre-calculated in ETL
    
    return dim_incident_type, f_fire, f_ems

def analyze_reality_gap_sankey(f_ems):
    print("Running Reality Gap (Sankey) - MISCLASSIFICATIONS ONLY...")
    
    try:
        # 1. Filter: Keep ONLY rows where the Initial type DOES NOT MATCH the Final type
        # Drop missing values
        clean_ems = f_ems.dropna(subset=["initial_call_type", "final_call_type"])
        mismatches = clean_ems[clean_ems["initial_call_type"] != clean_ems["final_call_type"]].copy()
        
        if mismatches.empty:
            print("No mismatches found. Check data.")
            return

        # 2. Group & Count the Mismatches
        flow = mismatches.groupby(["initial_call_type", "final_call_type"]).size().reset_index(name="value")
        
        # 3. Filter Top 20 Mismatches (Now these are the "Top Errors")
        flow = flow.sort_values("value", ascending=False).head(20)
        
        # 4. Add suffixes to ensure distinct nodes (Left vs Right)
        flow['source_label'] = flow['initial_call_type'] + " (Dispatched As)"
        flow['target_label'] = flow['final_call_type'] + " (Actually Was)"
        
        # 5. Create Node Map
        all_nodes = list(pd.concat([flow['source_label'], flow['target_label']]).unique())
        node_map = {name: i for i, name in enumerate(all_nodes)}
        
        source_indices = flow['source_label'].map(node_map)
        target_indices = flow['target_label'].map(node_map)
        values = flow['value']
        
        # 6. Plot
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20,
                thickness=30,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                # color="blue" # Removed to allow default palette
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                # color='rgba(231, 76, 60, 0.4)' # Removed to allow default palette (or grey)
            )
        )])
        
        fig.update_layout(
            title_text="The Reality Gap: Top 20 Dispatch Misclassifications", 
            font_size=12,
            height=700
        )
        fig.write_image(OUTPUT_FIG / "reality_gap_sankey_errors.png")
        print("Sankey (Errors Only) generated successfully.")
        
    except Exception as e:
        print(f"Sankey failed: {e}")

def analyze_stress_test_binned(f_fire):
    """
    IMPROVEMENT: Uses Binning instead of Scatter plot.
    Groups hourly data into buckets of 20 units to show the clear trend line.
    """
    print("Running Stress Test (Binned Analysis)...")
    
    # 1. Agg: Hourly Total Units vs Avg Dispatch Time
    agg = f_fire.groupby(["date_key", "hour"]).agg({
        "total_units": "sum",
        "dispatch_time": "mean"
    }).reset_index()
    
    # Filter valid
    agg = agg[(agg["dispatch_time"] < 600) & (agg["total_units"] > 0)]
    
    # 2. THE FIX: Create Bins
    # We bin the "Total Units" (Load) into buckets of 20 units (0-20, 20-40, etc.)
    # This removes noise and shows the structural limit of the system.
    bins = range(0, int(agg["total_units"].max()) + 20, 20)
    agg["load_bin"] = pd.cut(agg["total_units"], bins=bins)
    
    # Calculate mean dispatch time per bin
    binned_data = agg.groupby("load_bin", observed=True)["dispatch_time"].mean().reset_index()
    
    # Convert bin intervals to string or mid-point for plotting
    binned_data["bin_mid"] = binned_data["load_bin"].apply(lambda x: x.mid)
    
    plt.figure(figsize=(12, 7))
    
    # Plot Line Chart
    sns.lineplot(data=binned_data, x="bin_mid", y="dispatch_time", marker="o", linewidth=2.5, color="#e74c3c")
    
    # Add a threshold line (optional, purely visual based on observation)
    # plt.axvline(x=300, color='grey', linestyle='--', alpha=0.5, label="Potential Saturation Point")

    plt.title("The Stress Test: System Saturation Curve", fontsize=14)
    plt.xlabel("Total Units Deployed (Hourly System Load)", fontsize=12)
    plt.ylabel("Avg Dispatch Time (Seconds)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)
    
    # Annotation
    plt.text(binned_data["bin_mid"].iloc[-1], binned_data["dispatch_time"].iloc[-1] + 2, 
             "Performance degrades\nunder load", color="#e74c3c", fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "stress_test_binned.png")
    plt.close()

def analyze_resource_consumption(f_fire, dim_incident_type):
    """
    NEW CHART: Replaces 'Anatomy of Delay'.
    Calculates Total Resource Cost (Units * Duration) per Incident Type.
    """
    print("Running Resource Consumption Analysis...")
    
    # 1. Merge to get descriptions
    # Note: Ensure your dim_incident_type has 'incident_type_desc' or similar
    merged = f_fire.merge(dim_incident_type, on="incident_type_key")
    
    # 2. Calculate Resource Cost
    # Cost = Units Assigned * (Dispatch Time + Travel Time)
    # This represents "Active System Seconds" consumed.
    merged["active_duration"] = merged["dispatch_time"].fillna(0) + merged["travel_time"].fillna(0)
    merged["resource_cost_seconds"] = merged["total_units"] * merged["active_duration"]
    
    # 3. Agg by Type
    summary = merged.groupby("category")["resource_cost_seconds"].sum().reset_index()
    
    # Convert to Hours for readability
    summary["resource_hours"] = summary["resource_cost_seconds"] / 3600
    
    # Get Top 10 Consumers
    top_consumers = summary.sort_values("resource_hours", ascending=False).head(10)
    
    plt.figure(figsize=(12, 6))
    
    # Horizontal Bar Chart
    sns.barplot(data=top_consumers, x="resource_hours", y="category", palette="viridis", hue="category", legend=False)
    
    plt.title("The Resource Hog: Total Operational Capacity Consumed by Incident Type", fontsize=14)
    plt.xlabel("Total Unit-Hours Consumed (Units * Duration)", fontsize=12)
    plt.ylabel("")
    
    # Add value labels
    for i, v in enumerate(top_consumers["resource_hours"]):
        plt.text(v + (v*0.01), i, f"{int(v):,}", va='center', fontsize=10)
        
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "resource_consumption_bar.png")
    plt.close()

def main():
    try:
        dim_incident_type, f_fire, f_ems = load_data()
        
        analyze_reality_gap_sankey(f_ems)
        analyze_stress_test_binned(f_fire)
        analyze_resource_consumption(f_fire, dim_incident_type)
        
        print(f"Operational V3 Analysis Complete. Figures saved in: {OUTPUT_FIG}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()