
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

# --- CONFIG ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "galaxy_schema"
GEO_DIR = PROJECT_ROOT / "geodata"
OUTPUT_FIG = PROJECT_ROOT / "output" / "figures" / "geographic"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "reports"

OUTPUT_FIG.mkdir(parents=True, exist_ok=True)
OUTPUT_REPORT.mkdir(parents=True, exist_ok=True)

def load_data():
    print("Loading data...")
    dim_location = pd.read_parquet(DATA_DIR / "Dim_Location.parquet")
    dim_firehouse = pd.read_parquet(DATA_DIR / "Dim_Firehouse.parquet")
    
    cols = ["location_key", "nb_interventions", "response_time"] 
    # Note: 'response_time' was normalized in ETL to 'INCIDENT_RESPONSE_SECONDS_QY' or similar. 
    # Check ETL output names. in etl_pipeline_galaxy.py: 
    # kp_cols = {"INCIDENT_RESPONSE_SECONDS_QY": "response_time", ...}
    # So 'response_time' is the correct column name.
    
    f_ems = pd.read_parquet(DATA_DIR / "Fact_Incidents_EMS.parquet", columns=cols)
    # Fire might not have response_time depending on raw data, but ETL tried to populate it.
    f_fire = pd.read_parquet(DATA_DIR / "Fact_Incidents_Fire.parquet", columns=cols)
    
    combined = pd.concat([f_ems, f_fire])
    
    # Load Shapefile (MODZCTA)
    # The file is GeoJSON
    shape_path = GEO_DIR / "MODZCTA_2010_WGS1984.geo.json"
    print(f"Loading Shapefile from {shape_path}...")
    nyc_map = gpd.read_file(shape_path)
    
    # MODZCTA has 'MODZCTA' column as label? Let's check columns if this fails, but usually it's standard 
    # for this dataset.
    
    return dim_location, dim_firehouse, combined, nyc_map

def analyze_speed_trap(combined, dim_location, nyc_map):
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
        edgecolor="0.6", # Lighter borders to reduce noise
        legend=True, 
        legend_kwds={"label": "Avg Response Time (s)", "shrink": 0.6}, 
        missing_kwds={'color': '#f0f0f0'}
    )
    
    # HOLLOW RINGS
    map_data_points = map_data.copy()
    map_data_points["geometry"] = map_data_points.geometry.centroid
    valid_points = map_data_points.dropna(subset=["nb_interventions"])
    valid_points = valid_points.sort_values("nb_interventions", ascending=False)
    sizes = valid_points["nb_interventions"] / valid_points["nb_interventions"].max() * 800
    
    # LAYER A: The Rings (Volume)
    # Facecolor='none' makes them transparent. Edgecolor gives the outline.
    ax.scatter(
        valid_points.geometry.x, 
        valid_points.geometry.y, 
        s=sizes, 
        facecolors='none',      # Hollow center
        edgecolors='#2c3e50',   # Dark Slate Blue outline (high contrast on Red/Green)
        linewidths=1.5,         # Thicker line to be visible
        alpha=0.8,              # High opacity for the line
        label="Volume (Ring Size)"
    )
    
    # LAYER B: The Anchors (Location)
    # A tiny dot in the center so we know EXACTLY where the zip code center is
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
    plt.savefig(OUTPUT_FIG / "speed_trap_map.png", dpi=300) # Increased DPI for crisp lines
    plt.close()

def analyze_triage_matrix(combined, dim_location):
    print("Running Triage Matrix Analysis...")
    
    # Aggregate by Zipcode
    agg_loc = combined.groupby("location_key").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()
    
    merged = agg_loc.merge(dim_location, on="location_key")
    zip_agg = merged.groupby("zipcode").agg({
        "nb_interventions": "sum",
        "response_time": "mean"
    }).reset_index()
    
    # Calculate Averages
    avg_vol = zip_agg["nb_interventions"].mean()
    avg_resp = zip_agg["response_time"].mean()
    
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=zip_agg, x="nb_interventions", y="response_time", alpha=0.6, s=60)
    
    # Quadrant Lines
    plt.axvline(avg_vol, color="red", linestyle="--", label=f"Avg Vol: {int(avg_vol)}")
    plt.axhline(avg_resp, color="red", linestyle="--", label=f"Avg Resp: {int(avg_resp)}s")
    
    # Highlight Top-Right (High Vol, Slow Resp)
    # Annotate top 5 worst offenders in that quadrant
    danger_zone = zip_agg[(zip_agg["nb_interventions"] > avg_vol) & (zip_agg["response_time"] > avg_resp)]
    
    # Score them by distance from center or just sum of normalized values?
    # Simple metric: Vol * Resp (Impact Factor)
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
    
    # Label Quadrants
    # Top-Right
    plt.text(zip_agg["nb_interventions"].max()*0.9, zip_agg["response_time"].max()*0.9, "CRITICAL\n(High Vol, Slow)", 
             ha='right', va='top', color='red', fontsize=12, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))
             
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "triage_matrix.png")
    plt.close()

