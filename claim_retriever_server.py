import os
import uvicorn
import yaml
import nest_asyncio
from collections.abc import AsyncGenerator
import typing as _t
from dotenv import load_dotenv

# Load environment variables from the .env file (if present)
load_dotenv()

# Uvicorn loop setup back-compat
_cfg = uvicorn.config
if not hasattr(_cfg, "LoopSetupType"):
    try:
        from typing import Literal as _Literal
        _cfg.LoopSetupType = _Literal["none", "auto", "asyncio", "uvloop"]
    except Exception:
        _cfg.LoopSetupType = _t.Any

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server
from crewai import Crew, Task, Agent, LLM, Process

from tools.claim_retriever_tool import ClaimRetrieverTool

server = Server()
llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)

nest_asyncio.apply()

@server.agent()
async def claim_retriever_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Orchestrates a CrewAI task to RETRIEVE hospital claim details.
    Input should contain an invoice number.
    Output will be a JSON string of the database record.
    """
    try:
        if not messages or not messages[-1].parts:
            yield Message(parts=[MessagePart(content='{"error": "No input provided."}')])
            return

        claim_details_input = messages[-1].parts[0].content

        with open('config/agents.yaml', 'r') as file:
            agents_config = yaml.safe_load(file)
        with open('config/tasks.yaml', 'r') as file:
            tasks_config = yaml.safe_load(file)

        claim_retriever_tool = ClaimRetrieverTool()

        retriever_agent = Agent(
            config=agents_config["ClaimRetrieverAgent"],
            tools=[claim_retriever_tool],
            llm=llm,
            verbose=True
        )

        retrieval_task = Task(
            config=tasks_config["retrieve_hospital_claim"],
            agent=retriever_agent
        )

        crew = Crew(agents=[retriever_agent], tasks=[retrieval_task], verbose=True)

        inputs = {'claim_details': claim_details_input}
        print(f"Kicking off data retrieval crew with input: {inputs}")
        task_output = await crew.kickoff_async(inputs=inputs)

        yield Message(parts=[MessagePart(content=str(task_output))])

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_message = f'{{"error": "An error occurred on the data retriever server: {str(e)}"}}'
        yield Message(parts=[MessagePart(content=error_message)])

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    server.run(port=8012)
