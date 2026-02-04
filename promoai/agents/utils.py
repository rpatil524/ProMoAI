import ast


def get_expected_event_log_format() -> str:
    return (
        "The expected event log format is a pandas DataFrame with at least the following columns:\n"
        "- 'case:concept:name': Identifier for each case (string)\n"
        "- 'concept:name': Name of the activity (string)\n"
        "- 'time:timestamp': Timestamp of the event (datetime)\n"
        "- 'org:resource': Resource associated with the event (string), this is optional\n\n"
        "Additional columns may be present, but these are the minimum required for process mining tasks."
    )

def __check_whitelisted_libraries(generated_code: str):
    whitelist = {"pandas", "pm4py", "promoai"}
    try:
        tree = ast.parse(generated_code)
    except SyntaxError as e:
        raise Exception(f"Generated code contains syntax errors: {e}")

    for node in ast.walk(tree):
        # import pandas as pd
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level not in whitelist:
                    raise Exception(f"Generated code contains imports from non-whitelisted libraries: {top_level}")

        # from pm4py.objects.log import x
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                raise Exception("Generated code contains syntax errors: relative imports are not allowed")

            top_level = node.module.split(".")[0]
            if top_level not in whitelist:
                raise Exception(f"Generated code contains imports from non-whitelisted libraries: {top_level}") 


def __check_code_for_compilation(generated_code: str):
    try:
        compile(generated_code, "<string>", "exec")
    except SyntaxError as e:
        raise Exception(f"Generated code contains syntax errors: {e}")
