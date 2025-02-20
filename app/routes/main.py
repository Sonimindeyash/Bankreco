from flask import Blueprint, request, jsonify
import pandas as pd
import asyncio  # Import asyncio
from app.services.file_processor import ReconciliationProcessor
from app.utils.validators import allowed_file
import json

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'pdf', 'xls'}

@main_bp.route('/api/upload', methods=['POST'])
def upload_files():  # Remove `async`
    if 'bank_statement' not in request.files or 'company_book' not in request.files:
        return jsonify({'error': 'Both files are required'}), 400
    
    bank_file = request.files['bank_statement']
    book_file = request.files['company_book']
    
    if not (bank_file and allowed_file(bank_file.filename, ALLOWED_EXTENSIONS) and 
            book_file and allowed_file(book_file.filename, ALLOWED_EXTENSIONS)):
        return jsonify({'error': 'Invalid file format'}), 400

    try:
        processor = ReconciliationProcessor()
        
        # Run async function in Flask using asyncio.run()
        results = asyncio.run(processor.process_files_with_ai(bank_file, book_file))
        return jsonify(results), 200  # Return results as JSON
    except Exception as e:
        return jsonify({'error': str(e)}), 500
