# FDNY Incident Data Analysis Report

## Executive Summary
This report details the findings from a Principal Component Analysis (PCA) conducted on FDNY metrics. The goal was to uncover underlying patterns in Fire Department operations and neighborhood characteristics. By reducing complex datasets into fundamental "dimensions," we can better understand what drives performance and demand.

Our analysis successfully identified distinct drivers for both Fire Efficiency and Neighborhood Activity. Crucially, we found that **incident complexity is distinct from dispatch speed**, and that **neighborhood busyness does not predict response delays**. These insights suggest that resource allocation models need to treat these factors independently.

---

## 1. Fire Efficiency Analysis
The first analysis focused on the operational efficiency of fire interventions. We analyzed five key variables: Dispatch Time, Travel Time, and the number of resources deployed (Engines, Ladders, Other Units).

### Key Findings
The analysis reveals that fire interventions are not one-dimensional. A "complex" fire is not necessarily a "slow" one. We identified three distinct factors that explain over 65% of the operational variance:

1.  **Resource Intensity (Dimension 1)**: This is the dominant factor. It differentiates simple incidents from massive, multi-unit responses. It captures the sheer scale of the event.
2.  **Dispatch Speed (Dimension 2)**: This factor is exclusively about how fast the dispatch system reacts. Surprisingly, this is largely independent of the intervention's size; the dispatch system is just as fast (or slow) for small fires as it is for large ones.
3.  **Travel Speed (Dimension 3)**: Travel time forms its own separate dimension, likely driven by distance and traffic rather than the nature of the emergency.

### Technical Deep Dive
*   **Eigenvalues**: The first two axes explain **65.9%** of the information (Variance).
    *   **PC1 (46.0%)**: Strongly correlated with Engines (0.85) and Ladders (0.85).
    *   **PC2 (19.9%)**: Strongly correlated with Dispatch Time (0.98).
*   **Correlation Circle**: The visual below demonstrates the orthogonality (independence) of these variables. Note how the "Dispatch Time" vector is at a 90-degree angle to the resource vectors (Engines, Ladders), proving they are independent phenomena.

![Fire Efficiency Correlation Circle](/output/pca_results/fire/fire_efficiency_corr_circle_pc1_pc2.png)

### Distribution of Incidents
Projecting individual incidents onto these axes shows a clear pattern. The majority of incidents cluster in the "Low Resource" zone, with a long tail extending into the "High Resource" zone. This confirms that while most calls are routine, the system must maintain the capacity for these extreme outliers.

![Fire Incident Projection](/output/pca_results/fire/fire_efficiency_individuals_pc1_pc2.png)

![Fire Efficiency Scree Plot](/output/pca_results/fire/fire_efficiency_scree_plot.png)

---

## 2. Neighborhood Characteristics Analysis
The second analysis examined New York City neighborhoods (via Zipcodes) to understand the relationship between demand (Incident Counts) and performance (Response Times).

### Key Findings
A common assumption is that the busiest neighborhoods suffer from slower service due to congestion or high demand. **Our analysis proves this assumption false.**

We found that neighborhoods differ along two completely independent axes:
1.  **Activity Level (Dimension 1)**: This simply measures how "busy" a neighborhood is. Some zip codes generate massive call volumes for both EMS and Fire, while others are quiet.
2.  **Responsiveness (Dimension 2)**: This measures how long it takes to help to arrive.

The lack of correlation between these two dimensions is a positive finding for the FDNY. It implies the department has successfully scaled its presence to match demand—busy areas do not inherently suffer from worse response times. Delays are likely caused by geographic isolation or local infrastructure rather than system overload.

### Technical Deep Dive
*   **Eigenvalues**: The first two axes explain a very high **82.0%** of the variance, making this a highly reliable model.
    *   **PC1 (51.2%)**: "Busyness". Correlation with EMS Count (0.98) and Fire Count (0.98).
    *   **PC2 (30.7%)**: "Slowness". Correlation with EMS Avg Response Time (0.81).

### Visual Interpretation
The Correlation Circle below is striking. The vectors for "Incident Counts" point horizontally (PC1), while "Response Times" point vertically (PC2). The near-perfect right angle between them visually confirms that being busy does not equate to being slow.

![Neighborhood Correlation Circle](/output/pca_results/neighborhoods/neighborhoods_corr_circle_pc1_pc2.png)

### Borough Dynamics
We have enhanced the individual projection by coloring neighborhoods according to their **Borough**. This reveals interesting geographical clusters:
*   **Staten Island**: Typically forms a distinct cluster (often in the "Quiet" but sometimes "Slower" zones due to geography).
*   **Manhattan**: Concentrated in the high-activity zones.
*   **Bronx/Brooklyn/Queens**: Spread across the spectrum, reflecting the diverse nature of these boroughs from dense urban centers to quieter residential areas.

The visual separation of these boroughs on the plot further emphasizes that operational challenges are often localized and borough-specific.

### Neighborhood Clusters
We can classify neighborhoods into four distinct categories based on the plot below:
*   **Efficient Hubs (Bottom Right)**: High volume, fast response. Ideally staffed.
*   **Quiet Enclaves (Bottom Left)**: Low volume, fast response.
*   **Hard-to-Reach Areas (Top Left)**: Low volume, but slow response. likely remote or geographically challenging areas.
*   **Problem Areas (Top Right)**: High volume and slow response. These are the critical zones requiring immediate strategic attention.

![Neighborhood Projection](/output/pca_results/neighborhoods/neighborhoods_individuals_pc1_pc2.png)

![Neighborhood Scree Plot](/output/pca_results/neighborhoods/neighborhoods_scree_plot.png)

---

