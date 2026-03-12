import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Work on the current event log
log_df = api.event_log.copy()

# Ensure timestamp is datetime
log_df["time:timestamp"] = pd.to_datetime(log_df["time:timestamp"], errors="coerce")

# Compute case-level throughput times
case_throughput = (
    log_df.groupby("case:concept:name")["time:timestamp"]
    .agg(case_start="min", case_end="max")
    .reset_index()
)

case_throughput["throughput_time_days"] = (
    (case_throughput["case_end"] - case_throughput["case_start"]).dt.total_seconds() / 86400.0
)

# Remove invalid/missing durations
case_throughput = case_throughput.dropna(subset=["throughput_time_days"])
case_throughput = case_throughput[case_throughput["throughput_time_days"] >= 0]

# Save the case-level throughput dataframe
api.save_dataframe(
    case_throughput,
    description="Case-level throughput times computed as the difference between the first and last event timestamp for each case, expressed in days."
)

# Prepare summary statistics
summary_df = case_throughput["throughput_time_days"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).reset_index()
summary_df.columns = ["statistic", "throughput_time_days"]
api.save_dataframe(
    summary_df,
    description="Descriptive statistics of case throughput times in days, including key percentiles to characterize the distribution."
)

# Create histogram
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(case_throughput["throughput_time_days"], bins=50)
ax.set_title("Distribution of Throughput Times")
ax.set_xlabel("Throughput time (days)")
ax.set_ylabel("Number of cases")

api.save_visualization(
    fig,
    description="Histogram showing the distribution of case throughput times across the process, measured in days from first to last event per case.",
    data=case_throughput[["case:concept:name", "throughput_time_days"]]
)

# Create boxplot
fig2, ax2 = plt.subplots(figsize=(10, 3))
ax2.boxplot(case_throughput["throughput_time_days"], vert=False)
ax2.set_title("Boxplot of Throughput Times")
ax2.set_xlabel("Throughput time (days)")

api.save_visualization(
    fig2,
    description="Boxplot summarizing the spread and outliers of case throughput times in days.",
    data=case_throughput[["case:concept:name", "throughput_time_days"]]
)

# Return the event log unchanged
final_event_log = api.event_log