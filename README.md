# FDNY Operational Response Analysis
## Group members

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

## File setup

After downloading, rename the CSV files exactly as follows:

* `EMS.csv`
* `FIRE.csv`
* `Firehouse.csv`

Place all three files next to the notebook in the root.

---

## Run

Run the notebook:

**`fdny_galaxy_model_export.ipynb`**

It cleans the data, builds fact and dimension tables, and exports everything as Parquet.

---

## Output

After execution, you should get a folder:

```
powerbi_parquet/
```

It contains all fact and dimension tables as **.parquet** files, ready to import into Power BI.

---

## Power BI

Import the Parquet files, create relationships, build measures `to be continued....`