def analyze_station_reach(dim_location, dim_firehouse, combined, nyc_map):
    print("Running Station Reach (Voronoi) Analysis...")
    # NOTE: Since we don't have incident lat/lon, we approximate.
    # 1. Generate Voronoi for Firehouses
    # 2. Assign Zipcodes to nearest Firehouse (or Spatial Join Centroids -> Voronoi)
    # 3. Calculate Avg performance for that group of Zipcodes
    # 4. Color Voronoi Polygon by that performance
    
    # 1. Firehouse Points
    # Ensure we valid coord
    fh = dim_firehouse.dropna(subset=["Latitude", "Longitude"])
    points = [Point(xy) for xy in zip(fh.Longitude, fh.Latitude)]
    
    # Create Voronoi
    # We need a boundary box to bound infinite Voronoi regions
    # Use bounds of nyc_map
    minx, miny, maxx, maxy = nyc_map.total_bounds
    envelope = box(minx, miny, maxx, maxy)
    
    # Scipy Voronoi or Shapely? Shapely `voronoi_diagram` is easier if available (recent shapely)
    # Else geovoronoi. We will try shapely first.
    
    # Points to MultiPoint
    mp = MultiPoint(points)
    
    if True: # try:
        voronoi_polys = voronoi_diagram(mp, envelope=envelope)
        # Result is a GeometryCollection of Polygons
        
        # Convert to GeoDataFrame
        # We need to map polygons back to firehouses. 
        # Voronoi regions order isn't guaranteed to match input points order in shapely 1.8 without care.
        # Although shapely documentation says: "The regions are not guaranteed to be ordered".
        # We need to perform a spatial join to associate firehouses with their polygon.
        
        gs = gpd.GeoSeries([p for p in voronoi_polys.geoms], crs=nyc_map.crs) # Assuming coords match CRS (WGS84 usually 4326)
        # Note: nyc_map might be EPSG:4326 (WGS84) or projected. 
        # Firehouse coords are Lat/Lon (4326).
        # Check CRS
        if nyc_map.crs is None:
            nyc_map.set_crs(epsg=4326, inplace=True) # MODZCTA geojson is usually 4326
            
        gs.crs = "EPSG:4326"
        
        gdf_voronoi = gpd.GeoDataFrame(geometry=gs)
        
        # Join Firehouses to Polygons (Assign Metadata)
        fh_gdf = gpd.GeoDataFrame(
            fh, geometry=gpd.points_from_xy(fh.Longitude, fh.Latitude), crs="EPSG:4326"
        )
        
        # Spatial Join: Which Firehouse is inside which Voronoi Poly?
        # Each poly should have exactly 1 firehouse (generator).
        gdf_voronoi = gpd.sjoin(gdf_voronoi, fh_gdf, how="inner", predicate="contains")
        gdf_voronoi = gdf_voronoi.rename(columns={"index_right": "firehouse_index"})
        
        # 2. Assign Incidents to Voronoi (via Zipcode Centroid)
        # Aggregate stats by Zipcode first
        agg_loc = combined.groupby("location_key").agg({"response_time": "mean"}).reset_index()
        merged = agg_loc.merge(dim_location, on="location_key")
        zip_stats = merged.groupby("zipcode")["response_time"].mean().reset_index()
        
        # Zipcode GeoDataFrame
        # Get centroids from MODZCTA map
        nyc_map["MODZCTA"] = nyc_map["MODZCTA"].astype(str)
        zip_stats["zipcode"] = zip_stats["zipcode"].astype(str)
        
        zip_geo = nyc_map.merge(zip_stats, left_on="MODZCTA", right_on="zipcode", how="inner")
        # Use Centroids for association
        zip_geo["centroid"] = zip_geo.geometry.centroid
        zip_points = zip_geo.set_geometry("centroid")
        
        # Spatial Join Zip-Centroids to Voronoi
        # Assign each Zip's performance to the Voronoi region it falls into
        joined = gpd.sjoin(zip_points, gdf_voronoi, how="inner", predicate="within")
        
        # Now aggregate performance by Voronoi Zone (Firehouse)
        # One Voronoi zone might cover multiple zips
        voronoi_stats = joined.groupby("index_right")["response_time"].mean().reset_index()
        # 'index_right' maps back to gdf_voronoi index
        
        gdf_voronoi = gdf_voronoi.merge(voronoi_stats, left_index=True, right_on="index_right", how="left")
        
        # Clip to NYC shoreline for aesthetics
        # Dissolve nyc_map to get outline
        nyc_outline = nyc_map.dissolve()
        gdf_voronoi_clipped = gpd.clip(gdf_voronoi, nyc_outline)
        
        # Plot
        fig, ax = plt.subplots(figsize=(12, 10))
        gdf_voronoi_clipped.plot(column="response_time", cmap="RdYlGn_r", linewidth=0.5, edgecolor="white", 
                                 ax=ax, legend=True, legend_kwds={"label": "Estimated Response Time (s)"},
                                 missing_kwds={'color': 'lightgrey'})
        
    # Plot Firehouse Points on top
    fh_gdf.plot(ax=ax, color="white", markersize=15, marker="^", edgecolor="black", linewidth=0.5, label="Firehouse")
    
    plt.title("Station Reach: Voronoi Territories Colored by Response Time")
    plt.axis("off")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG / "station_reach_voronoi.png")
    plt.close()

def main():
    dim_location, dim_firehouse, combined, nyc_map = load_data()
    
    analyze_speed_trap(combined, dim_location, nyc_map)
    analyze_triage_matrix(combined, dim_location)
    analyze_station_reach(dim_location, dim_firehouse, combined, nyc_map)
    
    print("Geographic V2 Analysis Complete. Figures in", OUTPUT_FIG)

if __name__ == "__main__":
    main()
