import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Work on current event log
log_df = api.event_log.copy()

# Ensure proper timestamp type
log_df["time:timestamp"] = pd.to_datetime(log_df["time:timestamp"], errors="coerce")

# Identify "requests for completion" via the activity name
# We use a case-insensitive contains match on 'complete application'
completion_mask = log_df["concept:name"].astype(str).str.contains("complete application", case=False, na=False)

# Count number of completion-request related events per case
completion_counts = (
    log_df[completion_mask]
    .groupby("case:concept:name")
    .size()
    .reset_index(name="num_completion_requests")
)

# Derive case-level final offer acceptance indicator from available Accepted column
# If any event in the case has Accepted=True, treat case as accepted
accepted_case = (
    log_df.groupby("case:concept:name")["Accepted"]
    .apply(lambda x: x.astype(str).str.lower().eq("true").any())
    .reset_index(name="accepted_final_offer")
)

# Build case-level analysis table
case_df = (
    log_df[["case:concept:name"]]
    .drop_duplicates()
    .merge(completion_counts, on="case:concept:name", how="left")
    .merge(accepted_case, on="case:concept:name", how="left")
)

case_df["num_completion_requests"] = case_df["num_completion_requests"].fillna(0).astype(int)
case_df["accepted_final_offer"] = case_df["accepted_final_offer"].fillna(False)
case_df["not_accepted_final_offer"] = ~case_df["accepted_final_offer"]

# Aggregate acceptance / non-acceptance rates by number of completion requests
request_effect_df = (
    case_df.groupby("num_completion_requests")
    .agg(
        cases=("case:concept:name", "count"),
        accepted_cases=("accepted_final_offer", "sum"),
        not_accepted_cases=("not_accepted_final_offer", "sum")
    )
    .reset_index()
)

request_effect_df["acceptance_rate"] = request_effect_df["accepted_cases"] / request_effect_df["cases"]
request_effect_df["non_acceptance_rate"] = request_effect_df["not_accepted_cases"] / request_effect_df["cases"]

api.save_dataframe(
    case_df,
    description="Case-level dataset linking the number of completion-request related events to whether the final offer was accepted at least once in the case."
)

api.save_dataframe(
    request_effect_df,
    description="Acceptance and non-acceptance rates by number of completion-request related events per case. Used to assess whether more completion requests are associated with lower offer acceptance."
)

# Restrict to groups with enough support for a more robust visual comparison
plot_df = request_effect_df[request_effect_df["cases"] >= 20].copy()

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(plot_df["num_completion_requests"], plot_df["acceptance_rate"], marker="o", label="Acceptance rate")
ax.plot(plot_df["num_completion_requests"], plot_df["non_acceptance_rate"], marker="o", label="Non-acceptance rate")
ax.set_title("Offer Outcome vs. Number of Completion Requests")
ax.set_xlabel("Number of completion-request related events per case")
ax.set_ylabel("Rate")
ax.legend()

api.save_visualization(
    fig,
    description="Line chart comparing acceptance and non-acceptance rates across cases with different numbers of completion-request related events. Only groups with at least 20 cases are shown.",
    data=plot_df.to_dict(orient="list")
)

# Also compare low vs high completion-request groups using the median split
median_requests = case_df["num_completion_requests"].median()
case_df["request_group"] = np.where(
    case_df["num_completion_requests"] > median_requests,
    "High completion requests",
    "Low completion requests"
)

group_comparison_df = (
    case_df.groupby("request_group")
    .agg(
        cases=("case:concept:name", "count"),
        accepted_cases=("accepted_final_offer", "sum"),
        not_accepted_cases=("not_accepted_final_offer", "sum")
    )
    .reset_index()
)

group_comparison_df["acceptance_rate"] = group_comparison_df["accepted_cases"] / group_comparison_df["cases"]
group_comparison_df["non_acceptance_rate"] = group_comparison_df["not_accepted_cases"] / group_comparison_df["cases"]

api.save_dataframe(
    group_comparison_df,
    description="Comparison of offer acceptance outcomes between cases with high versus low numbers of completion-request related events, using a median split."
)

fig2, ax2 = plt.subplots(figsize=(8, 5))
ax2.bar(group_comparison_df["request_group"], group_comparison_df["non_acceptance_rate"])
ax2.set_title("Non-Acceptance Rate: High vs Low Completion Requests")
ax2.set_xlabel("Completion request group")
ax2.set_ylabel("Non-acceptance rate")

api.save_visualization(
    fig2,
    description="Bar chart comparing non-acceptance rates between cases with high versus low numbers of completion-request related events.",
    data=group_comparison_df.to_dict(orient="list")
)

# Return event log unchanged
final_event_log = api.event_log