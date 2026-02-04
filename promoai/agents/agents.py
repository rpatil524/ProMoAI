from promoai.agents.state import ProcessState
from promoai.agents.pm4py_wrapper import PM4PYWrapper as api
from promoai.agents.utils import __check_whitelisted_libraries, __check_code_for_compilation
from promoai.general_utils.llm_connection import generate_result_with_error_handling
from promoai.general_utils.llm_connection import LLMConnection


def preprocesser_node(state : ProcessState, LLMCredentials : LLMConnection):
    # 1. Construct Prompt
    api_summary = api.get_API_summary()
    
    msg = f"""
    You are a Process Mining Data Engineer.
    User Request: "{state['user_request']}"
        
    API CHEATSHEET:
    {api_summary} \n

    DATA: \n
    Assume that the log is already loaded and accessible via api.event_log. \n
    Furthermore, the data has the following structure: {state['log_abstraction']} \n


    TASK:
    - If the user asks to filter (e.g. "only 2023", "remove attribute X"), write Python code to call `api.filter...`. \n
    - If no filtering is needed, output "pass". \n
    REQUIREMENTS:
    - You can only use the `api` object to interact with the event log, as well as pandas for advanced data manipulation (if needed). \n
    - Ensure that the generated code adheres to the whitelisted libraries and can compile without errors \n
    - Output ONLY code. No markdown.
    - Return the final event log as `final_event_log` variable.
    """
    msg_history = {"role": "user", "content": msg}
    generate_result_with_error_handling(msg_history,
                            extraction_function = api.code_extraction,
                            llm_name=LLMCredentials.llm_name,
                            ai_provider=LLMCredentials.ai_provider,
                            api_key=LLMCredentials.api_key,
                            llm_args=LLMCredentials.args,
                            max_iterations=3,
                            additional_iterations=2)
    
    
            

def analyst_node(state: ProcessState):
    # The prompt adapts to the data provided
    msg = f"""
    You are a Process Mining Expert. 
    The user asked: "{state['user_request']}"
    
    Here is the generated data up to this moment:
    {state['analysis_data']}
    
    Interpret this data for a business user.
    """
