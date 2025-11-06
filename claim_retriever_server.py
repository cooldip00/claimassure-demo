"""ACP server exposing the claim retriever CrewAI pipeline."""

from __future__ import annotations

import json
import os
import re
import typing as _t
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import nest_asyncio
import uvicorn
import yaml
from dotenv import load_dotenv

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server
from crewai import Agent, Crew, LLM, Process, Task

from tools.claim_retriever_tool import ClaimRetrieverTool


# Load environment variables from the .env file (if present)
load_dotenv()


# ---------------------------------------------------------------------------
# Runtime configuration helpers
# ---------------------------------------------------------------------------


CONFIG_ROOT = Path(__file__).resolve().parent / "config"
INVOICE_PATTERN = re.compile(r"INV\d+")


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


def _ensure_loop_backcompat() -> None:
    """Provide LoopSetupType for older uvicorn versions."""

    cfg = uvicorn.config
    if hasattr(cfg, "LoopSetupType"):
        return
    try:
        from typing import Literal as _Literal  # type: ignore

        cfg.LoopSetupType = _Literal["none", "auto", "asyncio", "uvloop"]  # type: ignore[attr-defined]
    except Exception:
        cfg.LoopSetupType = _t.Any  # type: ignore[attr-defined]


_ensure_loop_backcompat()


# ---------------------------------------------------------------------------
# ACP server + Crew primitives
# ---------------------------------------------------------------------------


server = Server()
llm = LLM(model="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

CLAIM_RETRIEVER_TOOL = ClaimRetrieverTool()
nest_asyncio.apply()


@dataclass
class RetrieverRequest:
    raw_input: str
    invoice_number: str | None
    warnings: list[str]


def _parse_request(messages: list[Message]) -> RetrieverRequest:
    warnings: list[str] = []

    if not messages or not messages[-1].parts:
        warnings.append("No input provided.")
        return RetrieverRequest(raw_input="", invoice_number=None, warnings=warnings)

    payload = messages[-1].parts[0].content
    if isinstance(payload, str):
        raw_input = payload
    else:
        raw_input = json.dumps(payload, ensure_ascii=False)
        warnings.append("Expected string input; coerced payload to JSON string.")

    match = INVOICE_PATTERN.search(raw_input)
    invoice = match.group(0) if match else None
    if invoice is None:
        warnings.append("Unable to locate an invoice number in the request text.")

    return RetrieverRequest(raw_input=raw_input, invoice_number=invoice, warnings=warnings)


def _build_crew() -> Crew:
    agents_config = _agents_config()
    tasks_config = _tasks_config()

    retriever_agent = Agent(
        config=agents_config["ClaimRetrieverAgent"],
        tools=[CLAIM_RETRIEVER_TOOL],
        llm=llm,
        verbose=True,
    )

    retrieval_task = Task(
        config=tasks_config["retrieve_hospital_claim"],
        agent=retriever_agent,
        output_json=True,
    )

    return Crew(
        agents=[retriever_agent],
        tasks=[retrieval_task],
        process=Process.sequential,
        verbose=True,
    )


@server.agent()
async def claim_retriever_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Orchestrate a CrewAI task that retrieves hospital claim details."""

    request = _parse_request(messages)
    if request.invoice_number is None:
        error = {
            "error": "Invoice number missing.",
            "warnings": request.warnings,
        }
        yield Message(parts=[MessagePart(content=json.dumps(error, ensure_ascii=False))])
        return

    try:
        crew = _build_crew()
        inputs = {"claim_details": request.raw_input}
        print(f"Kicking off data retrieval crew with invoice {request.invoice_number}")
        task_output = await crew.kickoff_async(inputs=inputs)

        raw_result = getattr(task_output, "raw", str(task_output))
        try:
            parsed_result = json.loads(raw_result)
        except Exception:
            parsed_result = raw_result

        payload = {
            "success": True,
            "invoice_number": request.invoice_number,
            "result": parsed_result,
        }
        if request.warnings:
            payload["warnings"] = request.warnings

        yield Message(parts=[MessagePart(content=json.dumps(payload, ensure_ascii=False))])

    except Exception as exc:
        import traceback

        traceback.print_exc()
        error_message = {
            "error": "An error occurred on the data retriever server.",
            "details": repr(exc),
            "warnings": request.warnings,
        }
        yield Message(parts=[MessagePart(content=json.dumps(error_message, ensure_ascii=False))])


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    server.run(port=8012)
