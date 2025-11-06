"""Bridge tool that lets CrewAI reach the ACP retriever microservice."""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Type

from acp_sdk.client import Client
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


ACP_RETRIEVER_URL = os.getenv("ACP_RETRIEVER_URL", "http://localhost:8012")
ACP_RETRIEVER_TIMEOUT = float(os.getenv("ACP_RETRIEVER_TIMEOUT", "30"))


class ACPClaimRetrieveArgs(BaseModel):
    invoice_number: str = Field(description="The unique invoice number for the claim.")


class ACPClaimRetrieverBridgeTool(BaseTool):
    name: str = "External Hospital Claim Retriever (via ACP Bridge)"
    description: str = (
        "Calls an external ACP microservice to retrieve a full hospital claim record "
        "using only the invoice_number."
    )
    args_schema: Type[BaseModel] = ACPClaimRetrieveArgs

    def _run(self, invoice_number: str) -> str:
        inv = (invoice_number or "").strip()
        if not re.fullmatch(r"INV[\d]+", inv):
            return '{"error": "Invalid invoice number format; expected e.g. INV445566."}'

        natural_language_input = f"Please retrieve the record for invoice number {inv}."

        async def _call_retriever_agent() -> str:
            async with Client(base_url=ACP_RETRIEVER_URL) as client:
                run = await client.run_sync(
                    agent="claim_retriever_agent",
                    input=natural_language_input,
                )
                if not run.output or not run.output[0].parts:
                    return '{"error": "Empty response from ACP claim retriever service."}'
                content = run.output[0].parts[0].content
                try:
                    parsed = json.loads(content)
                except Exception:
                    return content

                if isinstance(parsed, dict) and "result" in parsed:
                    result_obj = parsed.get("result")
                    meta = {k: v for k, v in parsed.items() if k not in {"result"}}
                    if isinstance(result_obj, dict):
                        if meta:
                            result_obj = {**result_obj, "_meta": meta}
                        return json.dumps(result_obj, ensure_ascii=False)
                    if isinstance(result_obj, list):
                        wrapped = {"data": result_obj}
                        if meta:
                            wrapped["_meta"] = meta
                        return json.dumps(wrapped, ensure_ascii=False)
                    try:
                        return json.dumps(parsed, ensure_ascii=False)
                    except Exception:
                        return content

                return content

        async def _call_with_timeout() -> str:
            try:
                return await asyncio.wait_for(
                    _call_retriever_agent(),
                    timeout=ACP_RETRIEVER_TIMEOUT,
                )
            except asyncio.TimeoutError:
                return '{"error": "ACP claim retriever timed out."}'

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop – safe to use asyncio.run
            try:
                return asyncio.run(_call_with_timeout())
            except Exception as exc:  # pragma: no cover - top-level guard
                return f'{"error": "ACP bridge call failed: {exc!r}"}'

        try:
            return loop.run_until_complete(_call_with_timeout())
        except Exception as exc:  # pragma: no cover - reentrant loop fallback
            return f'{"error": "ACP bridge call failed: {exc!r}"}'
