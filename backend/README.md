# Resume ATS Backend

This backend uses FastAPI to handle resume uploads, parsing, JD optimization, and resume generation.

## Features
- Upload resume (PDF/DOCX)
- Parse and extract structured data
- Accept job description input
- Update/optimize resume for JD
- Generate new resume (DOCX/PDF)

## Setup
1. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the server:
   ```powershell
   uvicorn main:app --reload
   ```
