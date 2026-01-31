import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "operational"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150

def load_data():
    """
    Loads operational datasets required for analysis.
    
    This function reads parquet files to load incident type dimensions, and both Fire and EMS incident facts.
    It selects specific columns relevant to operational analysis such as dispatch time, travel time,
    and unit assignments.
        
    Returns:
        tuple: A tuple containing:
            - dim_incident_type (pd.DataFrame): Incident type dimensions.
            - f_fire (pd.DataFrame): Fire incident facts with resource usage data.
            - f_ems (pd.DataFrame): EMS incident facts with call type classifications.
    """
    print("Loading data...")
    dim_incident_type = pd.read_parquet(DATA_DIR / "Dim_IncidentType.parquet")
    
    cols_fire = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time", 
                 "engines_assigned_quantity", "other_units_assigned_quantity", "ladders_assigned_quantity", "total_units"]
    
    cols_ems = ["date_key", "hour", "incident_type_key", "dispatch_time", "travel_time", "initial_call_type", "final_call_type"]
    
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols_fire)
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols_ems)
    
    return dim_incident_type, f_fire, f_ems

def analyze_reality_gap_sankey(f_ems):
    """
    Generates a Sankey diagram visualizing dispatch misclassifications.
    
    The analysis tracks the 'Reality Gap' by comparing the initial call type (how it was dispatched) 
    versus the final call type (what it actually was). It filters for instances where these do not match, 
    identifying the top 20 most frequent misclassifications.
    
    Parameters:
        f_ems (pd.DataFrame): EMS incident data containing 'initial_call_type' and 'final_call_type'.
        
    Returns:
        None: Saves the generated figure 'reality_gap_sankey_errors.png' to the output directory.
    """
    print("Running Reality Gap (Sankey) - MISCLASSIFICATIONS ONLY...")
    
    try:
        clean_ems = f_ems.dropna(subset=["initial_call_type", "final_call_type"])
        mismatches = clean_ems[clean_ems["initial_call_type"] != clean_ems["final_call_type"]].copy()
        
        if mismatches.empty:
            print("No mismatches found. Check data.")
            return

        flow = mismatches.groupby(["initial_call_type", "final_call_type"]).size().reset_index(name="value")
        
        flow = flow.sort_values("value", ascending=False).head(20)
        
        flow['source_label'] = flow['initial_call_type'] + " (Dispatched As)"
        flow['target_label'] = flow['final_call_type'] + " (Actually Was)"
        
        all_nodes = list(pd.concat([flow['source_label'], flow['target_label']]).unique())
        node_map = {name: i for i, name in enumerate(all_nodes)}
        
        source_indices = flow['source_label'].map(node_map)
        target_indices = flow['target_label'].map(node_map)
        values = flow['value']
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20,
                thickness=30,
                line=dict(color="black", width=0.5),
                label=all_nodes,
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
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
    Analyzes system performance under load using binned aggregation.
    
    This method performs a 'stress test' by grouping hourly data into bins based on total units deployed 
    (system load). It then calculates the average dispatch time for each load bin to reveal how 
    performance degrades as the system approaches saturation.
    
    Parameters:
        f_fire (pd.DataFrame): Fire incident data containing 'total_units' and 'dispatch_time'.
        
    Returns:
        None: Saves the generated figure 'stress_test_binned.png' to the output directory.
    """
    print("Running Stress Test (Binned Analysis)...")
    
    agg = f_fire.groupby(["date_key", "hour"]).agg({
        "total_units": "sum",
        "dispatch_time": "mean"
    }).reset_index()
    
    agg = agg[(agg["dispatch_time"] < 600) & (agg["total_units"] > 0)]
    
    bins = range(0, int(agg["total_units"].max()) + 20, 20)
    agg["load_bin"] = pd.cut(agg["total_units"], bins=bins)
    
    binned_data = agg.groupby("load_bin", observed=True)["dispatch_time"].mean().reset_index()
    
    binned_data["bin_mid"] = binned_data["load_bin"].apply(lambda x: x.mid)
    
    plt.figure(figsize=(12, 7))
    
    sns.lineplot(data=binned_data, x="bin_mid", y="dispatch_time", marker="o", linewidth=2.5, color="#e74c3c")
    
    plt.title("The Stress Test: System Saturation Curve", fontsize=14)
    plt.xlabel("Total Units Deployed (Hourly System Load)", fontsize=12)
    plt.ylabel("Avg Dispatch Time (Seconds)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)
    
    plt.text(binned_data["bin_mid"].iloc[-1], binned_data["dispatch_time"].iloc[-1] + 2, 
             "Performance degrades\nunder load", color="#e74c3c", fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "stress_test_binned.png")
    plt.close()

def analyze_resource_consumption(f_fire, dim_incident_type):
    """
    Identifies the most resource-intensive incident types.
    
    This function calculates the total "Active System Seconds" consumed by each incident type.
    The cost is derived from the number of units assigned multiplied by the active duration 
    (dispatch + travel time). It produces a bar chart of the top 10 resource-consuming incident types.
    
    Parameters:
        f_fire (pd.DataFrame): Fire incident data.
        dim_incident_type (pd.DataFrame): Incident type dimension data.
        
    Returns:
        None: Saves the generated figure 'resource_consumption_bar.png' to the output directory.
    """
    print("Running Resource Consumption Analysis...")
    
    merged = f_fire.merge(dim_incident_type, on="incident_type_key")
    
    merged["active_duration"] = merged["dispatch_time"].fillna(0) + merged["travel_time"].fillna(0)
    merged["resource_cost_seconds"] = merged["total_units"] * merged["active_duration"]

    summary = merged.groupby("category")["resource_cost_seconds"].sum().reset_index()
    summary["resource_hours"] = summary["resource_cost_seconds"] / 3600
    
    top_consumers = summary.sort_values("resource_hours", ascending=False).head(10)
    plt.figure(figsize=(12, 6))
    sns.barplot(data=top_consumers, x="resource_hours", y="category", palette="viridis", hue="category", legend=False)
    
    plt.title("The Resource Hog: Total Operational Capacity Consumed by Incident Type", fontsize=14)
    plt.xlabel("Total Unit-Hours Consumed (Units * Duration)", fontsize=12)
    plt.ylabel("")
    
    for i, v in enumerate(top_consumers["resource_hours"]):
        plt.text(v + (v*0.01), i, f"{int(v):,}", va='center', fontsize=10)
        
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "resource_consumption_bar.png")
    plt.close()

def main():
    """
    Main entry point for the operational analysis script.
    
    Orchestrates the loading of data and execution of three primary analyses:
    Reality Gap (Sankey), Stress Test (Binned Curve), and Resource Consumption (Bar Chart).
    It handles exceptions during execution to ensure robust reporting.
    """
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