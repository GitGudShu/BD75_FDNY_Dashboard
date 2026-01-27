# Geographic Analysis V2: Maps & Coverage

This updated report includes advanced geospatial visualizations to identify coverage gaps and operational bottlenecks.

## 1. The Speed Trap: Performance vs Demand
**Concept**: Visualizing two variables at once.
- **Background Color**: Average Response Time (Red = Slow, Green = Fast).
- **Bubble Size**: Incident Volume (Bigger = More Incidents).

![Speed Trap](/output/figures/geographic_v2/speed_trap_map.png)
> Note for Thib: **10/10** Well f-ing yeah, we can clearly see the "Inequality of Safety". Look at the contrast: Manhattan is a swarm of massive activity (huge rings) but the ground underneath is mostly green/yellow, the system is stressed but holding. Compare that to the Rockaways (that strip at the very bottom) or parts of Eastern Queens: tiny rings but dark orange/red ground. This tells the Chief immediately that those people aren't waiting because the system is busy; they are waiting because they are isolated. I think ?

*Insight*: Look for **Large 'radar looking thing' on Red Backgrounds**. These are your "Crisis Zones", high demand areas where the system is failing (slow response). Conversely, you can also argue for the relevency of small radars on red backgrounds might be remote areas where speed is sacrificed for coverage efficiency.

## 2. Station Reach: Voronoi Territories
**Concept**: Theoretical vs Actual Coverage.
We generated Voronoi polygons around each firehouse to define its "natural territory" and colored them by the average response time of incidents occurring within that territory.

![Station Reach](/output/figures/geographic_v2/station_reach_voronoi.png)
> Note for Thib: 8/10 The infrastructure audit. This map validates the station layout logic but exposes its cracks. Look at the size difference in the polygons: in Manhattan, the cells are microscopic, which explains why response times are good despite the traffic, you are never more than 5 blocks from a firehouse. But look at that massive red polygon at the bottom (Broad Channel/Rockaways). That single station is trying to cover a territory ten times the size of a Midtown station. That is a clear argument for building a new facility or permanently staging a unit halfway down that peninsula.

*Insight*: If a firehouse has a **small territory but red color**, the issue is not distance, it is likely traffic congestion or station processing efficiency. If a territory is large and red, it suggests a need for an additional station (or satellite unit) to split the load.

## 3. The Triage Matrix
**Concept**: Prioritization Ranking.
- **X-Axis**: Incident Volume (Demand).
- **Y-Axis**: Response Time (Performance).
- **Quadrants**: Divided by citywide averages.

![Triage Matrix](/output/figures/geographic_v2/triage_matrix.png)
> Note for Thib: 9/10 The budget allocator. This is the chart that gets things done. By plotting the quadrants, we’ve isolated the "Kill List" in the top right. We can now ignore the noise and tell leadership: "Forget about the city average. We need to fix Zip 10468 (Bronx) and 11207 (Brooklyn) immediately". These neighborhoods are suffering the worst of both worlds: they are incredibly busy and the trucks are arriving late. If you have budget for 5 new ambulances or a new traffic pre-emption system, this chart proves mathematically that they belong in 10468, not in a quiet neighborhood that complains louder.

### The "Critical" Quadrant (Top Right)
The labeled Zip Codes in the top-right are your immediate investment targets. They represent neighborhoods with **Above Average Demand** AND **Slower Than Average Response**.
- **Action**: These zones yield the highest ROI for new resources. Improving speed here impacts the maximum number of people?
