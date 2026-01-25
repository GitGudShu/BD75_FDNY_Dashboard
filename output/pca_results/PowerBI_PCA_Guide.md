# Power BI PCA Guide

Use these scripts in the "Python Visual" component in Power BI. 

## Prerequisites
1.  **Select Fields**: Drag the necessary fields into the "Values" section of the Python visual.
    *   **Always include**: The numeric columns you want to analyze (e.g., `EMS_Incident_Count`, `Fire_Avg_Response_Time`, etc.).
    *   **For Individuals**: Include `ZIPCODE` and `BOROUGH` (or your identifier/group columns).
2.  **Environment**: Ensure your machine has python installed with `pandas`, `matplotlib`, `seaborn`, and `scikit-learn`.

---

## 1. Scree Plot (Eigenvalues)
**Goal**: Decide how many axes (components) to keep.
**Input**: Drag *only* the numeric metric columns.

```python
# Paste this into the Power BI Python Script Editor
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Power BI creates 'dataset' automatically
df = dataset.dropna().drop_duplicates()

# Select only numeric columns just in case
df_numeric = df.select_dtypes(include=[np.number])

# Normalize
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_numeric)

# PCA
pca = PCA()
pca.fit(df_scaled)

# Variance
explained_variance = pca.explained_variance_ratio_ * 100
cumulative_variance = np.cumsum(explained_variance)
n_components = len(explained_variance)
x_range = range(1, n_components + 1)

# Plot
plt.figure(figsize=(10, 6))
plt.bar(x_range, explained_variance, alpha=0.6, label='Individual Variance')
plt.plot(x_range, cumulative_variance, marker='o', color='red', linewidth=2, label='Cumulative Variance')

# Labels
for i, val in enumerate(cumulative_variance):
    plt.text(i + 1, val + 1, f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

plt.xlabel('Principal Components')
plt.ylabel('% Variance Explained')
plt.title('PCA Scree Plot')
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

plt.show()
```

---

## 2. Correlation Circle (Variables)
**Goal**: See relationships between variables (arrows).
**Input**: Drag *only* the numeric metric columns.
**Config**: Change `PC_X` and `PC_Y` variables at the top to change planes.

```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# --- CONFIGURATION ---
PC_X = 1  # First Component (Index 1)
PC_Y = 2  # Second Component (Index 2)
# ---------------------

df = dataset.dropna().drop_duplicates()
df_numeric = df.select_dtypes(include=[np.number])

scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_numeric)

pca = PCA()
pca.fit(df_scaled)

# Get Loadings (Correlations)
loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
features = df_numeric.columns

# Draw
plt.figure(figsize=(8, 8))
circle = plt.Circle((0, 0), 1, color='black', fill=False, linestyle='--')
plt.gca().add_artist(circle)

# Adjust indices (python is 0-indexed)
idx_x = PC_X - 1
idx_y = PC_Y - 1

for i, feature in enumerate(features):
    x_val = loadings[i, idx_x]
    y_val = loadings[i, idx_y]
    plt.arrow(0, 0, x_val, y_val, head_width=0.03, ec='blue', fc='blue', alpha=0.8)
    # Avoid text overlap logic can be complex, doing simple offset
    plt.text(x_val * 1.15, y_val * 1.15, feature, color='black', ha='center', va='center')

plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
plt.xlim(-1.2, 1.2)
plt.ylim(-1.2, 1.2)
plt.xlabel(f'PC{PC_X} ({pca.explained_variance_ratio_[idx_x]*100:.1f}%)')
plt.ylabel(f'PC{PC_Y} ({pca.explained_variance_ratio_[idx_y]*100:.1f}%)')
plt.title(f'Correlation Circle (PC{PC_X} & PC{PC_Y})')
plt.grid()
plt.tight_layout()

plt.show()
```

---

## 3. Reliability Table (Cos2)
**Goal**: Display how well each particular Zipcode is represented on the chosen plane.
**Input**: `ZIPCODE` + Metric Columns.
**Action**: This script generates a matplotlib **Table**. 

