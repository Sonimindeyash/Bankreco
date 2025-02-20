from typing import Dict, List
import pandas as pd
from .ai_service import AIReconciliationService  # Import the AIReconciliationService

class ReconciliationProcessor:
    def __init__(self):
        self.ai_service = AIReconciliationService()

    def _read_file(self, file_path: str) -> pd.DataFrame:
        try:
            if file_path.filename.split(".")[-1] == "csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            return df
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {str(e)}")

    async def process_files_with_ai(self, bank_file, book_file) -> Dict:
        # Read files
        bank_df = self._read_file(bank_file)
        book_df = self._read_file(book_file)
        # Convert DataFrames to dictionaries
        bank_data = bank_df.to_dict(orient='records')
        book_data = book_df.to_dict(orient='records')
        # Use AI service to match transactions
        results = await self.ai_service.match_transactions(bank_data, book_data)
        return results