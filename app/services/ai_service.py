import os
import json
from typing import Dict, List
import openai
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

logging.getLogger("openai").setLevel(logging.WARNING)

class AIReconciliationService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
    async def match_transactions(self, bank_data: List[Dict], book_data: List[Dict]) -> List[Dict]:
        """Let the LLM do the matching based on dynamic column and handles large datasets."""
        if not bank_data or not book_data:
            print("No transactions to process.")
            return []

        prompt = self._create_matching_prompt(bank_data, book_data)
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """
                            You are an expert in financial reconciliation handling large datasets mostly csv.
                            Your goal is to match bank transactions with book records based on:
                            
                            -Date Matching: Transactions can be matched with up to a 5-day difference.
                            -Amount Matching: Accept minor rounding errors up to ±0.05%.
                            -Narration Similarity: Transactions with at least 70% text similarity should be considered potential matches.
                            
                            Classification Rules:
                            -Green (Exact Match): Matches on date (within allowed range), amount, and narration.
                            -Yellow (Possible Match): Minor differences in amount or narration but still likely the same transaction.
                            -Red (Unmatched): No suitable match found.

                            Important Considerations:
                            - Ignore reference numbers for matching.
                            - Ensure all transactions are processed and categorized.
                            - Return results only in valid JSON format.

                            Output Format (Example JSON):
                            {
                            "green": [ {matched transaction details} ],
                            "yellow": [ {potential matches} ],
                            "red": [ {unmatched transactions} ]
                            }
                     Also provide if book transactions are missing in bank transactions or vice versa.
                     Give a output specifying the amount to be adjusted in the book transactions at the last.
                        """},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.2,
                max_tokens=4000
            )

            raw_content = response.choices[0].message['content'].strip()
            print("Raw JSON content:", raw_content)  # Debugging

            if not raw_content:
                print("Received empty response from API")
                return []

            # Validate JSON format and fix common issues
            raw_content = raw_content.replace("'", '"')  # Ensure proper double quotes
            result = json.loads(raw_content)
            return self._combine_results([result])
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {str(e)}")
            with open("error_log.txt", "a", encoding="utf-8") as log_file:
                log_file.write(f"JSON decoding error: {str(e)}\nRaw response content: {raw_content}\n")
            return []
        except Exception as e:
            print(f"Error processing transactions: {str(e)}")
            with open("error_log.txt", "a", encoding="utf-8") as log_file:
                log_file.write(f"Error processing transactions: {str(e)}\n")
            return []

    def _create_matching_prompt(self, bank_data: List[Dict], book_data: List[Dict]) -> str:
        """Convert transactions into a prompt while handling datetime serialization."""
        
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        prompt = (
            f"Here are two sets of transactions:\n\n"
            f"Bank Transactions:\n{json.dumps(bank_data, indent=2, default=convert_datetime)}\n\n"
            f"Book Transactions:\n{json.dumps(book_data, indent=2, default=convert_datetime)}\n\n"
            " Match transactions based on date, amount, and narration similarity.\n"
            " Ignore reference numbers when finding matches.\n"
            " Provide the results in valid JSON format with three categories:\n"
            "- Green: Exact match.\n"
            "- Yellow: Possible match.\n"
            "- Red: No match found.\n"
            "Ensure no transactions are skipped."
        )
        return prompt

    def _combine_results(self, results: List) -> List[Dict]:
        """Combine the JSON results into a single output."""
        combined_results = {"green": [], "yellow": [], "red": []}

        for result in results:
            try:
                if isinstance(result, str):
                    result = json.loads(result)
                # Use the entire result if "matches" isn't provided.
                source = result.get("matches", result)
                combined_results["green"].extend(source.get("green", []))
                combined_results["yellow"].extend(source.get("yellow", []))
                combined_results["red"].extend(source.get("red", []))
            except Exception as e:
                print(f"Error processing result: {str(e)}")
                with open("error_log.txt", "a", encoding="utf-8") as log_file:
                    log_file.write(f"Error processing result: {str(e)}\n")

        print(f"Processed Transactions: {len(combined_results['green']) + len(combined_results['yellow']) + len(combined_results['red'])}")
        print(f"Green: {len(combined_results['green'])}, Yellow: {len(combined_results['yellow'])}, Red: {len(combined_results['red'])}")

        with open("ai_results.json", "w", encoding="utf-8") as file:
            json.dump(combined_results, file, indent=4)

        return combined_results
