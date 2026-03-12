# Discover and summarize the process without filtering, since the user asks for an overall view
import pandas as pd

api.discover_process_model()

# Save standard process mining visualizations
api.save_pnet()
api.save_dfg()

# Generate textual abstractions for downstream analysis
dfg_summary = api.get_dfg_summary()
model_summary = api.get_model_summary()
variant_summary = api.get_variant_summary()

summary_df = pd.DataFrame({
    "summary_type": ["dfg_summary", "model_summary", "variant_summary"],
    "summary": [dfg_summary, model_summary, variant_summary]
})
api.save_dataframe(
    summary_df,
    description="Textual summaries of the overall process structure, discovered model, and common variants to describe what the process looks like and the typical workflows."
)

# Return the event log unchanged
final_event_log = api.event_log