import os
import json
import openai
import asyncio
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, List
import logging
from datetime import datetime

load_dotenv()

# Set logging level to suppress debug messages
logging.getLogger("openai").setLevel(logging.WARNING)

class AIReconciliationService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')

    def load_and_extract_columns(self, file_path: str, required_columns: List[str]) -> List[Dict]:
        """Loads an Excel file and extracts only the required columns."""
        try:
            df = pd.read_excel(file_path, usecols=required_columns, dtype=str)  # Read specific columns
            df.fillna("", inplace=True)  # Handle NaN values by replacing with an empty string
            return df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

    def chunk_data(self, data: List[Dict], chunk_size: int = 50) -> List[List[Dict]]:
        """Splits data into smaller chunks."""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    async def match_transactions(self, bank_data: List[Dict], book_data: List[Dict]) -> List[Dict]:
        """Processes transactions sequentially to avoid rate limit issues."""
        
        chunk_size = 50  # Adjust chunk size to balance efficiency and API limits
        results = []
        unmatched_bank = []
        unmatched_book = []

        # **First Pass: Process chunks one by one**
        for i in range(0, max(len(bank_data), len(book_data)), chunk_size):
            bank_chunk = bank_data[i:i + chunk_size]
            book_chunk = book_data[i:i + chunk_size]
            
            result = await self.process_chunk(bank_chunk, book_chunk, i // chunk_size)
            
            if result:
                results.append(result)
                unmatched_bank.extend(result.get("red", []))
                unmatched_book.extend(result.get("red", []))

            # **Introduce a delay to avoid rate limits**
            await asyncio.sleep(2)

        # **Second Pass: Process remaining unmatched transactions**
        if unmatched_bank and unmatched_book:
            print(f"Processing final batch of {len(unmatched_bank)} unmatched transactions...")
            final_result = await self.process_chunk(unmatched_bank, unmatched_book, "final")
            
            if final_result:
                results.append(final_result)

        return self._combine_results(results)

    async def process_chunk(self, bank_chunk: List[Dict], book_chunk: List[Dict], index):
        """Processes a single chunk asynchronously."""
        prompt = self._create_matching_prompt(bank_chunk, book_chunk)

        response = await self.call_openai_with_retry(prompt)
        if response:
            try:
                raw_response = response.choices[0].message['content'].strip()
                print(f"Raw AI Response for chunk {index}: {raw_response}")  # Debugging print
                return json.loads(raw_response)
            except Exception as e:
                print(f"Error parsing JSON for chunk {index}: {str(e)}")
        return None

    async def call_openai_with_retry(self, prompt, retries=1):
        """Calls OpenAI API with a single retry mechanism."""
        for attempt in range(retries + 1):
            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=8000
                )
                return response
            except Exception as e:
                if attempt == retries:
                    print(f"Final failure for OpenAI API: {e}")
                    return None
                print(f"Retrying due to API error: {e}")
                await asyncio.sleep(1)

    def _get_system_prompt(self) -> str:
        """Returns the system prompt for AI model"""
        return """
            You are an expert in financial reconciliation handling large datasets mostly CSV.
            Your goal is to match bank transactions with book records based on:
            
            - Date Matching: Transactions can be matched with up to a 5-day difference.
            - Amount Matching: Accept minor rounding errors up to ±0.05%.
            - Narration Similarity: Transactions with at least 70% text similarity should be considered potential matches.
            
            Classification Rules:
            - Green (Exact Match): Matches on date (within allowed range), amount, and narration.
            - Yellow (Possible Match): Minor differences in amount or narration but still likely the same transaction.
            - Red (Unmatched): No suitable match found.

            Return results in valid JSON format with "green", "yellow", and "red" categories.
            Use the same decision logic and formatting as previous chunks.
            For each transaction, if a similar one was found in previous chunks, ensure it is matched consistently.
        """

    def _create_matching_prompt(self, bank_data: List[Dict], book_data: List[Dict]) -> str:
        """Convert transactions into a structured AI prompt while handling datetime serialization."""
        
        def convert_datetime(obj):
            """Convert datetime objects to string format (ISO 8601)."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
            
        prompt = (
            f"Here are two sets of transactions:\n\n"
            f"Bank Transactions:\n{json.dumps(bank_data, separators=(',', ':'), default=convert_datetime)}\n\n"
            f"Book Transactions:\n{json.dumps(book_data, separators=(',', ':'), default=convert_datetime)}\n\n"
            "Match transactions based on date, amount, and narration similarity.\n"
            "Ignore reference numbers when finding matches.\n"
            "Provide the results in valid JSON format with three categories:\n"
            "- Green: Exact match.\n"
            "- Yellow: Possible match.\n"
            "- Red: No match found.\n"
            "Ensure no transactions are skipped.\n"
        )
        
        return prompt

    def _combine_results(self, results: List) -> List[Dict]:
        """Combine the JSON results from all matches into a single output, ensuring unmatched transactions are properly updated."""
        combined_results = {"green": [], "yellow": [], "red": []}
        unmatched_set = set()  # Track transactions that were initially unmatched

        for result in results:
            try:
                if isinstance(result, str):
                    result = json.loads(result)

                combined_results["green"].extend(result.get("green", []))
                combined_results["yellow"].extend(result.get("yellow", []))
                
                # Track initially unmatched transactions
                for txn in result.get("red", []):
                    unmatched_set.add(json.dumps(txn, sort_keys=True))  # Store as string to handle dict comparisons

            except Exception as e:
                print(f"Error processing result: {str(e)}")

        # **Remove transactions from "red" if they got matched later**
        matched_set = {
            json.dumps(txn, sort_keys=True)
            for txn in (combined_results["green"] + combined_results["yellow"])
        }

        combined_results["red"] = [
            json.loads(txn) for txn in unmatched_set if txn not in matched_set
        ]

        # **Logging for Debugging**
        print(f"Total Transactions Processed: {sum(map(len, combined_results.values()))}")
        print(f"Green: {len(combined_results['green'])}, Yellow: {len(combined_results['yellow'])}, Red: {len(combined_results['red'])}")

        # Save to JSON for debugging
        with open("ai_results.json", "w", encoding="utf-8") as file:
            json.dump(combined_results, file, indent=4)

        return combined_results



# **Usage Example**
if __name__ == "__main__":
    reconciliation_service = AIReconciliationService()

    bank_columns = ['Date', 'Narration', 'Withdrawal Amt.', 'Deposit Amt.']
    book_columns = ['date', 'transaction_details', 'debit', 'credit']

    bank_data = reconciliation_service.load_and_extract_columns("bank_statement.xlsx", bank_columns)
    book_data = reconciliation_service.load_and_extract_columns("company_records.xlsx", book_columns)

    bank_chunks = reconciliation_service.chunk_data(bank_data)
    book_chunks = reconciliation_service.chunk_data(book_data)

    asyncio.run(reconciliation_service.match_transactions(bank_data, book_data))
