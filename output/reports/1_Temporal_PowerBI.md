# Power BI Scripts: Temporal Analysis

Paste these snippets into Python Visuals in Power BI.

## Prerequisites
- Library: `matplotlib`, `seaborn`, `pandas`
- **Fields**: You must drag the relevant columns into the "Values" well of the visual.

---

## 1. Hourly Pattern (Line Chart)
**Fields to Drag**: `hour`, `nb_interventions`, `Type` (or Source).

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# 1. Config
# Make sure your column names match what is in 'dataset'
# Power BI often renames 'Sum of nb_interventions' to 'nb_interventions' inside the script environment, 
# but check dataset.columns if unsure.
X_COL = "hour"
Y_COL = "nb_interventions"
HUE_COL = "Type" # Optional: if you have a source column

# 2. Data Prep
df = dataset.copy()

# Ensure aggregation (SUM) in case Power BI passed raw rows
if HUE_COL in df.columns:
    df_agg = df.groupby([X_COL, HUE_COL])[Y_COL].sum().reset_index()
else:
    df_agg = df.groupby([X_COL])[Y_COL].sum().reset_index()

# 3. Plot
plt.figure(figsize=(10, 6))
if HUE_COL in df.columns:
    sns.lineplot(data=df_agg, x=X_COL, y=Y_COL, hue=HUE_COL, marker="o")
else:
    sns.lineplot(data=df_agg, x=X_COL, y=Y_COL, marker="o")

plt.title("Hourly Incidents Pattern")
plt.xticks(range(0, 24))
plt.grid(True)
plt.tight_layout()
plt.show()
```

## 2. Weekly Pattern (Bar Chart)
**Fields to Drag**: `day_name` (or `day_of_week`), `nb_interventions`, `Type`.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Config
X_COL = "day_name"
Y_COL = "nb_interventions"
HUE_COL = "Type"
ORDER_COL = "day_of_week" # Optional: drag numeric day to sort correctly

df = dataset.copy()

# Sort order
if ORDER_COL in df.columns:
    df = df.sort_values(ORDER_COL)

plt.figure(figsize=(10, 6))
if HUE_COL in df.columns:
    sns.barplot(data=df, x=X_COL, y=Y_COL, hue=HUE_COL, errorbar=None)
else:
    sns.barplot(data=df, x=X_COL, y=Y_COL, errorbar=None)

plt.title("Incidents by Day of Week")
plt.grid(axis='y')
plt.tight_layout()
plt.show()
```

## 3. Yearly/Monthly Trend
**Fields to Drag**: `year` (or `date`), `nb_interventions`, `Type`.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Config
X_COL = "year" # or 'date' or 'month'
Y_COL = "nb_interventions"
HUE_COL = "Type"

df = dataset.copy()
df = df.groupby([X_COL, HUE_COL])[Y_COL].sum().reset_index() if HUE_COL in df.columns else df.groupby(X_COL)[Y_COL].sum().reset_index()

plt.figure(figsize=(10, 6))
if HUE_COL in df.columns:
    sns.lineplot(data=df, x=X_COL, y=Y_COL, hue=HUE_COL, marker="o")
else:
    sns.lineplot(data=df, x=X_COL, y=Y_COL, marker="o")

plt.title("Trend Analysis")
plt.grid(True)
plt.tight_layout()
plt.show()
```
