"""ACP server orchestrating the end-to-end ClaimAssure policy workflow."""

from __future__ import annotations

import json
import os
import traceback
from collections.abc import AsyncGenerator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import nest_asyncio
import uvicorn
import yaml
from dotenv import load_dotenv

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server
from crewai import Agent, Crew, LLM, Process, Task
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from tools.acp_claim_verifier_bridge_tool import ACPClaimRetrieverBridgeTool
from tools.document_load import DirectoryLoaderTool
from tools.mcp_adapters import MCPReadHistoryAdapter, MCPUpdateHistoryAdapter
from tools.mcp_history_tools import ReadCustomerHistoryMCP, UpdateClaimHistoryMCP


# Load environment variables from the .env file (if present)
load_dotenv()


# ---------------------------------------------------------------------------
# Paths & configuration helpers
# ---------------------------------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_ROOT = PROJECT_ROOT / "config"
DEFAULT_UPLOAD_ROOT = Path(
    os.getenv("UPLOADS_ROOT", PROJECT_ROOT / "uploads")
).resolve()


def _ensure_loop_backcompat() -> None:
    """Provide LoopSetupType for older uvicorn versions."""

    cfg = uvicorn.config
    if hasattr(cfg, "LoopSetupType"):
        return
    try:
        from typing import Literal as _Literal  # type: ignore

        cfg.LoopSetupType = _Literal["none", "auto", "asyncio", "uvloop"]  # type: ignore[attr-defined]
    except Exception:
        cfg.LoopSetupType = Any  # type: ignore[name-defined]


_ensure_loop_backcompat()


