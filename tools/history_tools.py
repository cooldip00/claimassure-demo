from crewai.tools import BaseTool
import pandas as pd
import os
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Type

class ReadHistoryInput(BaseModel):
    policy_holder: str = Field(description="The full name of the policy holder to search for.")
    policy_number: str = Field(description="The policy number associated with the policy holder.")

class UpdateHistoryInput(BaseModel):
    customer_name: str = Field(description="The full name of the customer.")
    policy_number: str = Field(description="The customer's policy number.")
    claim_number: str = Field(description="The unique number for the new claim being recorded.")
    approved_amount: float = Field(description="The final approved claim amount as a numeric value (e.g., 40000.0).")
    status: str = Field(description="The final approval status (e.g., 'Approved Full Amount', 'Approved Partial Amount').")

class ReadCustomerHistoryTool(BaseTool):
    name: str = "Read Customer Claim History Tool"
    description: str = (
        "Use this tool to get the total previously claimed amount for a customer "
        "based on their full name and policy number. "
        "It reads the 'Claim Amount (₹)' column from the history file and returns the sum."
    )
    args_schema: Type[BaseModel] = ReadHistoryInput

    def _run(self, policy_holder: str, policy_number: str) -> str:
        if not policy_holder or not policy_number:
            return "Error: Both 'policy_holder' and 'policy_number' must be provided."

        file_path = os.path.join("history", "customer_history.csv")

        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            pd.DataFrame(columns=[
                'Customer Name', 'Policy Number', 'Claim Number', 'Date of Claim',
                'Type of Claim', 'Claim Amount (₹)', 'Status'
            ]).to_csv(file_path, index=False)

        try:
            history_df = pd.read_csv(
                file_path,
                dtype={'Customer Name': str, 'Policy Number': str, 'Claim Amount (₹)': float}
            )

            search_name = policy_holder.strip().lower()
            search_policy = policy_number.strip()

            customer_claims = history_df[
                (history_df['Customer Name'].str.strip().str.lower() == search_name) &
                (history_df['Policy Number'].str.strip() == search_policy)
            ]

            if customer_claims.empty:
                return f"No claim history found for {policy_holder}. Total previously claimed: 0."

            total_claimed = customer_claims['Claim Amount (₹)'].sum()
            return f"Success. Total previously claimed amount for {policy_holder} is: {total_claimed}."

        except FileNotFoundError:
             return "Error: Customer history file not found at 'history/customer_history.csv'."
        except KeyError as e:
            return f"Error: A required column is missing from the CSV file: {e}. Please check the file headers."
        except Exception as e:
            return f"An unexpected error occurred while reading the history file: {e}"

class UpdateClaimHistoryTool(BaseTool):
    name: str = "Update Claim History Database Tool"
    description: str = (
        "Use this tool to add a new approved claim record to the customer history database. "
        "You must provide all required details, including the approved amount as a number."
    )
    args_schema: Type[BaseModel] = UpdateHistoryInput

    def _run(self, customer_name: str, policy_number: str, claim_number: str, approved_amount: float, status: str) -> str:
        if not all([customer_name, policy_number, claim_number, status]):
            return "Error: 'customer_name', 'policy_number', 'claim_number', and 'status' cannot be empty."

        try:
            validated_amount = float(approved_amount)
            if validated_amount < 0:
                return "Error: 'approved_amount' cannot be negative."
        except (ValueError, TypeError):
            return f"Error: 'approved_amount' must be a valid number. Received: '{approved_amount}'."

        file_path = os.path.join("history", "customer_history.csv")

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            new_record_data = {
                'Customer Name': [customer_name.strip()],
                'Policy Number': [policy_number.strip()],
                'Claim Number': [claim_number.strip()],
                'Date of Claim': [datetime.now().strftime('%Y-%m-%d')],
                'Type of Claim': ['Medical'],
                'Claim Amount (₹)': [validated_amount],
                'Status': [status.strip()]
            }
            new_claim_record = pd.DataFrame(new_record_data)

            header = not os.path.exists(file_path)
            new_claim_record.to_csv(file_path, mode='a', header=header, index=False)

            return f"Success. Database updated for {customer_name} with a new claim of {validated_amount} and status '{status}'."
        except Exception as e:
            return f"An unexpected error occurred while updating the history file: {e}"
