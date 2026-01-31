
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import voronoi_diagram
from shapely.geometry import MultiPoint, box

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
GEO_DIR = PROJECT_ROOT / "geodata"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "geographic"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    """
    Loads necessary datasets for geographic analysis including dimensions, facts, and shapefiles.
    
    This function reads parquet files for location and firehouse dimensions, and EMS/Fire incident facts.
    It combines EMS and Fire facts into a single dataset. It also loads the NYC MODZCTA shapefile 
    for geospatial plotting.
        
    Returns:
        tuple: A tuple containing:
            - dim_location (pd.DataFrame): Location dimension data.
            - dim_firehouse (pd.DataFrame): Firehouse dimension data.
            - combined (pd.DataFrame): Combined EMS and Fire incident data.
            - nyc_map (gpd.GeoDataFrame): NYC MODZCTA shapefile data.
    """
    print("Loading data...")
    dim_location = pd.read_parquet(DATA_DIR / "Dim_Location.parquet")
    dim_firehouse = pd.read_parquet(DATA_DIR / "Dim_Firehouse.parquet")
    
    cols = ["location_key", "nb_interventions", "response_time"] 
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols)
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols)
    combined = pd.concat([f_ems, f_fire])
    
    shape_path = GEO_DIR / "MODZCTA_2010_WGS1984.geo.json"
    print(f"Loading Shapefile from {shape_path}...")
    nyc_map = gpd.read_file(shape_path)
    
    return dim_location, dim_firehouse, combined, nyc_map

def analyze_speed_trap(combined, dim_location, nyc_map):
    """
    Generates a map visualizing the relationship between response time and incident volume.
    
    This method aggregates incident data by location key and then by zipcode to calculate
    average response times and total intervention volumes. It merges this data with the 
    NYC shapefile to produce a map where color represents response time and ring size 
    represents volume.
    
    Parameters:
        combined (pd.DataFrame): Combined incident data.
        dim_location (pd.DataFrame): Location dimension data.
        nyc_map (gpd.GeoDataFrame): NYC shapefile data.
        
    Returns:
        None: Saves the generated figure 'speed_trap_map.png' to the output directory.
    """
    print("Running Speed Trap Analysis (Map)...")
    
    agg_loc = combined.groupby("location_key").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()
    
    merged = agg_loc.merge(dim_location, on="location_key")
    
    zip_agg = merged.groupby("zipcode").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()

    nyc_map["MODZCTA"] = nyc_map["MODZCTA"].astype(str)
    zip_agg["zipcode"] = zip_agg["zipcode"].astype(str)
    
    map_data = nyc_map.merge(zip_agg, left_on="MODZCTA", right_on="zipcode", how="left")
    fig, ax = plt.subplots(figsize=(14, 12))
    map_data.plot(
        column="response_time", 
        cmap="RdYlGn_r", 
        linewidth=0.5, 
        ax=ax, 
        edgecolor="0.6",
        legend=True, 
        legend_kwds={"label": "Avg Response Time (s)", "shrink": 0.6}, 
        missing_kwds={'color': '#f0f0f0'}
    )
    
    map_data_points = map_data.copy()
    map_data_points["geometry"] = map_data_points.geometry.centroid
    valid_points = map_data_points.dropna(subset=["nb_interventions"])
    valid_points = valid_points.sort_values("nb_interventions", ascending=False)
    sizes = valid_points["nb_interventions"] / valid_points["nb_interventions"].max() * 800
    
    ax.scatter(
        valid_points.geometry.x, 
        valid_points.geometry.y, 
        s=sizes, 
        facecolors='none',
        edgecolors='#2c3e50',
        linewidths=1.5,
        alpha=0.8,
        label="Volume (Ring Size)"
    )
    
    ax.scatter(
        valid_points.geometry.x, 
        valid_points.geometry.y, 
        s=10, 
        color='#2c3e50',
        alpha=1
    )
    
    plt.title("The Speed Trap: Response Time (Color) vs Volume (Ring Size)", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "speed_trap_map.png", dpi=300)
    plt.close()

def analyze_triage_matrix(combined, dim_location):
    """
    Creates a scatter plot to analyze performance versus demand (Triage Matrix).
    
    This function groups data by zipcode to compare incident volume against average response time.
    It plots these zipcodes on a scatter chart, drawing quadrant lines at the average volume and
    average response time. It highlights and annotates the most critical zipcodes (high volume, slow response).
    
    Parameters:
        combined (pd.DataFrame): Combined incident data.
        dim_location (pd.DataFrame): Location dimension data.
        
    Returns:
        None: Saves the generated figure 'triage_matrix.png' to the output directory.
    """
    print("Running Triage Matrix Analysis...")
    
    agg_loc = combined.groupby("location_key").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()
    
    merged = agg_loc.merge(dim_location, on="location_key")
    zip_agg = merged.groupby("zipcode").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()
    
    avg_vol = zip_agg["nb_interventions"].mean()
    avg_resp = zip_agg["response_time"].mean()
    
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=zip_agg, x="nb_interventions", y="response_time", alpha=0.6, s=60)
    plt.axvline(avg_vol, color="red", linestyle="--", label=f"Avg Vol: {int(avg_vol)}")
    plt.axhline(avg_resp, color="red", linestyle="--", label=f"Avg Resp: {int(avg_resp)}s")
    danger_zone = zip_agg[(zip_agg["nb_interventions"] > avg_vol) & (zip_agg["response_time"] > avg_resp)]
    danger_zone = danger_zone.copy()
    danger_zone["impact"] = danger_zone["nb_interventions"] * danger_zone["response_time"]
    top_danger = danger_zone.nlargest(5, "impact")
    
    for _, row in top_danger.iterrows():
        plt.text(row["nb_interventions"], row["response_time"], str(row["zipcode"]), fontsize=9, fontweight='bold', color='darkred')
        
    plt.title("Triage Matrix: Performance vs Demand")
    plt.xlabel("Incident Volume (Demand)")
    plt.ylabel("Avg Response Time (Performance)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    
    plt.text(zip_agg["nb_interventions"].max()*0.9, zip_agg["response_time"].max()*0.9, "CRITICAL\n(High Vol, Slow)", 
             ha='right', va='top', color='red', fontsize=12, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))
             
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "triage_matrix.png")
    plt.close()

