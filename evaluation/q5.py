import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Work on current event log
log_df = api.event_log.copy()

# Case-level number of unique offers
offers_per_case = (
    log_df.groupby("case:concept:name")["OfferID"]
    .nunique(dropna=True)
    .reset_index(name="num_offers")
)

# Case-level acceptance outcome:
# treat a case as successful if any event has Accepted == True
accepted_case = (
    log_df.groupby("case:concept:name")["Accepted"]
    .apply(lambda x: x.astype(str).str.lower().eq("true").any())
    .reset_index(name="accepted_final_offer")
)

# Build analysis dataset
case_df = (
    log_df[["case:concept:name"]]
    .drop_duplicates()
    .merge(offers_per_case, on="case:concept:name", how="left")
    .merge(accepted_case, on="case:concept:name", how="left")
)

case_df["num_offers"] = case_df["num_offers"].fillna(0).astype(int)
case_df["accepted_final_offer"] = case_df["accepted_final_offer"].fillna(False)
case_df["more_than_one_offer"] = case_df["num_offers"] > 1

api.save_dataframe(
    case_df,
    description="Case-level dataset containing number of unique offers per customer case and whether the final offer was accepted."
)

# Count customers/cases with more than one offer
offer_count_summary = (
    case_df["more_than_one_offer"]
    .value_counts(dropna=False)
    .rename_axis("more_than_one_offer")
    .reset_index(name="cases")
)

offer_count_summary["share"] = offer_count_summary["cases"] / offer_count_summary["cases"].sum()

api.save_dataframe(
    offer_count_summary,
    description="Number and share of cases with more than one unique offer versus zero or one offer."
)

# Success rate comparison: >1 offer vs baseline process
baseline_success_rate = case_df["accepted_final_offer"].mean()

success_comparison_df = (
    case_df.groupby("more_than_one_offer")
    .agg(
        cases=("case:concept:name", "count"),
        successful_cases=("accepted_final_offer", "sum")
    )
    .reset_index()
)

success_comparison_df["success_rate"] = (
    success_comparison_df["successful_cases"] / success_comparison_df["cases"]
)
success_comparison_df["baseline_success_rate"] = baseline_success_rate
success_comparison_df["difference_vs_baseline"] = (
    success_comparison_df["success_rate"] - success_comparison_df["baseline_success_rate"]
)

api.save_dataframe(
    success_comparison_df,
    description="Success rate comparison between cases with more than one offer and the overall baseline process success rate."
)

# Statistical significance test approximation using bootstrap/permutation-style resampling
# This avoids non-whitelisted imports while still assessing whether the difference is likely due to chance.
group_multi = case_df[case_df["more_than_one_offer"]]
group_other = case_df[~case_df["more_than_one_offer"]]

x1 = int(group_multi["accepted_final_offer"].sum())
n1 = int(group_multi.shape[0])
x2 = int(group_other["accepted_final_offer"].sum())
n2 = int(group_other.shape[0])

if n1 > 0 and n2 > 0:
    p1 = x1 / n1
    p2 = x2 / n2
    observed_diff = p1 - p2

    pooled = case_df["accepted_final_offer"].astype(int).values
    rng = np.random.default_rng(42)
    n_iter = 1000
    simulated_diffs = np.empty(n_iter)

    for i in range(n_iter):
        sample1 = rng.choice(pooled, size=n1, replace=True)
        sample2 = rng.choice(pooled, size=n2, replace=True)
        simulated_diffs[i] = sample1.mean() - sample2.mean()

    p_value = np.mean(np.abs(simulated_diffs) >= abs(observed_diff))
else:
    p1 = np.nan
    p2 = np.nan
    observed_diff = np.nan
    p_value = np.nan

significance_df = pd.DataFrame({
    "comparison": ["more_than_one_offer vs zero_or_one_offer"],
    "group_1_success_rate": [p1],
    "group_2_success_rate": [p2],
    "group_1_cases": [n1],
    "group_2_cases": [n2],
    "observed_rate_difference": [observed_diff],
    "approx_p_value": [p_value],
    "significant_at_0_05": [bool(p_value < 0.05) if pd.notna(p_value) else False],
    "test_method": ["bootstrap_resampling_from_pooled_outcomes"]
})

api.save_dataframe(
    significance_df,
    description="Approximate significance test comparing success rates of cases with more than one offer versus cases with zero or one offer, using bootstrap-style resampling from pooled outcomes."
)

# Visualize success rates
plot_df = success_comparison_df.copy()
plot_df["group"] = plot_df["more_than_one_offer"].map({
    True: "More than 1 offer",
    False: "0 or 1 offer"
})

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(plot_df["group"], plot_df["success_rate"])
ax.axhline(baseline_success_rate, linestyle="--", label="Baseline success rate")
ax.set_title("Success Rate by Offer Count Group")
ax.set_xlabel("Group")
ax.set_ylabel("Success rate")
ax.legend()

api.save_visualization(
    fig,
    description="Bar chart comparing success rates for cases with more than one offer versus cases with zero or one offer, with the overall baseline success rate shown as a dashed line.",
    data=plot_df[["group", "cases", "successful_cases", "success_rate", "difference_vs_baseline"]]
)

# Return event log unchanged
final_event_log = api.event_log