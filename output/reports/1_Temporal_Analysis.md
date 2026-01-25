# Temporal Analysis V2: Multidimensional Insights

This report enhances the basic volumetry with critical operational insights: Gridlock, Risk Profiles, Shift Vulnerabilities, and Weather Impact.

## 1. The Gridlock: Volume vs. Speed
Does high volume always mean slow service?
We examine the relationship between **Incident Volume** (Bar) and **Travel Time** (Line) by hour.

![Gridlock Analysis](/output/figures/temporal_v2/gridlock_analysis.png)
> Note for Thib: **8/10** (on the scale of "my god we learn a lot from this :)") This is our "reality check." We’re seeing something vital here: "busy" doesn't necessarily mean "slow." Look at how the incident volume peaks in the afternoon, but our worst travel times are actually at 7 AM, right when the city wakes up and hits the bridges. For the chiefs, this is actionable intelligence. We can tell them that adding more trucks in the morning won't help if they're stuck in traffic; instead, we need to recommend pre-positioning units at key access points before the 7 AM rush hits. We're showing them exactly when their mobility is compromised, regardless of the call volume.

*Insight*: Look for divergence. If volume drops but travel time stays high (e.g., late rush hour), traffic is the bottleneck, not demand.

## 2. Risk Heatmap: When do specific incidents happen?
A heatmap of Incident Types vs. Hour of Day.

![Risk Heatmap](/output/figures/temporal_v2/risk_heatmap.png)
> Note for Thib: **7/10** This is perfect for winning staffing arguments. It’s obvious that medical calls are our bread and butter during the day, but look at the "Structural Fires" column, that risk flatlines and stays present all night long. We can use this to warn command: just because call volume drops at 3 AM doesn't mean the danger does. If they try to cut overnight fire crews to save money, we pull up this chart to show that the lethal incidents don't respect office hours. It justifies keeping the heavy equipment manned 24/7.

*Insight*: Observe the "Morning Medical" surge vs. "Evening Fire/Accident" patterns. This justifies specialized unit deployment.

## 3. Shift Change Vulnerability
Analyzing **Dispatch Time** specifically.
Vertical lines mark standard shift changes (09:00 and 18:00).

![Shift Change](/output/figures/temporal_v2/shift_change.png)
> Note for Thib: **9/10** This is the "smoking gun" management loves. We caught a massive inefficiency right here. Look at that spike in dispatch time leading up to 6 PM, it shoots up to over 65 seconds exactly when the shift change happens. That is pure friction, crews swapping radios, finishing paperwork, or just chatting during handover. If we show this to leadership, we’re handing them a "free" win. They don’t need more budget to fix this; they just need to tighten up the 6 PM handover protocol to match the smoother morning shift. We just found them 25 free seconds per call.

> It a big maybe though, but clearly needs to be investigated. (not by us because I don't think we can afford to play detective in the time that we have)

*Insight*: If the purple line spikes near the orange/green lines, the handover process is causing delays.

## 4. Weather Impact
Correlation between **Temperature** and **Volume**.
Linear regression shows the trend.

![Weather Volume](/output/figures/temporal_v2/weather_volume.png)
*Insight*: Extreme temperatures (Hot > 90°F or Cold < 30°F) often correlating with higher volumes (Heat stress / Heating fires).

> Note for Thib: **6/10** This is our seasonal forecaster. It's like "eh" though... We’ve proved that as the thermometer climbs, so does the call volume, right up until it gets too hot to move. This isn't just trivia; but it’s just a very obvious planning tool that's about it really. We can tell the operational planners, "Don't schedule heavy training exercises or maintenance downtime when the forecast hits 80°F (freedom units whooooooooo)," because we know for a fact the system is going to be running hot. It helps them stop reacting to the summer surge and start expecting it.