```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pandas.plotting import table
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# --- CONFIGURATION ---
PC_X = 1
PC_Y = 2
ID_COL = 'ZIPCODE' # Name of your ID column
# ---------------------

df = dataset.dropna().drop_duplicates()

# Separate IDs and Data
ids = df[ID_COL].astype(str).values
df_numeric = df.select_dtypes(include=[np.number])
# Remove ID col from numeric if it was auto-detected
if ID_COL in df_numeric.columns:
    df_numeric = df_numeric.drop(columns=[ID_COL])

# PCA
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_numeric)
pca = PCA()
X_pca = pca.fit_transform(X_scaled)

# Calculate Cos2
# Distances squared to origin in N-dim space
d2 = np.sum(X_scaled**2, axis=1)

# Coordinates squared
idx_x = PC_X - 1
idx_y = PC_Y - 1
coord_sq_x = X_pca[:, idx_x]**2
coord_sq_y = X_pca[:, idx_y]**2

# Cos2
cos2_x = coord_sq_x / d2
cos2_y = coord_sq_y / d2
quality_plane = cos2_x + cos2_y

# Create Result Dataframe
res = pd.DataFrame({
    ID_COL: ids,
    f'Cos2_PC{PC_X}': np.round(cos2_x, 3),
    f'Cos2_PC{PC_Y}': np.round(cos2_y, 3),
    'Quality(Sum)': np.round(quality_plane, 3)
})

# Sort by lowest quality to identify bad representations
res = res.sort_values('Quality(Sum)', ascending=True).head(20) # Show top 20 worst/best? Let's show bottom 20 (worst represented)

# Plot Table
fig, ax = plt.subplots(figsize=(10, 6))
ax.axis('off')
tbl = table(ax, res, loc='center', cellLoc='center')
tbl.auto_set_font_size(False)
tbl.set_fontsize(10)
tbl.scale(1.2, 1.2)
plt.title(f'Quality of Representation (Cos2) on PC{PC_X}-PC{PC_Y}\n(Bottom 20 - Potential Misinterpretations)')

plt.show()
```

---

## 4. Individuals Projection (Scatter Plot)
**Goal**: Project Zipcodes onto the map, colored by Borough.
**Input**: `ZIPCODE`, `BOROUGH` (optional), and Metric Columns.
**Config**: `PC_X`, `PC_Y`, `COLOR_COL`.

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# --- CONFIGURATION ---
PC_X = 1
PC_Y = 2
COLOR_COL = 'BOROUGH'   # Name of grouping column (set None if none)
LABEL_COL = 'ZIPCODE'   # Name of ID column
# ---------------------

df = dataset.dropna().drop_duplicates()

# numeric data
df_numeric = df.select_dtypes(include=[np.number])
# Exclude numeric ID or Color cols if they slipped in
cols_to_exclude = [c for c in [COLOR_COL, LABEL_COL] if c]
df_numeric = df_numeric.drop(columns=[c for c in cols_to_exclude if c in df_numeric.columns], errors='ignore')

# PCA
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_numeric)
pca = PCA()
X_pca = pca.fit_transform(X_scaled)

# Prepare Plot Data
idx_x = PC_X - 1
idx_y = PC_Y - 1

plot_df = pd.DataFrame({
    'x': X_pca[:, idx_x],
    'y': X_pca[:, idx_y]
})

if LABEL_COL and LABEL_COL in df.columns:
    plot_df['label'] = df[LABEL_COL].astype(str)
else:
    plot_df['label'] = ''

if COLOR_COL and COLOR_COL in df.columns:
    plot_df['group'] = df[COLOR_COL]
else:
    plot_df['group'] = 'All'

# Variance Info
var_x = pca.explained_variance_ratio_[idx_x] * 100
var_y = pca.explained_variance_ratio_[idx_y] * 100

# Plot
plt.figure(figsize=(12, 8))
sns.scatterplot(
    data=plot_df, x='x', y='y', 
    hue='group', alpha=0.7, s=100, palette='tab10'
)

# Add Labels (Only extremes to avoid clutter)
# Calculate distance from origin
plot_df['dist'] = np.sqrt(plot_df['x']**2 + plot_df['y']**2)
# Label top 15 most extreme points
top_indices = plot_df.nlargest(15, 'dist').index

for i in top_indices:
    row = plot_df.loc[i]
    plt.text(row['x'], row['y'], row['label'], fontsize=9, fontweight='bold', ha='right')

plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
plt.xlabel(f'PC{PC_X} ({var_x:.1f}%)')
plt.ylabel(f'PC{PC_Y} ({var_y:.1f}%)')
plt.title(f'Individuals Map (PC{PC_X} & PC{PC_Y})')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()

plt.show()
```
