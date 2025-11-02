# ClaimAssure (Fixed)

This bundle includes the patched files discussed:
- **Consistency**: Document type is `Bill` everywhere (no `Medical Bill` drift).
- **Task keys**: `synthesize_final_statement` is top-level in `config/tasks.yaml`.
- **Safe formatting**: `manage_history_and_decide` description supports `{available_tools}` placeholder,
  and the server uses a safe `.replace(...)` rather than `.format(...)`.
- **No false verification failures**: removed the forced `used_invoice_number` guard from `main_policy_server.py`.
- **Robust loaders**: `DirectoryLoaderTool._run` accepts `directory_path` override.

## Quick Start

1. Set environment variable `GEMINI_API_KEY`.
2. Prepare `data/` with Policy, Bill, and Claim Form files; prepare `history/` with `hospital_db.csv` and optional `customer_history.csv`.
3. Start servers:
   - `python main_policy_server.py`  (port 8011)
   - `python claim_retriever_server.py` (port 8012)
4. Launch the demo UI:
   - `cd webapp`
   - Use any ASGI/WSGI/Static server to serve the folder, or run `uvicorn` for your own API and open `/`.

# ClaimAssure — End-to-End Claims Demo

FastAPI web UI + two ACP agents (Policy Server :8011, Retriever :8012) + Gemini 2.0 flash.

## Quick Start

```bash
# 1) Create venv & install
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2) Set environment
copy .env.example .env
# Add your GEMINI_API_KEY to .env

# 3) Start servers (in separate terminals)
python main_policy_server.py      # http://127.0.0.1:8011
python claim_retriever_server.py  # http://127.0.0.1:8012

# 4) Start web UI
uv run uvicorn webapp.app:app --reload --port 8080
