# # import os
# # import json
# # from fastapi import FastAPI, Request, Body
# # from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
# # from fastapi.staticfiles import StaticFiles
# # from fastapi.middleware.cors import CORSMiddleware
# # from acp_sdk.client import Client
# # from pydantic import BaseModel

# # # Config (change if you use different ports/hosts)
# # POLICY_SERVER_URL = os.getenv("POLICY_SERVER_URL", "http://localhost:8011")
# # RETRIEVER_SERVER_URL = os.getenv("RETRIEVER_SERVER_URL", "http://localhost:8012")

# # app = FastAPI(title="ClaimAssure — Demo UI")

# # # Serve static and index
# # app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# # @app.get("/", response_class=HTMLResponse)
# # async def root():
# #     index_path = os.path.join(os.path.dirname(__file__), "index.html")
# #     return FileResponse(index_path)

# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # @app.get("/api/health")
# # async def health():
# #     return {"ok": True, "policy_server": POLICY_SERVER_URL}

# # # Models
# # class RetrieveBody(BaseModel):
# #     invoice_number: str

# # @app.post("/api/run")
# # async def run_full_flow():
# #     """
# #     Calls the policy agent on :8011. Expects a JSON string with per-agent outputs.
# #     """
# #     try:
# #         async with Client(base_url=POLICY_SERVER_URL) as c:
# #             run = await c.run_sync(agent="policy_agent", input=[])
# #             if not run.output or not run.output[0].parts:
# #                 return JSONResponse({"error": "Empty response from policy agent"}, status_code=502)
# #             content = run.output[0].parts[0].content

# #             # We expect JSON now (from the policy agent change above).
# #             try:
# #                 parsed = json.loads(content)
# #                 return {"success": True, "result": parsed}
# #             except Exception:
# #                 # Fallback: return raw text if something unexpected comes through.
# #                 return {"success": True, "result_raw": content}
# #     except Exception as e:
# #         return JSONResponse({"error": f"Policy run failed: {e!r}"}, status_code=500)

# # @app.post("/api/retrieve")
# # async def retrieve_record(body: RetrieveBody):
# #     """
# #     Calls the retriever agent on :8012 with the invoice number.
# #     """
# #     try:
# #         natural_language_input = f"Please retrieve the record for invoice number {body.invoice_number}."
# #         async with Client(base_url=RETRIEVER_SERVER_URL) as c:
# #             run = await c.run_sync(agent="claim_retriever_agent", input=natural_language_input)
# #             if not run.output or not run.output[0].parts:
# #                 return JSONResponse({"error": "Empty response from retriever agent"}, status_code=502)
# #             content = run.output[0].parts[0].content
# #             try:
# #                 parsed = json.loads(content)
# #                 return {"success": True, "record": parsed}
# #             except Exception:
# #                 return {"success": True, "record_raw": content}
# #     except Exception as e:
# #         return JSONResponse({"error": f"Retriever call failed: {e!r}"}, status_code=500)

# import os
# import json
# import uuid
# from pathlib import Path
# from typing import Optional, List

# from fastapi import FastAPI, UploadFile, File, Form
# from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from acp_sdk.client import Client

# # Config
# POLICY_SERVER_URL = os.getenv("POLICY_SERVER_URL", "http://localhost:8011")
# RETRIEVER_SERVER_URL = os.getenv("RETRIEVER_SERVER_URL", "http://localhost:8012")
# UPLOADS_ROOT = Path(os.getenv("UPLOADS_ROOT", Path(__file__).resolve().parent.parent / "uploads"))
# UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

# app = FastAPI(title="ClaimAssure — Demo UI")
# app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# @app.get("/", response_class=HTMLResponse)
# async def root():
#   index_path = os.path.join(os.path.dirname(__file__), "index.html")
#   return FileResponse(index_path)

# app.add_middleware(
#   CORSMiddleware,
#   allow_origins=["*"],
#   allow_methods=["*"],
#   allow_headers=["*"],
# )

# @app.get("/api/health")
# async def health():
#   return {"ok": True, "policy_server": POLICY_SERVER_URL}

# # -------- Upload --------
# @app.post("/api/upload")
# async def upload_files(files: List[UploadFile] = File(...)):
#   if not files:
#     return JSONResponse({"success": False, "error": "No files"}, status_code=400)

#   session_id = uuid.uuid4().hex[:8]
#   session_dir = UPLOADS_ROOT / f"session-{session_id}"
#   session_dir.mkdir(parents=True, exist_ok=True)

#   saved = 0
#   allowed = {".pdf", ".docx", ".txt"}
#   for f in files:
#     ext = Path(f.filename).suffix.lower()
#     if ext not in allowed:
#       continue
#     data = await f.read()
#     (session_dir / f.filename).write_bytes(data)
#     saved += 1

#   if saved == 0:
#     return JSONResponse({"success": False, "error": "No valid files (pdf/docx/txt)"}, status_code=400)

#   return {"success": True, "dir": str(session_dir), "count": saved}

# # -------- Run full flow --------
# class RunBody(BaseModel):
#   upload_dir: Optional[str] = None