def analyze_station_reach(dim_location, dim_firehouse, combined, nyc_map):
    """
    Performs Voronoi analysis to estimate station reach and performance.
    
    This function approximates station territories using Voronoi diagrams based on firehouse locations.
    It assigns incidents to these territories by spatially joining zipcode centroids to the Voronoi polygons.
    It then aggregates response times within each territory and visualizes the results on a map, clipped 
    to the NYC boundary.
    
    The analysis approximates location by using zipcode centroids as we do not have exact incident lat/lon.
    
    Parameters:
        dim_location (pd.DataFrame): Location dimension data.
        dim_firehouse (pd.DataFrame): Firehouse dimension data.
        combined (pd.DataFrame): Combined incident data.
        nyc_map (gpd.GeoDataFrame): NYC shapefile data.
        
    Returns:
        None: Saves the generated figure 'station_reach_voronoi.png' to the output directory.
    """
    print("Running Station Reach (Voronoi) Analysis...")
    
    fh = dim_firehouse.dropna(subset=["Latitude", "Longitude"])
    points = [Point(xy) for xy in zip(fh.Longitude, fh.Latitude)]
    
    minx, miny, maxx, maxy = nyc_map.total_bounds
    envelope = box(minx, miny, maxx, maxy)
    
    mp = MultiPoint(points)
    
    if True:
        voronoi_polys = voronoi_diagram(mp, envelope=envelope)
        gs = gpd.GeoSeries([p for p in voronoi_polys.geoms], crs=nyc_map.crs)
        if nyc_map.crs is None:
            nyc_map.set_crs(epsg=4326, inplace=True)

        gs.crs = "EPSG:4326"
        gdf_voronoi = gpd.GeoDataFrame(geometry=gs)
        fh_gdf = gpd.GeoDataFrame(
            fh, geometry=gpd.points_from_xy(fh.Longitude, fh.Latitude), crs="EPSG:4326"
        )
        
        gdf_voronoi = gpd.sjoin(gdf_voronoi, fh_gdf, how="inner", predicate="contains")
        gdf_voronoi = gdf_voronoi.rename(columns={"index_right": "firehouse_index"})
        
        agg_loc = combined.groupby("location_key").agg({"response_time": "mean"}).reset_index()
        merged = agg_loc.merge(dim_location, on="location_key")
        zip_stats = merged.groupby("zipcode")["response_time"].mean().reset_index()
        
        nyc_map["MODZCTA"] = nyc_map["MODZCTA"].astype(str)
        zip_stats["zipcode"] = zip_stats["zipcode"].astype(str)
        
        zip_geo = nyc_map.merge(zip_stats, left_on="MODZCTA", right_on="zipcode", how="inner")
        zip_geo["centroid"] = zip_geo.geometry.centroid
        zip_points = zip_geo.set_geometry("centroid")
        
        joined = gpd.sjoin(zip_points, gdf_voronoi, how="inner", predicate="within")
        voronoi_stats = joined.groupby("index_right")["response_time"].mean().reset_index()
        gdf_voronoi = gdf_voronoi.merge(voronoi_stats, left_index=True, right_on="index_right", how="left")
        nyc_outline = nyc_map.dissolve()
        gdf_voronoi_clipped = gpd.clip(gdf_voronoi, nyc_outline)
        
        fig, ax = plt.subplots(figsize=(12, 10))
        gdf_voronoi_clipped.plot(column="response_time", cmap="RdYlGn_r", linewidth=0.5, edgecolor="white", 
                                 ax=ax, legend=True, legend_kwds={"label": "Estimated Response Time (s)"},
                                 missing_kwds={'color': 'lightgrey'})
        
    fh_gdf.plot(ax=ax, color="white", markersize=15, marker="^", edgecolor="black", linewidth=0.5, label="Firehouse")
    
    plt.title("Station Reach: Voronoi Territories Colored by Response Time")
    plt.axis("off")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "station_reach_voronoi.png")
    plt.close()

def main():
    """
    Main entry point for the geographic analysis script.
    
    Orchestrates the loading of data and execution of three primary analyses:
    Speed Trap (Map), Triage Matrix (Scatter), and Station Reach (Voronoi).
    """
    dim_location, dim_firehouse, combined, nyc_map = load_data()
    
    analyze_speed_trap(combined, dim_location, nyc_map)
    analyze_triage_matrix(combined, dim_location)
    analyze_station_reach(dim_location, dim_firehouse, combined, nyc_map)
    
    print("Geographic V2 Analysis Complete. Figures in", OUTPUT_FIG)

if __name__ == "__main__":
    main()
