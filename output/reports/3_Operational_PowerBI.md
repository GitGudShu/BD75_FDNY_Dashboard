# Power BI Scripts: Operational Analysis V2

Snippets for advanced efficiency metrics.

## 1. Reality Gap (Sankey)
**Note**: Power BI has a native **Sankey Chart** custom visual (setup required). Python is alternative but static.
**Fields**: `INITIAL_CALL_TYPE`, `FINAL_CALL_TYPE`.

```python
# If using Python Visual
import plotly.graph_objects as go
import pandas as pd

df = dataset.copy()
# Aggregate flows
flow = df.groupby(["INITIAL_CALL_TYPE", "FINAL_CALL_TYPE"]).size().reset_index(name="value")
flow = flow.nlargest(20, "value")

# Indices
all_nodes = list(pd.concat([flow["INITIAL_CALL_TYPE"], flow["FINAL_CALL_TYPE"]]).unique())
node_map = {name: i for i, name in enumerate(all_nodes)}
source = flow["INITIAL_CALL_TYPE"].map(node_map)
target = flow["FINAL_CALL_TYPE"].map(node_map)

fig = go.Figure(data=[go.Sankey(
    node=dict(label=all_nodes, color="blue"),
    link=dict(source=source, target=target, value=flow["value"])
)])
fig.show()
```

## 2. Stress Test (Saturation Curve)
**Fields**: `hour`, `total_units`, `dispatch_time`.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = dataset.copy()
# Filter
df = df[df["dispatch_time"] < 600]

plt.figure(figsize=(10, 6))
# Order=2 for Hockey Stick curve
sns.regplot(data=df, x="total_units", y="dispatch_time", order=2, scatter_kws={'alpha':0.1}, line_kws={'color':'red'})
plt.title("System Saturation")
plt.show()
```

## 3. Anatomy of Delay (100% Stacked)
**Fields**: `hour`, `dispatch_time`, `travel_time`.

```python
import matplotlib.pyplot as plt
import pandas as pd

df = dataset.copy()
agg = df.groupby("hour")[["dispatch_time", "travel_time"]].mean().reset_index()

# Normalize
total = agg["dispatch_time"] + agg["travel_time"]
d_pct = agg["dispatch_time"] / total * 100
t_pct = agg["travel_time"] / total * 100

plt.figure(figsize=(10, 6))
plt.bar(agg["hour"], d_pct, label="Dispatch", color="#e74c3c")
plt.bar(agg["hour"], t_pct, bottom=d_pct, label="Travel", color="#3498db")
plt.legend()
plt.title("Anatomy of Delay (%)")
plt.axhline(50, color='white', linestyle='--')
plt.show()
```
