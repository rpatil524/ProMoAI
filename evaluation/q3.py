import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Work on the current event log
log_df = api.event_log.copy()

# Ensure proper types and sort for sequence analysis
log_df["time:timestamp"] = pd.to_datetime(log_df["time:timestamp"], errors="coerce")
log_df = log_df.dropna(subset=["case:concept:name", "concept:name", "time:timestamp"])
log_df = log_df.sort_values(["case:concept:name", "time:timestamp"])

# Create next-event information within each case
log_df["next_activity"] = log_df.groupby("case:concept:name")["concept:name"].shift(-1)
log_df["next_timestamp"] = log_df.groupby("case:concept:name")["time:timestamp"].shift(-1)

# Compute waiting time between consecutive events
log_df["waiting_time_hours"] = (
    (log_df["next_timestamp"] - log_df["time:timestamp"]).dt.total_seconds() / 3600.0
)

# Keep only valid transitions
transitions_df = log_df.dropna(subset=["next_activity", "waiting_time_hours"]).copy()
transitions_df = transitions_df[transitions_df["waiting_time_hours"] >= 0]

# Add transition label
transitions_df["transition"] = (
    transitions_df["concept:name"] + " -> " + transitions_df["next_activity"]
)

# Aggregate waiting times per transition
transition_wait_summary = (
    transitions_df.groupby(["concept:name", "next_activity", "transition"])["waiting_time_hours"]
    .agg(
        count="count",
        mean_wait_hours="mean",
        median_wait_hours="median",
        std_wait_hours="std",
        p90_wait_hours=lambda x: x.quantile(0.90),
        p95_wait_hours=lambda x: x.quantile(0.95),
        max_wait_hours="max"
    )
    .reset_index()
    .sort_values(["mean_wait_hours", "median_wait_hours"], ascending=False)
)

# Save detailed transition waiting times
api.save_dataframe(
    transition_wait_summary,
    description="Waiting time statistics in hours between consecutive activities for each directly observed transition. Useful for identifying potential chokeholds based on long delays."
)

# Identify potential chokeholds:
# focus on frequent transitions with high median/mean waiting times
min_count = 30
chokeholds_df = transition_wait_summary[transition_wait_summary["count"] >= min_count].copy()
chokeholds_df = chokeholds_df.sort_values(
    ["median_wait_hours", "mean_wait_hours", "p90_wait_hours"],
    ascending=False
).head(20)

api.save_dataframe(
    chokeholds_df,
    description="Top potential chokehold transitions: frequent activity-to-activity transitions with the highest waiting times in hours."
)

# Visualize top chokeholds by median waiting time
top_plot_df = chokeholds_df.sort_values("median_wait_hours", ascending=True)

fig, ax = plt.subplots(figsize=(12, 8))
ax.barh(top_plot_df["transition"], top_plot_df["median_wait_hours"])
ax.set_title("Potential Chokeholds by Median Waiting Time")
ax.set_xlabel("Median waiting time (hours)")
ax.set_ylabel("Transition")

api.save_visualization(
    fig,
    description="Horizontal bar chart of the most likely chokeholds, defined as frequent transitions with the highest median waiting times between activities.",
    data=top_plot_df[["transition", "count", "mean_wait_hours", "median_wait_hours", "p90_wait_hours", "p95_wait_hours", "max_wait_hours"]]
)

# Also provide a broader view of waiting time distribution across all transitions
all_wait_summary = transitions_df["waiting_time_hours"].describe(
    percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
).reset_index()
all_wait_summary.columns = ["statistic", "waiting_time_hours"]

api.save_dataframe(
    all_wait_summary,
    description="Overall descriptive statistics of waiting times in hours between consecutive activities across the entire process."
)

# Visualize overall waiting time distribution
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.hist(transitions_df["waiting_time_hours"], bins=50)
ax2.set_title("Distribution of Waiting Times Between Activities")
ax2.set_xlabel("Waiting time (hours)")
ax2.set_ylabel("Number of transitions")

api.save_visualization(
    fig2,
    description="Histogram of waiting times in hours between consecutive activities across all cases and transitions.",
    data=transitions_df[["case:concept:name", "concept:name", "next_activity", "transition", "waiting_time_hours"]]
)

# Return the event log unchanged
final_event_log = api.event_log