import code
import pm4py
import powl
import pandas as pd
from pm4py.objects import petri_net as PNet
from pm4py.objects.log import EventLog
from promoai.agents.utils import __check_code_for_compilation, __check_whitelisted_libraries
from typing import Any
import os
import re
from promoai.model_generation.code_extraction import (
    execute_code_and_get_variable,
)


class PM4PYWrapper:
    def __init__(self, log_path):
        # ==== Load event log ==== #
        self.event_log = self.load_event_log(log_path)
        # ========================= #
        self.pnet = None
        self.powl = None
        self.execution_log = []
        self.context_to_pass_down = []
    @staticmethod
    def get_API_summary() -> str:
        return (
        """
        You have access to a variable `api` which is an instance of the Process Mining Engine.
        
        AVAILABLE METHODS:
        1. Filtering (Updates the log in-place):
           - api.filter_time_range(start_date: str, end_date: str) -> "YYYY-MM-DD"
           - api.filter_attribute(column: str, value: str)
           - api.filter_pandas_query(query: str) -> e.g. "amount > 500"
        
        2. Abstraction (Returns text summary):
           - api.get_dfg_summary()
           - api.get_variant_summary()
        
        3. Mining & Analysis:
           - api.discover_process_model() -> returns nothing, updates internal state.
           - api.check_conformance() -> returns dict with fitness/precision.
        
        RULES:
        - DO NOT import `PM4PYWrapper`. Use the existing `api` object.
        - DO NOT return the log. The `api` object manages state internally.
        """
        )
    def _add_context(self, description: str, data: Any):
        self.context_to_pass_down.append((description, data))       
    def _log_action(self, description: str):
        # Check if it already exists, if this is the case, then append it to a list
        self.execution_log.append(description)
        return description

    @staticmethod
    def save_event_log(event_log, file_name: str):
        """
        Used to save an event log to a file.
        """
        root_dir = os.getcwd()
        save_dir = os.path.join(root_dir, "temp")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file_name)
        if file_path.endswith('.xes'):
            if type(event_log) == pd.DataFrame:
                # Transform it to pm4py EventLog
                event_log = pm4py.convert_to_event_log(event_log)
            pm4py.write_xes(event_log, file_path)
        elif file_path.endswith('.csv') or file_path.endswith('.parquet'):
            if type(event_log) == EventLog:
                # Transform it to pandas DataFrame
                event_log = pm4py.convert_to_dataframe(event_log)
            if file_path.endswith('.csv'):
                event_log.to_csv(file_path, index=False)
            else:
                event_log.to_parquet(file_path, index=False)
        else:
            raise ValueError("Unsupported file format. Please use .xes, .csv, or .parquet")
        
    # ===== Preprocessing Methods ===== #
        # --- STEP 1: PREPROCESSOR (Filtering) ---
    def filter_time_range(self, start_date: str, end_date: str):
        """Filters log by timeframe (YYYY-MM-DD). Updates self.df inplace."""
        self.event_log = pm4py.filter_time_range(self.event_log, start_date, end_date, mode='traces_contained')
        msg = f"Filtered log from {start_date} to {end_date}. Remaining cases: {len(self.event_log)}"
        return self._log_action(msg)


    def filter_attribute(self, column: str, value: str):
        """Filters specific attribute (e.g., org:resource == 'UserA')."""
        self.event_log = pm4py.filter_event_attribute_values(self.event_log, column, [value], level="case")
        msg = f"Filtered cases where {column} contains {value}."
        return self._log_action(msg)

    def filter_pandas_query(self, query: str):
        """Allows complex filtering via pandas query string."""
        if not isinstance(self.event_log, pd.DataFrame):
            self.event_log = pm4py.convert_to_dataframe(self.event_log)
        self.event_log = self.event_log.query(query)
        msg = f"Applied pandas query filter: {query}"
        return self._log_action(msg)


    # ===== LLM-based Abstractions ===== #

    def get_dfg_summary(self) -> str:
        summary = pm4py.llm.abstract_dfg(self.event_log)
        return self._add_context("DFG Summary", summary)
    
    def get_model_summary(self) -> str:
        if self.pnet is None:
            raise ValueError("Process model not discovered yet. Please run discover_process_model() first.")
        net, im, fm = self.pnet
        return self._add_context("Model Summary", pm4py.llm.abstract_petri_net(net, im, fm))
    
    def get_variant_summary(self) -> str:
        return self._add_context("Variant Summary", pm4py.llm.abstract_variants(self.event_log))
    
    def get_case_summary(self) -> str:
        return self._add_context("Case Summary", pm4py.llm.abstract_cases(self.event_log))
        
    
    # ===== Process Mining Algorithms ===== #
    
    def discover_process_model(self) -> PNet:
        self.powl = powl.discover(self.event_log)
        net, im, fm = self.powl.convert_to_petri_net(self.powl)
        self.pnet = (net, im, fm)
        return net, im, fm
    
    def cc_alignments(self, net: PNet, im, fm) -> dict:
        fitness = pm4py.conformance_diagnostics_alignments(self.event_log, net, im, fm)
        precision = pm4py.precision_alignments(self.event_log, net, im, fm)

        self.statistics.update({'Alignments Fitness': fitness, 'Alignments Precision': precision})
        return {
            "fitness": fitness,
            "precision": precision,
            "F1_score": 2 * (fitness * precision) / (fitness + precision) if (fitness + precision) > 0 else 0
        }
    
    def cc_token_based_replay(self, net: PNet, im, fm) -> dict:
        fitness = pm4py.conformance_diagnostics_token_based_replay(self.event_log, net, im, fm)
        precision = pm4py.precision_token_based_replay(self.event_log, net, im, fm)
        self.statistics.update({'Token-based Replay Fitness': fitness, 'Token-based Replay Precision': precision})
        return {
            "fitness": fitness,
            "precision": precision,
            "F1_score": 2 * (fitness * precision) / (fitness + precision) if (fitness + precision) > 0 else 0
        }
    @staticmethod
    def code_extraction(code_snippet: str) -> str:
        """
        Extracts code from a given code snippet, removing any markdown formatting.
        """
        # Check that the code is wrapped in ```python ... ```
        pattern = r"```python\s*(.*?)\s*```"
        match = re.search(pattern, code_snippet, re.DOTALL)

        if not match:
            raise ValueError("Code snippet is not properly formatted with ```python ... ```")

        code = match.group(1).strip()        
        __check_whitelisted_libraries(code)
        __check_code_for_compilation(code)
        return execute_code_and_get_variable(code, "final_event_log")



