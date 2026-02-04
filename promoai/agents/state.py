from typing import TypedDict, Any, List

class ProcessState(TypedDict):
    user_request: str 

    log_abstraction: dict

    extracted_statistics: dict 
    
    discovered_model: dict | None
    
    final_report: str
    
    messages: List[Any]

    def check_types(self) -> bool:
        assert isinstance(self['user_request'], str)
        assert isinstance(self['log_abstraction'], dict)
        assert isinstance(self['extracted_statistics'], dict)
        assert (isinstance(self['discovered_model'], dict) or self['discovered_model'] is None)
        assert isinstance(self['final_report'], str)
        assert isinstance(self['messages'], list)
        return True

