from pathlib import Path
import geopandas as gpd
import topojson as tp
import json

FOLDER = Path(r"nypp_25d")

shp_path = FOLDER / "nypp.shp"
out_path = FOLDER / "nyc_police_precincts.topojson"

gdf = gpd.read_file(shp_path, engine="pyogrio")

if gdf.crs is None:
    raise ValueError("Missing CRS in shapefile.")
gdf = gdf.to_crs(epsg=4326)

keep = []
for c in gdf.columns:
    if c.lower() in {"precinct", "pct", "precinctid", "precinct_id", "name"}:
        keep.append(c)
gdf = gdf[keep + ["geometry"]] if keep else gdf[["geometry"]]

geo = gdf.__geo_interface__
topo = tp.Topology(geo, prequantize=True).to_dict()

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(topo, f)

print(out_path)
