# import csv
# import json
# from typing import Type
# from pydantic import BaseModel, Field
# from crewai.tools import BaseTool
# from pathlib import Path

# class RetrieveClaimSchema(BaseModel):
#     invoice_number: str = Field(description="The unique invoice number to retrieve from the database.")

# class ClaimRetrieverTool(BaseTool):
#     name: str = "ClaimRetrieverTool"
#     description: str = "Retrieves a full hospital claim record from the database using its invoice number."
#     args_schema: Type[BaseModel] = RetrieveClaimSchema

#     def _run(self, invoice_number: str) -> str:
#         filename = str(Path(__file__).resolve().parents[1] / "history" / "hospital_db.csv")
#         try:
#             with open(filename, mode='r', newline='', encoding='utf-8') as file:
#                 reader = csv.DictReader(file)
#                 for row in reader:
#                     if row["Invoice Number"] == invoice_number:
#                         return json.dumps(row)
#                 return json.dumps({"error": "No record found for the provided invoice number."})
#         except FileNotFoundError:
#             return json.dumps({"error": f"The database file '{filename}' was not found."})
#         except Exception as e:
#             return json.dumps({"error": f"An unexpected error occurred during data retrieval: {e}"})

import csv
import json
from typing import Type, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from pathlib import Path

class RetrieveClaimSchema(BaseModel):
    invoice_number: str = Field(description="The unique invoice number to retrieve from the database.")

def _merge_row_extras_into_total(row: dict, headers: List[str]) -> dict:
    """
    If DictReader encounters extra columns (because a field contained an unquoted comma),
    it puts them under the None key (list). We merge those extras back into 'Total Amount'.
    """
    if None in row and row[None]:
        extras = row.pop(None)
        # Decide where to merge: prefer 'Total Amount' if present, otherwise the last known header
        target_key = "Total Amount" if "Total Amount" in row else headers[-1] if headers else None
        if target_key:
            base_val = (row.get(target_key) or "").strip()
            # Join extras with commas to reconstruct original value
            merged_val = (base_val + ("," if base_val and extras else "") + ",".join(extras)).strip(", ")
            row[target_key] = merged_val
        else:
            # Fallback: store under a safe key if no headers detected
            row["Extra"] = ",".join(extras)
    return row

def _strip_bom(s: str) -> str:
    # Handle UTF-8 BOM if present in header cells
    return s.lstrip("\ufeff") if isinstance(s, str) else s

class ClaimRetrieverTool(BaseTool):
    name: str = "ClaimRetrieverTool"
    description: str = "Retrieves a full hospital claim record from the database using its invoice number."
    args_schema: Type[BaseModel] = RetrieveClaimSchema

    def _run(self, invoice_number: str) -> str:
        filename = str(Path(__file__).resolve().parents[1] / "history" / "hospital_db.csv")
        try:
            with open(filename, mode='r', newline='', encoding='utf-8-sig') as file:
                # Use DictReader but be ready to merge extras
                reader = csv.DictReader(file, skipinitialspace=True)
                # Normalize headers (strip BOM)
                if reader.fieldnames:
                    reader.fieldnames = [_strip_bom(h) for h in reader.fieldnames]

                for raw_row in reader:
                    row = {(_strip_bom(k) if k is not None else k): (v.strip() if isinstance(v, str) else v)
                           for k, v in raw_row.items()}
                    # Merge any extras from unquoted commas
                    row = _merge_row_extras_into_total(row, reader.fieldnames or [])

                    # Match by invoice number (exact match)
                    if row.get("Invoice Number") == invoice_number:
                        # Optional: normalize currency spacing (do NOT strip commas; keep original)
                        # Ensure stable JSON (no None keys)
                        row.pop(None, None)
                        return json.dumps(row, ensure_ascii=False)

                return json.dumps({"error": "No record found for the provided invoice number."}, ensure_ascii=False)

        except FileNotFoundError:
            return json.dumps({"error": f"The database file '{filename}' was not found."}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"An unexpected error occurred during data retrieval: {e}"},
                              ensure_ascii=False)
