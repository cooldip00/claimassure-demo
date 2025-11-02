from typing import Type, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

class ReadHistoryArgs(BaseModel):
    policy_holder: str = Field(..., description="Full name of policy holder")
    policy_number: str = Field(..., description="Policy number")

class UpdateHistoryArgs(BaseModel):
    customer_name: str
    policy_number: str
    claim_number: str
    approved_amount: float
    status: str

class MCPReadHistoryAdapter(BaseTool):
    # Allow arbitrary types so we can hold a live MCP tool instance
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Read Customer Claim History Tool (MCP-backed)"
    description: str = "CrewAI adapter that calls the MCP implementation to read total claimed amount."
    args_schema: Type[BaseModel] = ReadHistoryArgs

    # store the mcp tool instance as a field excluded from serialization
    mcp_tool: Any = Field(default=None, exclude=True)

    def __init__(self, mcp_tool):
        super().__init__(mcp_tool=mcp_tool)

    def _run(self, policy_holder: str, policy_number: str) -> str:
        payload: Dict[str, Any] = {
            "policy_holder": policy_holder,
            "policy_number": policy_number
        }
        res = self.mcp_tool.execute(payload)
        return str(res)

class MCPUpdateHistoryAdapter(BaseTool):
    # Allow arbitrary types so we can hold a live MCP tool instance
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Update Claim History Database Tool (MCP-backed)"
    description: str = "CrewAI adapter that calls the MCP implementation to append an approved claim."
    args_schema: Type[BaseModel] = UpdateHistoryArgs

    mcp_tool: Any = Field(default=None, exclude=True)

    def __init__(self, mcp_tool):
        super().__init__(mcp_tool=mcp_tool)

    def _run(self, customer_name: str, policy_number: str, claim_number: str, approved_amount: float, status: str) -> str:
        payload: Dict[str, Any] = {
            "customer_name": customer_name,
            "policy_number": policy_number,
            "claim_number": claim_number,
            "approved_amount": approved_amount,
            "status": status
        }
        res = self.mcp_tool.execute(payload)
        return str(res)
