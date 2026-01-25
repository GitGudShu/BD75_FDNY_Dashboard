# Power BI Scripts: Geographic Analysis V2

scripts for advanced geospatial plots.

## Prerequisites
- Library: `geopandas`, `matplotlib`, `seaborn`, `shapely`
- **Shapefiles**: You must have `MODZCTA` geojson available to the script (or modify path).
- **Dependencies**: In Power BI service, using `geopandas` might require a custom environment or Gateways. A simpler alternative is using native Azure Maps for the "Speed Trap" (using Bubbles layer + Filled Map layer if supported) or "Shape Map".
- **For Python Visuals**: Ensure you install the libraries in your Python environment used by Power BI.

---

## 1. Triage Matrix (Scatter)
**Fields**: `location_key`, `nb_interventions` (Sum), `response_time` (Average).

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = dataset.copy()

# Averages (Citywide)
avg_vol = df["nb_interventions"].mean()
avg_resp = df["response_time"].mean()

plt.figure(figsize=(10, 8))
sns.scatterplot(data=df, x="nb_interventions", y="response_time", alpha=0.6, s=80, color="blue")

# Lines
plt.axvline(avg_vol, color="red", linestyle="--", label="Avg Vol")
plt.axhline(avg_resp, color="red", linestyle="--", label="Avg Resp")

# Labels for Top Right (Outliers)
df['dist'] = (df['nb_interventions'] - avg_vol) * (df['response_time'] - avg_resp)
top = df[(df['nb_interventions'] > avg_vol) & (df['response_time'] > avg_resp)].nlargest(5, 'dist')

# Assuming we have a Label column (e.g. Zipcode) dragged in. 
# If not, we just show points.
# If you dragged 'zipcode' into Values, it might be aggregated. Ensure 'Don't Summarize' or includes in ID.

plt.title("Triage Matrix")
plt.xlabel("Volume")
plt.ylabel("Response Time")
plt.legend()
plt.grid(True, linestyle=":", alpha=0.5)
plt.show()
```

## 2. Speed Trap Map (Python)
*Note: Rendering Maps in Power BI Python visual is slow. Use native visuals if possible.*

```python
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

# Load Shapefile inside Python script (Path must be absolute or accessible)
SHAPE_PATH = "C:/path/to/MODZCTA_2010_WGS1984.geo.json"
gdf = gpd.read_file(SHAPE_PATH)

# Join Data
df = dataset.copy()
# df must have 'zipcode' column
gdf = gdf.merge(df, left_on="MODZCTA", right_on="zipcode", how="left")

fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(column="response_time", cmap="RdYlGn_r", ax=ax, legend=True)

# Bubbles
# ... (Requires centroid calculation which is heavy for Power BI visual timeout limit)
# Recommendation: Use native Map.
plt.axis("off")
plt.show()
```
