from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from acp_sdk.client import Client
import asyncio
from typing import Type

class ACPClaimRetrieveArgs(BaseModel):
    invoice_number: str = Field(description="The unique invoice number for the claim.")

class ACPClaimRetrieverBridgeTool(BaseTool):
    name: str = "External Hospital Claim Retriever (via ACP Bridge)"
    description: str = ("Calls an external ACP microservice to retrieve a full hospital claim record "
                        "using only the invoice_number.")
    args_schema: Type[BaseModel] = ACPClaimRetrieveArgs

    def _run(self, invoice_number: str) -> str:
        inv = (invoice_number or "").strip()
        import re
        if not re.fullmatch(r"INV[\d]+", inv):
            return '{"error": "Invalid invoice number format; expected e.g. INV445566."}'

        natural_language_input = f"Please retrieve the record for invoice number {inv}."

        async def _call_retriever_agent():
            async with Client(base_url="http://localhost:8012") as client:
                run = await client.run_sync(agent="claim_retriever_agent", input=natural_language_input)
                if not run.output or not run.output[0].parts:
                    return '{"error": "Empty response from ACP claim retriever service."}'
                return run.output[0].parts[0].content

        try:
            # Preferred path when no loop is running
            return asyncio.run(_call_retriever_agent())
        except RuntimeError:
            # Likely "asyncio.run() cannot be called from a running event loop"
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(_call_retriever_agent())
            except Exception as e:
                return f'{{"error": "ACP bridge call failed: {e!r}"}}'
        except Exception as e:
            return f'{{"error": "ACP bridge call failed: {e!r}"}}'
