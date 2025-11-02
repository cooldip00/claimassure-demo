import os
from collections.abc import AsyncGenerator
import typing as _t
import uvicorn
import yaml
from dotenv import load_dotenv

# Load environment variables from the .env file (if present)
load_dotenv()

_cfg = uvicorn.config

# Provide LoopSetupType if missing (older SDKs expect Literal)
if not hasattr(_cfg, "LoopSetupType"):
    try:
        from typing import Literal as _Literal
        _cfg.LoopSetupType = _Literal["none", "auto", "asyncio", "uvloop"]  # type: ignore[attr-defined]
    except Exception:
        _cfg.LoopSetupType = _t.Any  # type: ignore[attr-defined]

# # Provide LoopSetupType if missing (older SDKs expect Literal)
# if not hasattr(_cfg, "LoopSetupType"):
#     try:
#         from typing import Literal as _Literal
#         _cfg.LoopSetupType = _Literal[\"none\", \"auto\", \"asyncio\", \"uvloop\"]  # type: ignore[attr-defined]
#     except Exception:
#         _cfg.LoopSetupType = _t.Any  # type: ignore[attr-defined]

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server

from crewai import Crew, Task, Agent, LLM, Process
import nest_asyncio

# CrewAI tools used by agents
from tools.document_load import DirectoryLoaderTool
from tools.history_tools import ReadCustomerHistoryTool, UpdateClaimHistoryTool
from tools.acp_claim_verifier_bridge_tool import ACPClaimRetrieverBridgeTool

# MCP-native tools (no CrewAI dependency)
from tools.mcp_history_tools import ReadCustomerHistoryMCP, UpdateClaimHistoryMCP
from tools.mcp_adapters import MCPReadHistoryAdapter, MCPUpdateHistoryAdapter



server = Server()
llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)

file_tool = DirectoryLoaderTool()
bridge_tool = ACPClaimRetrieverBridgeTool()
nest_asyncio.apply()


class MCPServer:
    def __init__(self, tools):
        # tools must implement .name, .description, .execute(dict)->dict
        self.tools = {tool.name: tool for tool in tools}

    def list_tools(self):
        return [tool for tool in self.tools.values()]

    def call_tool(self, tool_name, tool_params):
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        if hasattr(tool, "execute"):
            return tool.execute(tool_params or {})
        if hasattr(tool, "run"):
            return tool.run(tool_params or {})
        return {"success": False, "error": "Tool has neither 'execute' nor 'run'."}


class MCPClient:
    """A client to interact with the MCPServer."""
    def __init__(self, server: MCPServer):
        self.server = server
    def list_tools(self):
        return [tool for tool in self.server.list_tools()]
    def call_tool(self, tool_name: str, tool_params: dict) -> dict:
        return self.server.call_tool(tool_name, tool_params)


def format_tools_for_llm_simple(tools):
    """Formats tools with only name and description."""
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)

# Register MCP-native tools on the MCP server
mcp_tools = [ReadCustomerHistoryMCP(), UpdateClaimHistoryMCP()]
mcp_server = MCPServer(mcp_tools)
mcp_client = MCPClient(server=mcp_server)
available_tools_from_server = mcp_server.list_tools()
formatted_tools = format_tools_for_llm_simple(available_tools_from_server)