@lru_cache(maxsize=1)
def _load_yaml(name: str) -> dict:
    with open(CONFIG_ROOT / name, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def _agents_config() -> dict:
    return _load_yaml("agents.yaml")


@lru_cache(maxsize=1)
def _tasks_config() -> dict:
    return _load_yaml("tasks.yaml")


# ---------------------------------------------------------------------------
# ACP server + Crew primitives
# ---------------------------------------------------------------------------


server = Server()
llm = LLM(model="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

file_tool = DirectoryLoaderTool()
bridge_tool = ACPClaimRetrieverBridgeTool()
nest_asyncio.apply()


class MCPServer:
    """Minimal MCP host so Crew agents can reuse MCP-native tooling."""

    def __init__(self, tools):
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


def format_tools_for_llm_simple(tools) -> str:
    return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)


mcp_tools = [ReadCustomerHistoryMCP(), UpdateClaimHistoryMCP()]
mcp_server = MCPServer(mcp_tools)
available_tools_from_server = mcp_server.list_tools()
formatted_tools = format_tools_for_llm_simple(available_tools_from_server)


# ---------------------------------------------------------------------------
# Payload parsing + upload directory sanitisation
# ---------------------------------------------------------------------------


@dataclass
class PolicyRunContext:
    upload_dir: Path | None
    raw_payload: str | None
    warnings: list[str]


def _resolve_upload_dir(upload_dir: str | None) -> tuple[Path | None, list[str]]:
    warnings: list[str] = []
    if not upload_dir:
        return None, warnings

    candidate = Path(upload_dir).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists() or not candidate.is_dir():
        warnings.append(f"Upload directory not found: {candidate}")
        return None, warnings

    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError:
        warnings.append(
            f"Upload directory {candidate} is outside project root; ensure this is intentional."
        )

    if DEFAULT_UPLOAD_ROOT.exists():
        try:
            candidate.relative_to(DEFAULT_UPLOAD_ROOT)
        except ValueError:
            warnings.append(
                f"Upload directory {candidate} is outside the configured uploads root {DEFAULT_UPLOAD_ROOT}."
            )

    return candidate, warnings


def _parse_policy_payload(messages: list[Message]) -> PolicyRunContext:
    warnings: list[str] = []
    raw_payload: str | None = None
    upload_dir: Path | None = None

    if not messages or not messages[-1].parts:
        warnings.append("No ACP input payload supplied.")
        return PolicyRunContext(upload_dir=None, raw_payload=None, warnings=warnings)

    payload = messages[-1].parts[0].content
    payload_dict: dict[str, Any] = {}

    if isinstance(payload, str):
        raw_payload = payload
        try:
            payload_dict = json.loads(payload) if payload else {}
        except Exception:
            warnings.append("Input payload was not valid JSON; ignoring optional parameters.")
    elif isinstance(payload, dict):
        payload_dict = payload
        raw_payload = json.dumps(payload_dict, ensure_ascii=False)
    else:
        warnings.append("Unexpected payload type from ACP; expected JSON string or dict.")
        raw_payload = json.dumps(payload, ensure_ascii=False, default=str)

    upload_dir_value = payload_dict.get("upload_dir") if isinstance(payload_dict, dict) else None
    resolved_dir, extra_warnings = _resolve_upload_dir(upload_dir_value)
    warnings.extend(extra_warnings)

    return PolicyRunContext(upload_dir=resolved_dir, raw_payload=raw_payload, warnings=warnings)


@contextmanager
def _temporary_upload_env(directory: Path | None):
    previous = os.environ.get("UPLOAD_DIR")
    try:
        if directory is not None:
            os.environ["UPLOAD_DIR"] = str(directory)
        yield
    finally:
        if previous is None:
            os.environ.pop("UPLOAD_DIR", None)
        else:
            os.environ["UPLOAD_DIR"] = previous


def _dump_pydantic(task: Task) -> dict | None:
    try:
        if getattr(task, "output", None) and getattr(task.output, "pydantic", None):
            return task.output.pydantic.model_dump()
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Policy agent definition
# ---------------------------------------------------------------------------


@server.agent()
async def policy_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Run the sequential CrewAI workflow and return a compact JSON response."""

    context = _parse_policy_payload(messages)

    agents_config = _agents_config()
    tasks_config = _tasks_config()

    # ----- Schema definitions (kept local to avoid import cycles) -----
    class A1ClassifyValidate(BaseModel):
        validation_status: str = Field(..., alias="Validation-Status")
        validation_message: str = Field(..., alias="Validation-Message")
        document_content: str = Field(..., alias="Document-Content")

        model_config = ConfigDict(populate_by_name=True)

    class A2Extract(BaseModel):
        status: str = Field(..., alias="status")
        message: str = Field(..., alias="message")

        policy_holder: str | None = Field(None, alias="Policy_Holder")
        claim_number: str | None = Field(None, alias="Claim_Number")
        policy_number: str | None = Field(None, alias="Policy_Number")
        hospital_name: str | None = Field(None, alias="Hospital Name")
        invoice_number: str | None = Field(None, alias="Invoice Number")
        claim_amount: str | None = Field(None, alias="Claim_Amount")
        email: str | None = Field(None, alias="Email")
        maximum_claim_limit: str | None = Field(None, alias="Maximum Claim Limit")
        policy_holder_full_name: str | None = Field(None, alias="Policy Holder's Full Name")
        total_claim_amount: str | None = Field(None, alias="Total Claim Amount")

        model_config = ConfigDict(populate_by_name=True)

    class VerificationDetails(BaseModel):
        status: str
        message: str

    class A3Verify(BaseModel):
        original_data: dict[str, Any]
        hospital_record: dict[str, Any]
        verification_details: VerificationDetails

    class A4Decision(BaseModel):
        customer_name: str = Field(..., alias="Customer Name")
        policy_number: str = Field(..., alias="Policy Number")
        final_decision: str = Field(..., alias="Final Decision")
        amount_approved: float | None = Field(None, alias="Amount Approved")
        confirmation: str | None = Field(None, alias="Confirmation")
        rejection_reason: str | None = Field(None, alias="Rejection Reason")

        model_config = ConfigDict(populate_by_name=True)

    class A5Statement(BaseModel):
        statement: str

    class A6Email(BaseModel):
        to: EmailStr | None = None
        subject: str
        body_text: str
        body_html: str | None = None

    # ----- Agent construction -----
    A1 = Agent(config=agents_config["DocumentClassifierAgent"], llm=llm, verbose=True)
    A2 = Agent(config=agents_config["ClaimDataExtractorAgent"], llm=llm, verbose=True)
    A3_ExternalVerifier = Agent(
        config=agents_config["ExternalVerifierAgent"],
        tools=[bridge_tool],
        llm=llm,
        verbose=True,
    )

    crew_history_tools = [
        MCPReadHistoryAdapter(ReadCustomerHistoryMCP()),
        MCPUpdateHistoryAdapter(UpdateClaimHistoryMCP()),
    ]

    A4_PolicyAdjudicator = Agent(
        config=agents_config["PolicyAdjudicatorAgent"],
        tools=crew_history_tools,
        llm=llm,
        verbose=True,
    )

    A5_Statement = Agent(config=agents_config["StatementSynthesizerAgent"], llm=llm, verbose=True)
    A6_Email = Agent(config=agents_config["EmailComposerAgent"], llm=llm, verbose=True)

    # ----- Tasks -----
    T1 = Task(
        config=tasks_config["classify_and_validate_documents"],
        agent=A1,
        tools=[file_tool],
        output_pydantic=A1ClassifyValidate,
    )

    if context.upload_dir is not None:
        extra = (
            "\n\nIMPORTANT:\n"
            f"- Use DirectoryLoaderTool with directory_path EXACTLY as: '{context.upload_dir}'.\n"
            "- Do not guess or change the folder name.\n"
        )
        T1.description = (T1.description or "") + extra

    T2 = Task(
        config=tasks_config["extract_claim_details"],
        agent=A2,
        context=[T1],
        output_pydantic=A2Extract,
    )

    T3 = Task(
        config=tasks_config["external_verification"],
        agent=A3_ExternalVerifier,
        context=[T2],
        output_pydantic=A3Verify,
    )

    T4 = Task(
        config=tasks_config["manage_history_and_decide"],
        agent=A4_PolicyAdjudicator,
        context=[T3],
        tools=crew_history_tools,
        output_pydantic=A4Decision,
    )

    if "{available_tools}" in (T4.description or ""):
        T4.description = T4.description.replace("{available_tools}", formatted_tools)
    T4.description = (T4.description or "") + (
        "\n\nReturn ONLY valid JSON matching the output schema. No prose, no code fences."
    )

    T5 = Task(
        config=tasks_config["synthesize_final_statement"],
        agent=A5_Statement,
        context=[T1, T2, T3, T4],
        output_pydantic=A5Statement,
    )

    T6 = Task(
        config=tasks_config["compose_email_to_policyholder"],
        agent=A6_Email,
        context=[T5, T4, T2],
        output_pydantic=A6Email,
    )

    crew = Crew(
        agents=[A1, A2, A3_ExternalVerifier, A4_PolicyAdjudicator, A5_Statement, A6_Email],
        tasks=[T1, T2, T3, T4, T5, T6],
        process=Process.sequential,
        verbose=True,
    )

    with _temporary_upload_env(context.upload_dir):
        try:
            await crew.kickoff_async()
        except Exception as exc:
            traceback.print_exc()
            error_payload = {
                "error": "Pipeline execution failed",
                "details": repr(exc),
                "warnings": context.warnings,
            }
            yield Message(parts=[MessagePart(content=json.dumps(error_payload, ensure_ascii=False))])
            return

    # Attempt to auto-fill "to" from extractor output if missing
    try:
        extractor_email = None
        if getattr(T2, "output", None) and getattr(T2.output, "pydantic", None):
            extractor_email = getattr(T2.output.pydantic, "email", None)
        if extractor_email and getattr(T6.output, "pydantic", None):
            email_obj = T6.output.pydantic.model_dump()
            if not email_obj.get("to"):
                email_obj["to"] = extractor_email
                T6.output.pydantic = type(T6.output.pydantic)(**email_obj)
    except Exception:
        pass

    statement_obj = _dump_pydantic(T5) or {"statement": "<unavailable>"}
    email_obj = _dump_pydantic(T6) or {"subject": "<unavailable>", "body_text": "<unavailable>"}

    response = {
        "statement": statement_obj.get("statement", ""),
        "email": email_obj,
        "meta": {
            "warnings": context.warnings,
            "upload_dir": str(context.upload_dir) if context.upload_dir else None,
        },
    }

    yield Message(parts=[MessagePart(content=json.dumps(response, ensure_ascii=False))])


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    server.run(port=8011)
