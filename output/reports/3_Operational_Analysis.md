# Operational Analysis: Efficiency Under Pressure

We move beyond "how fast" to "how efficient". This dashboard answers the hard questions about triage accuracy, system limits, and process bottlenecks.

## 1. The Reality Gap (Sankey Diagram)
**Concept**: Tracing the flow from **Initial Call Type** (What the public reported) to **Final Call Type** (What it actually was).
*Top 20 Misclassifications (Errors Only).*

![Reality Gap](/output/figures/operational_v3/reality_gap_sankey_errors.png)

> Notes for Thib: 10/10 I think it's very good, self-explanatory dare I say. We see that the UNKNOW block on the bottom left sprays out into critical categories like INJURY, SICK, and UNC is the ultimate proof that our initial dispatch intel is often blind, while the clean split of EDP (Psych) into EDPC and EDPM shows where the protocols are actually working. This is your political tool to tell the Chief: "See that massive grey ribbon from 'Unknown' to 'Injury'? That’s your risk exposure that better call-taking scripts could resolve before we roll the trucks."

> Not really a dimension analysis though, it's simple interesting data ;)

## 2. The Stress Test (System Saturation)
**Concept**: A binned analysis of **Total Hourly Unit Load** vs **Dispatch Speed**. We grouped hours by system load (in 20-unit buckets) to find the structural trend.

![Stress Test](/output/figures/operational_v3/stress_test_binned.png)
> Notes for Thib: 9/10 For every extra batch of 50 units we deploy, the system slows down by about 5 seconds. This is kinda cool because it moves the conversation from "we are busy" to "we can mathematically predict delay," allowing command to trigger contingency plans the moment active units hit that 400 mark. I could do ML to actually predict, but I don't want to get in there you feel me ?

*Insight*: **The Breaking Point**.
- Ideally, this line should be flat. In reality, it curves upwards (The "Hockey Stick").
- The trend line shows performance degrading as load increases. Use this to determine the **Maximum Safe Capacity** (e.g. at 300+ units) before dispatch times spiral.

## 3. The Resource Hog (Consumption Analysis)
**Concept**: Total **Operational Capacity Consumed** by Incident Type.
Formula: `Total Units Assigned * Duration of Incident`.

![Resource Consumption](/output/figures/operational_v3/resource_consumption_bar.png)
> Notes for Thib: 8/10 This bar chart is about budget. It’s shocking to see that "NonMedical Emergencies" consume nearly 3x the operational capacity of actual "Medical Emergencies", likely because those complex rescue/hazard events tie up heavy units for hours compared to quick ambulance runs. The pitch here is simple: "We spend most of our time and resources on non-medical events, so we need to optimize our workforce for these long-duration operations, not just for speed."

> Again, just some insight but good thing to have on a dashboard imo

*Insight*: **Where is the Budget Going?**
- A "Structural Fire" might be rare, but if it consumes 10,000 unit-hours, it is the primary driver of fleet wear and overtime costs.
- Use this to justify budget allocation: "We spend 60% of our operational capacity on Category X."