@server.agent()
async def policy_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    CrewAI pipeline returning only:
      - final_statement: str
      - email: {to, subject, body_text, body_html?}
    Internally still runs A1..A4 and uses their outputs as context for A5 (statement) and A6 (email).
    """
    import json
    # from pydantic import BaseModel, Field, EmailStr
    # from typing import Any, Dict, Optional
    # from pydantic import ConfigDict  # pydantic v2

    upload_dir = None
    try:
        if messages and messages[-1].parts:
            raw = messages[-1].parts[0].content
            if isinstance(raw, str):
                import json as _json
                try:
                    obj = _json.loads(raw)
                except Exception:
                    obj = {}
            elif isinstance(raw, dict):
                obj = raw
            else:
                obj = {}
            upload_dir = (obj or {}).get("upload_dir")
    except Exception:
        upload_dir = None

    from pydantic import BaseModel, Field, EmailStr
    from pydantic import ConfigDict
    from typing import Any, Dict, Optional  # <-- use Optional, not X | None

    class A1ClassifyValidate(BaseModel):
        validation_status: str = Field(..., alias="Validation-Status")
        validation_message: str = Field(..., alias="Validation-Message")
        document_content: str = Field(..., alias="Document-Content")
        model_config = ConfigDict(populate_by_name=True)

    class A2Extract(BaseModel):
        status: str = Field(..., alias="status")
        message: str = Field(..., alias="message")

        # Accept both your YAML field names & common variants via aliases
        policy_holder: Optional[str] = Field(None, alias="Policy_Holder")
        claim_number: Optional[str] = Field(None, alias="Claim_Number")
        policy_number: Optional[str] = Field(None, alias="Policy_Number")
        hospital_name: Optional[str] = Field(None, alias="Hospital Name")
        invoice_number: Optional[str] = Field(None, alias="Invoice Number")
        claim_amount: Optional[str] = Field(None, alias="Claim_Amount")
        email: Optional[str] = Field(None, alias="Email")
        maximum_claim_limit: Optional[str] = Field(None, alias="Maximum Claim Limit")
        # Alternate keys sometimes seen
        policy_holder_full_name: Optional[str] = Field(None, alias="Policy Holder's Full Name")
        total_claim_amount: Optional[str] = Field(None, alias="Total Claim Amount")

        model_config = ConfigDict(populate_by_name=True)

    class VerificationDetails(BaseModel):
        status: str
        message: str

    class A3Verify(BaseModel):
        original_data: Dict[str, Any]
        hospital_record: Dict[str, Any]
        verification_details: VerificationDetails

    class A4Decision(BaseModel):
        customer_name: str = Field(..., alias="Customer Name")
        policy_number: str = Field(..., alias="Policy Number")
        final_decision: str = Field(..., alias="Final Decision")
        amount_approved: Optional[float] = Field(None, alias="Amount Approved")
        confirmation: Optional[str] = Field(None, alias="Confirmation")
        rejection_reason: Optional[str] = Field(None, alias="Rejection Reason")
        model_config = ConfigDict(populate_by_name=True)

    class A5Statement(BaseModel):
        statement: str

    class A6Email(BaseModel):
        to: Optional[EmailStr] = None
        subject: str
        body_text: str
        body_html: Optional[str] = None

    # # ----- A1..A4 schemas -----
    # class A1ClassifyValidate(BaseModel):
    #     # Map the hyphen/cased keys from LLM output to snake_case fields
    #     validation_status: str = Field(..., alias="Validation-Status")
    #     validation_message: str = Field(..., alias="Validation-Message")
    #     document_content: str = Field(..., alias="Document-Content")
    #     model_config = ConfigDict(populate_by_name=True)

    # class A2Extract(BaseModel):
    #     # The task’s examples use these exact keys; give aliases for robustness
    #     status: str = Field(..., alias="status")
    #     message: str = Field(..., alias="message")

    #     # Common variations you've shown in examples / prompt text
    #     policy_holder: str | None = Field(None, alias="Policy_Holder")
    #     claim_number: str | None = Field(None, alias="Claim_Number")
    #     policy_number: str | None = Field(None, alias="Policy_Number")
    #     hospital_name: str | None = Field(None, alias="Hospital Name")
    #     invoice_number: str | None = Field(None, alias="Invoice Number")
    #     claim_amount: str | None = Field(None, alias="Claim_Amount")
    #     email: str | None = Field(None, alias="Email")
    #     maximum_claim_limit: str | None = Field(None, alias="Maximum Claim Limit")

    #     # If the extractor writes slightly different keys, also accept these:
    #     policy_holder_full_name: str | None = Field(None, alias="Policy Holder's Full Name")
    #     total_claim_amount: str | None = Field(None, alias="Total Claim Amount")

    #     model_config = ConfigDict(populate_by_name=True)

    # class VerificationDetails(BaseModel):
    #     status: str
    #     message: str

    # class A3Verify(BaseModel):
    #     original_data: dict
    #     hospital_record: dict
    #     verification_details: VerificationDetails

    # class A4Decision(BaseModel):
    #     customer_name: str = Field(..., alias="Customer Name")
    #     policy_number: str = Field(..., alias="Policy Number")
    #     final_decision: str = Field(..., alias="Final Decision")
    #     amount_approved: float | None = Field(None, alias="Amount Approved")
    #     confirmation: str | None = Field(None, alias="Confirmation")
    #     rejection_reason: str | None = Field(None, alias="Rejection Reason")
    #     model_config = ConfigDict(populate_by_name=True)

    # class A5Statement(BaseModel):
    #     statement: str

    # class A6Email(BaseModel):
    #     to: EmailStr | None = None
    #     subject: str
    #     body_text: str
    #     body_html: str | None = None
        
    # class A1ClassifyValidate(BaseModel):
    #     validation_status: str
    #     validation_message: str
    #     document_content: str

    # class A2Extract(BaseModel):
    #     status: str
    #     message: str
    #     policy_holder: Optional[str] = None
    #     claim_number: Optional[str] = None
    #     policy_number: Optional[str] = None
    #     hospital_name: Optional[str] = None
    #     invoice_number: Optional[str] = None
    #     claim_amount: Optional[str] = None
    #     email: Optional[str] = None
    #     maximum_claim_limit: Optional[str] = None

    # class VerificationDetails(BaseModel):
    #     status: str
    #     message: str

    # class A3Verify(BaseModel):
    #     original_data: Dict[str, Any]
    #     hospital_record: Dict[str, Any]
    #     verification_details: VerificationDetails

    # class A4Decision(BaseModel):
    #     customer_name: str = Field(..., alias="Customer Name")
    #     policy_number: str = Field(..., alias="Policy Number")
    #     final_decision: str = Field(..., alias="Final Decision")
    #     amount_approved: Optional[float] = Field(None, alias="Amount Approved")
    #     confirmation: Optional[str] = Field(None, alias="Confirmation")
    #     rejection_reason: Optional[str] = Field(None, alias="Rejection Reason")
    #     class Config: populate_by_name = True

    # # ----- NEW: A5/A6 schemas -----
    # class A5Statement(BaseModel):
    #     statement: str

    # class A6Email(BaseModel):
    #     to: Optional[EmailStr] = None
    #     subject: str
    #     body_text: str
    #     body_html: Optional[str] = None

    def _safe(obj):
        try:
            if isinstance(obj, (dict, list)):
                return json.dumps(obj, ensure_ascii=False, indent=2)
            return str(obj)
        except Exception:
            return repr(obj)

    with open('config/agents.yaml', 'r') as file:
        agents_config = yaml.safe_load(file)
    with open('config/tasks.yaml', 'r') as file:
        tasks_config = yaml.safe_load(file)

    # ----- Agents -----
    A1 = Agent(config=agents_config["DocumentClassifierAgent"], llm=llm, verbose=True)
    A2 = Agent(config=agents_config["ClaimDataExtractorAgent"], llm=llm, verbose=True)
    A3_ExternalVerifier = Agent(config=agents_config["ExternalVerifierAgent"], tools=[bridge_tool], llm=llm, verbose=True)

    crew_history_tools = [
        MCPReadHistoryAdapter(ReadCustomerHistoryMCP()),
        MCPUpdateHistoryAdapter(UpdateClaimHistoryMCP())
    ]

    A4_PolicyAdjudicator = Agent(
        config=agents_config["PolicyAdjudicatorAgent"],
        tools=crew_history_tools,
        llm=llm,
        verbose=True
    )

    # NEW agents
    A5_Statement = Agent(config=agents_config["StatementSynthesizerAgent"], llm=llm, verbose=True)
    A6_Email = Agent(config=agents_config["EmailComposerAgent"], llm=llm, verbose=True)

    # ----- Tasks (A1..A4) with structured outputs -----
    T1 = Task(
        config=tasks_config["classify_and_validate_documents"],
        agent=A1,
        tools=[file_tool],
        output_pydantic=A1ClassifyValidate
    )

    if upload_dir:
        extra = (
            "\n\nIMPORTANT:\n"
            f"- Use DirectoryLoaderTool with directory_path EXACTLY as: '{upload_dir}'.\n"
            "- Do not guess or change the folder name.\n"
        )
        T1.description = (T1.description or "") + extra

        # Also set an env var as a secondary fallback the tool can pick up
        os.environ["UPLOAD_DIR"] = upload_dir

    T2 = Task(
        config=tasks_config["extract_claim_details"],
        agent=A2,
        context=[T1],
        output_pydantic=A2Extract
    )
    T3 = Task(
        config=tasks_config["external_verification"],
        agent=A3_ExternalVerifier,
        context=[T2],
        output_pydantic=A3Verify
    )
    T4 = Task(
        config=tasks_config["manage_history_and_decide"],
        agent=A4_PolicyAdjudicator,
        context=[T3],
        tools=crew_history_tools,
        output_pydantic=A4Decision
    )

    # Safe placeholder replacement
    if "{available_tools}" in (T4.description or ""):
        safe_desc = T4.description.replace("{available_tools}", formatted_tools)
        T4.description = safe_desc

    T4.description = (T4.description or "") + "\n\nReturn ONLY valid JSON matching the output schema. No prose, no code fences."
    
    # ----- NEW Tasks (A5, A6) -----
    T5 = Task(
        config=tasks_config["synthesize_final_statement"],
        agent=A5_Statement,
        context=[T1, T2, T3, T4],
        output_pydantic=A5Statement
    )

    T6 = Task(
        config=tasks_config["compose_email_to_policyholder"],
        agent=A6_Email,
        context=[T5, T4, T2],  # include extractor to pick up email
        output_pydantic=A6Email
    )

    crew = Crew(
        agents=[A1, A2, A3_ExternalVerifier, A4_PolicyAdjudicator, A5_Statement, A6_Email],
        tasks=[T1, T2, T3, T4, T5, T6],
        process=Process.sequential,
        verbose=True
    )

    # final_obj = await crew.kickoff_async()
    try:
        final_obj = await crew.kickoff_async()
    except Exception as e:
        import traceback
        traceback.print_exc()
        err = {
            "error": "Pipeline execution failed",
            "details": repr(e)
        }
        yield Message(parts=[MessagePart(content=json.dumps(err, ensure_ascii=False))])
        return


    # Auto-fill "to" from extraction if missing
    try:
        extract_email = getattr(T2.output.pydantic, "email", None) if getattr(T2, "output", None) else None
        email_obj = T6.output.pydantic.model_dump()
        if (email_obj.get("to") in (None, "", "null")) and extract_email:
            email_obj["to"] = extract_email
            # reattach for unified response
            T6.output.pydantic = type(T6.output.pydantic)(**email_obj)  # reconstruct
    except Exception:
        pass

    def dump_pyd(task):
        try:
            if getattr(task, "output", None) and getattr(task.output, "pydantic", None):
                return task.output.pydantic.model_dump()
        except Exception:
            pass
        return None

    statement_obj = dump_pyd(T5) or {"statement": "<unavailable>"}
    email_obj = dump_pyd(T6) or {"subject": "<unavailable>", "body_text": "<unavailable>"}

    response = {
        "statement": statement_obj.get("statement", ""),
        "email": email_obj
    }

    yield Message(parts=[MessagePart(content=json.dumps(response, ensure_ascii=False))])

if __name__ == "__main__":
    server.run(port=8011)