# @app.post("/api/run")
# async def run_full_flow(body: RunBody):
#   """
#   Calls the policy agent on :8011; passes optional upload_dir into the agent input.
#   """
#   try:
#     input_payload = {"upload_dir": body.upload_dir} if body.upload_dir else {}
#     async with Client(base_url=POLICY_SERVER_URL) as c:
#       run = await c.run_sync(agent="policy_agent", input=input_payload)
#       if not run.output or not run.output[0].parts:
#         return JSONResponse({"error": "Empty response from policy agent"}, status_code=502)
#       content = run.output[0].parts[0].content
#       try:
#         parsed = json.loads(content)
#         return {"success": True, "result": parsed}
#       except Exception:
#         return {"success": True, "result_raw": content}
#   except Exception as e:
#     return JSONResponse({"error": f"Policy run failed: {e!r}"}, status_code=500)

"""FastAPI app powering the ClaimAssure demo experience."""

import json
import os
import traceback
import uuid
from pathlib import Path
from typing import List, Optional

from acp_sdk.client import Client
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

POLICY_SERVER_URL = os.getenv("POLICY_SERVER_URL", "http://localhost:8011")

UPLOADS_ROOT = Path(
    os.getenv("UPLOADS_ROOT", Path(__file__).resolve().parent.parent / "uploads")
)
UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".pdf,.docx,.txt").split(",")
    if ext
}
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "10"))


app = FastAPI(title="ClaimAssure — Demo UI")
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe version of *filename* (basename only)."""

    # ``Path.name`` drops any directory traversal while preserving unicode characters.
    return Path(filename).name


def _extension_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def root() -> FileResponse:
    """Serve the static single-page application."""

    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(index_path)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    """Simple readiness endpoint consumed by the UI."""

    return {
        "ok": True,
        "policy_server": POLICY_SERVER_URL,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "max_upload_files": MAX_UPLOAD_FILES,
    }


# -------- Upload --------


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> JSONResponse | dict:
    """Persist uploaded claim artefacts to a session folder."""

    if not files:
        return JSONResponse(
            {"success": False, "error": "No files submitted."}, status_code=400
        )

    if len(files) > MAX_UPLOAD_FILES:
        return JSONResponse(
            {
                "success": False,
                "error": f"Too many files. Limit is {MAX_UPLOAD_FILES}.",
                "received": len(files),
            },
            status_code=400,
        )

    session_id = uuid.uuid4().hex[:8]
    session_dir = UPLOADS_ROOT / f"session-{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_files: List[dict] = []
    skipped: List[str] = []

    for upload in files:
        filename = _sanitize_filename(upload.filename or "")
        if not filename:
            skipped.append("<unnamed>")
            continue

        if not _extension_allowed(filename):
            skipped.append(filename)
            continue

        data = await upload.read()
        destination = session_dir / filename
        destination.write_bytes(data)

        saved_files.append(
            {
                "name": filename,
                "size": len(data),
                "content_type": upload.content_type,
                "path": str(destination),
            }
        )

    if not saved_files:
        error_hint = (
            "Supported extensions: "
            + ", ".join(sorted(ALLOWED_EXTENSIONS))
            if ALLOWED_EXTENSIONS
            else "No extensions are currently allowed."
        )
        return JSONResponse(
            {
                "success": False,
                "error": "No valid files were uploaded.",
                "skipped": skipped,
                "hint": error_hint,
            },
            status_code=400,
        )

    return {
        "success": True,
        "dir": str(session_dir),
        "count": len(saved_files),
        "files": saved_files,
        "skipped": skipped,
    }


# -------- Run full flow --------


class RunBody(BaseModel):
    upload_dir: Optional[str] = None


@app.post("/api/run")
async def run_full_flow(body: RunBody) -> JSONResponse | dict:
    """Invoke the policy agent (via ACP) and return structured results."""

    input_payload = {"upload_dir": body.upload_dir} if body.upload_dir else {}
    payload_str = json.dumps(input_payload) if input_payload else "run"

    try:
        async with Client(base_url=POLICY_SERVER_URL) as client:
            run = await client.run_sync(agent="policy_agent", input=[payload_str])

        # Defensive parsing of the ACP response
        if not getattr(run, "output", None) or not run.output[0].parts:
            return {
                "success": False,
                "error": "Empty response from policy agent",
                "where": "policy_agent",
                "hint": "Check server logs on :8011 and ensure GEMINI_API_KEY is set.",
            }

        content = run.output[0].parts[0].content

        try:
            parsed = json.loads(content)
        except Exception as exc:  # pragma: no cover - best effort JSON parsing
            return {
                "success": True,
                "result_raw": content,
                "note": "Content was not valid JSON; showing raw output.",
                "parse_error": repr(exc),
                "policy_server": POLICY_SERVER_URL,
            }

        return {
            "success": True,
            "result": parsed,
            "policy_server": POLICY_SERVER_URL,
        }

    except Exception as exc:  # pragma: no cover - surface diagnostics to UI
        tb = traceback.format_exc()
        return JSONResponse(
            {
                "success": False,
                "error": f"Policy run failed: {repr(exc)}",
                "traceback": tb,
                "policy_server": POLICY_SERVER_URL,
                "hint": "Is :8011 reachable? Any validation/parsing errors in policy server?",
            },
            status_code=200,  # do not 500; let the UI render diagnostic info
        )
