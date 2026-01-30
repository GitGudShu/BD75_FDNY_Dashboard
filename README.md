# FDNY Operational Response Analysis

**Group Members:**
* Thibault Lebreuil
* Thomas Chu

---

## Project description

This project analyzes **FDNY operational response** in New York using fire and EMS incident data.
The goal is to build a clean **BI-ready galaxy model** (facts + dimensions) that can be directly loaded into **Power BI** for analysis of response times, workload, and spatial patterns.

---

## Data sources

Download the datasets from NYC Open Data:

* **Fire incidents**
  [https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data/8m42-w767/about_data](https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data/8m42-w767/about_data)

* **EMS incidents**
  [https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj/about_data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj/about_data)

* **FDNY firehouse list**
  [https://data.cityofnewyork.us/Public-Safety/FDNY-Firehouse-Listing/hc8x-tcnd/about_data](https://data.cityofnewyork.us/Public-Safety/FDNY-Firehouse-Listing/hc8x-tcnd/about_data)

---

## How to Run

### 1. Setup
Place the raw CSV files in `data/raw/`:
*   `EMS.csv`
*   `FIRE.csv`
*   `Firehouse.csv`

### 2. Execution
Run the main ETL pipeline:
```bash
python src/etl/etl_pipeline_galaxy.py
```

### 3. Output
The script generates optimized **Parquet** files in:
`data/processed/galaxy_schema/`

These files are ready for direct import into Power BI.

---

## Updating the Data

To refresh the dataset with the latest information (e.g., new months of data), follow this pipeline:

1.  **Download latest datasets** from the [Data Sources](#data-sources) links above:
    *   `EMS.csv`
    *   `FIRE.csv`
    *   `Firehouse.csv` (if updated)
    *   *Place these files in `data/raw/`, overwriting the old ones.*

2.  **Fetch latest weather data**:
    ```bash
    python src/etl/fetch_weather.py
    ```
    *This downloads historical weather data for NYC to `data/raw/weather_nyc.csv`.*

3.  **Run the ETL pipeline**:
    ```bash
    python src/etl/etl_pipeline_galaxy.py
    ```
    *This processes the new raw files and regenerates the Parquet files in `data/processed/galaxy_schema/`.*

---

## Analysis Modules
While the primary goal is Power BI preparation, this repository includes Python scripts in `src/analysis/` to validate the model and generate advanced operational insights:
*   **Temporal**: Trends, Shift Changes, and Weather Impact.
*   **Geographic**: Hotspot mapping and Speed Trap analysis.
*   **Operational**: Efficiency metrics and Triage accuracy (Sankey diagrams).
