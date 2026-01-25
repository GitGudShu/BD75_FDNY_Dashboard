# Power BI Scripts: Temporal Analysis V2

Enhanced visual scripts for advanced analysis.

## Prerequisites
- Library: `matplotlib`, `seaborn`, `pandas`
- **Weather Columns**: Ensure `Dim_Weather` attributes (`temp_f`) are available in the dataset.

---

## 1. Gridlock (Dual-Axis)
**Fields**: `hour`, `nb_interventions` (Sum), `travel_time` (Average).

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Load
df = dataset.copy()
# Aggregation check (Power BI might pass raw rows)
agg = df.groupby("hour").agg({"nb_interventions": "sum", "travel_time": "mean"}).reset_index()

fig, ax1 = plt.subplots(figsize=(10, 6))

# Volumetry
sns.barplot(data=agg, x="hour", y="nb_interventions", color="lightblue", alpha=0.6, ax=ax1)
ax1.set_ylabel("Volume")

# Speed
ax2 = ax1.twinx()
sns.lineplot(data=agg, x="hour", y="travel_time", color="red", marker="o", linewidth=2.0, ax=ax2)
ax2.set_ylabel("Travel Time (s)")

plt.title("Gridlock: Volume vs Travel Time")
plt.show()
```

## 2. Risk Heatmap
**Fields**: `hour`, `category` (from Dim_IncidentType), `nb_interventions`.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = dataset.copy()

# Pivot
pivot = df.pivot_table(index="hour", columns="category", values="nb_interventions", aggfunc="sum", fill_value=0)

plt.figure(figsize=(10, 8))
sns.heatmap(pivot, cmap="inferno", annot=False)
plt.title("Risk Heatmap")
plt.show()
```

## 3. Shift Change (Dispatch)
**Fields**: `hour`, `dispatch_time` (Average).

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = dataset.copy()
agg = df.groupby("hour")["dispatch_time"].mean().reset_index()

plt.figure(figsize=(10, 6))
sns.lineplot(data=agg, x="hour", y="dispatch_time", marker="o", color="purple")

# Shift Lines
plt.axvline(9, color="orange", linestyle="--", label="09:00")
plt.axvline(18, color="green", linestyle="--", label="18:00")

plt.title("Shift Change Vulnerability")
plt.legend()
plt.show()
```

## 4. Weather Impact
**Fields**: `temp_f` (from Dim_Weather), `nb_interventions`.
**Note**: It is best to bucket temperatures in DAX or Python.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = dataset.copy()

# Simple Bucketing
df["temp_bin"] = (df["temp_f"] // 5) * 5
agg = df.groupby("temp_bin")["nb_interventions"].sum().reset_index()

plt.figure(figsize=(10, 6))
sns.regplot(data=agg, x="temp_bin", y="nb_interventions", scatter_kws={'s': 50}, line_kws={'color': 'red'})

plt.title("Volume vs Temperature")
plt.show()
```
