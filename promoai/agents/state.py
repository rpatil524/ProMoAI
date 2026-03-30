from typing import Any, Dict, List, Tuple

from pm4py.objects.log.obj import EventLog

from promoai.general_utils.artifact_store import (
    append_manifest_entry,
    create_analysis_session,
)


class ProcessState(dict):
    user_request: List[str]

    # ---- Data Objects ---- #
    event_log: EventLog

    previous_code: str
    # --- Meta Data and Abstractions --- #
    log_abstraction: str

    discovered_model: Tuple[Any, Any, Any]

    saved_artifacts: Dict[str, Any]

    context: List[str]

    log_actions: Dict[str, List[str]]

    final_report: List[Dict[str, Any]]

    messages_ana: List[Any]

    messages_eng: List[Any]

    extracted_statistics: Dict[str, Any]

    analysis_data: Dict[str, Any]

    # To keep track of sent artifacts to the analyst so we spare tokens
    sent_artifacts: List[str]

    artifact_session_dir: str
    source_log_path: str | None

    def __init__(
        self,
        user_request: str,
        event_log: EventLog,
        artifact_session_dir: str | None = None,
        source_log_path: str | None = None,
    ):
        super().__init__()
        self["user_request"] = [user_request]
        if event_log is None:
            raise ValueError(
                "Event log cannot be None. Please provide a valid event log to initialize the ProcessState."
            )
        self["event_log"] = event_log
        self["artifact_session_dir"] = artifact_session_dir or create_analysis_session(
            "pmax"
        )
        self["source_log_path"] = source_log_path
        self["log_abstraction"] = self.generate_log_abstraction()
        self["discovered_model"] = None
        self["saved_artifacts"] = {}
        self["context"] = []
        self["previous_code"] = ""
        self["log_actions"] = {}
        self["final_report"] = []
        self["messages_ana"] = []
        self["messages_eng"] = []
        self["extracted_statistics"] = {}
        self["analysis_data"] = {}
        self["sent_artifacts"] = []
        append_manifest_entry(
            self["artifact_session_dir"],
            category="session",
            file_path=self["artifact_session_dir"],
            description="Initialized PMAx analysis session.",
            artifact_type="session",
            extra={"source_log_path": source_log_path},
        )

    def __str__(self):
        return (
            f"ProcessState(\n"
            f"  user_request={self['user_request']},\n"
            f"  log_abstraction={self['log_abstraction']},\n"
            f"  extracted_statistics={self['extracted_statistics']},\n"
            f"  discovered_model={'Available' if self['discovered_model'] else 'None'},\n"
            f"  analysis_data={self['analysis_data']},\n"
            f"  log_actions={self['log_actions']},\n"
            f"  final_report={self['final_report'][:100]}..., \n"
            f"  messages_ana=[{len(self['messages_ana'])} messages]\n"
            f"  messages_eng=[{len(self['messages_eng'])} messages]\n"
            f")"
        )

    def __repr__(self):
        return self.__str__()

    def generate_log_abstraction(self):
        df = self["event_log"]

        if df is None or len(df) == 0:
            return "The event log is empty."

        # Basic Stats
        msg = f"Event Log Abstraction:\n"
        msg += f"- Total Events: {len(df)}\n"
        msg += f"- Total Cases: {df['case:concept:name'].nunique() if 'case:concept:name' in df.columns else 'N/A'}\n"
        if "concept:name" in df.columns:
            msg += f"- Unique activities: {df['concept:name'].dropna().unique().tolist()}\n"
        msg += "- Columns & Samples:\n"

        for col in df.columns:
            col_type = df[col].dtype

            sample_data = df[col].dropna().unique()[:10].tolist()

            if "datetime" in str(col_type):
                sample_data = [str(x) for x in sample_data]

            msg += f"  * '{col}' (Type: {col_type}): {sample_data}\n"

        return msg

    def add_context(self, description: str):
        self["context"].append(description)

    def log_action(self, description: str):
        key = "Preprocessor Node"
        if key not in self["log_actions"]:
            self["log_actions"][key] = []
        self["log_actions"][key].append(description)

    def save_model(self, model: Tuple[Any, Any, Any]):
        self["discovered_model"] = model

    def update_artifacts(self, pathway: str, artifact_description: Any, data: Any):
        self["saved_artifacts"][pathway] = (artifact_description, data)

    def wipe_artifacts(self):
        self["saved_artifacts"] = {}

    def flush_context(self):
        self["context"] = []
