from __future__ import annotations
from typing import Dict, Any
import os
import pandas as pd
from datetime import datetime

HISTORY_CSV = os.path.join("history", "customer_history.csv")

def _ensure_history_csv():
    if not os.path.exists(HISTORY_CSV):
        os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
        pd.DataFrame(columns=[
            'Customer Name', 'Policy Number', 'Claim Number', 'Date of Claim',
            'Type of Claim', 'Claim Amount (₹)', 'Status'
        ]).to_csv(HISTORY_CSV, index=False)

class ReadCustomerHistoryMCP:
    """MCP-native tool (no CrewAI dependency)."""
    name = "Read Customer Claim History Tool"
    description = (
        "Return the total previously claimed amount for a customer given "
        "'policy_holder' and 'policy_number'."
    )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        policy_holder = (params or {}).get("policy_holder", "")
        policy_number = (params or {}).get("policy_number", "")
        if not policy_holder or not policy_number:
            return {"success": False, "error": "Both 'policy_holder' and 'policy_number' are required."}

        _ensure_history_csv()
        try:
            df = pd.read_csv(
                HISTORY_CSV,
                dtype={'Customer Name': str, 'Policy Number': str, 'Claim Amount (₹)': float}
            )
            mask = (
                df['Customer Name'].str.strip().str.lower().eq(policy_holder.strip().lower()) &
                df['Policy Number'].str.strip().eq(policy_number.strip())
            )
            subset = df.loc[mask]
            total = float(subset['Claim Amount (₹)'].sum()) if not subset.empty else 0.0
            return {
                "success": True,
                "message": f"Total previously claimed amount for {policy_holder}: {total}.",
                "total_claimed": total
            }
        except Exception as e:
            return {"success": False, "error": f"Read failed: {e!r}"}

class UpdateClaimHistoryMCP:
    """MCP-native tool (no CrewAI dependency)."""
    name = "Update Claim History Database Tool"
    description = (
        "Append a new approved claim record. Requires 'customer_name', 'policy_number', "
        "'claim_number', 'approved_amount' (float), and 'status'."
    )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        customer_name = (params or {}).get("customer_name", "")
        policy_number = (params or {}).get("policy_number", "")
        claim_number = (params or {}).get("claim_number", "")
        status = (params or {}).get("status", "")
        approved_amount = (params or {}).get("approved_amount", None)

        missing = [k for k in ["customer_name", "policy_number", "claim_number", "status", "approved_amount"]
                   if not (params or {}).get(k) and (params or {}).get(k) != 0]
        if missing:
            return {"success": False, "error": f"Missing fields: {', '.join(missing)}"}

        try:
            amt = float(approved_amount)
            if amt < 0:
                return {"success": False, "error": "'approved_amount' cannot be negative."}
        except Exception:
            return {"success": False, "error": f"'approved_amount' must be a number. Got: {approved_amount!r}"}

        _ensure_history_csv()
        try:
            row = {
                'Customer Name': customer_name.strip(),
                'Policy Number': policy_number.strip(),
                'Claim Number': claim_number.strip(),
                'Date of Claim': datetime.now().strftime('%Y-%m-%d'),
                'Type of Claim': 'Medical',
                'Claim Amount (₹)': amt,
                'Status': status.strip()
            }
            header = not os.path.exists(HISTORY_CSV) or os.path.getsize(HISTORY_CSV) == 0
            pd.DataFrame([row]).to_csv(HISTORY_CSV, mode='a', header=header, index=False)
            return {"success": True, "message": "History updated.", "record": row}
        except Exception as e:
            return {"success": False, "error": f"Write failed: {e!r}"}
