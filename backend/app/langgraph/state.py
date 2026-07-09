from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict):
    conversation: List[Dict[str, str]]
    doctor: Optional[str]
    hospital: Optional[str]
    entities: Dict[str, Any]
    summary: Optional[str]
    intent: Optional[str]
    interaction: Optional[Dict[str, Any]]
    database_result: Optional[Dict[str, Any]]
    tool_used: Optional[str]
    response: Optional[str]
    user_id: Optional[int]
    pending_deletion: Optional[Dict[str, Any]]
