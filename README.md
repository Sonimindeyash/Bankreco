#AI-Powered Bank Reconciliation System

Overview
This project leverages OpenAI's GPT models to automate the reconciliation of bank transactions with book records. It intelligently matches transactions based on date, amount, and narration similarity, helping businesses streamline their financial reconciliation process.

Features
- **Automated Matching**: Matches bank and book transactions dynamically based on predefined criteria.
- **Classification**:
  - **Green**: Exact matches.
  - **Yellow**: Possible matches with minor differences.
  - **Red**: Unmatched transactions.
- **Error Handling**: Handles JSON decoding errors and logs issues.
- **Logging & Debugging**: Saves raw API responses and errors for further analysis.
- **Efficient Processing**: Works with large datasets using chunk-based processing.

Installation

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Create a `.env` file and add your OpenAI API key:
   ```sh
   OPENAI_API_KEY=your_api_key_here
   ```

Usage
1. Prepare your bank and book transaction data as CSV.
2. Run the reconciliation process:
   ```python
   from your_script_name import AIReconciliationService
   
   service = AIReconciliationService()
   results = await service.match_transactions(bank_data, book_data)
   ```
3. Review the `ai_results.json` file for the output.

 Matching Criteria
- **Date Matching**: Allows up to a 5-day difference.
- **Amount Matching**: Accepts minor rounding errors (±0.05%).
- **Narration Similarity**: Requires at least 70% similarity for a match.
- **Reference Numbers**: Ignored during matching.

 Error Handling
- Raw API responses are stored for debugging.

## Output Format
Results are categorized into `green`, `yellow`, and `red`, with suggested book adjustments where necessary.
```json
{
  "green": [ { "matched transaction details" } ],
  "yellow": [ { "potential matches" } ],
  "red": [ { "unmatched transactions" } ]
}
```

## Future Enhancements
- Optimize token usage for larger datasets.
- Improve similarity scoring for better matching accuracy.
- Implement RAG for fine accuracy
  

