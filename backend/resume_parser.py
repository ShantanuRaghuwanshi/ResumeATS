import pdfplumber
from docx import Document
from typing import Dict
import os

# Helper functions to extract info from text


def extract_personal_details(text: str) -> Dict:
    # Dummy extraction logic, replace with NLP for production
    lines = text.splitlines()
    details = {"name": lines[0] if lines else "", "contact": "", "linkedin": ""}
    for line in lines:
        if "linkedin.com" in line.lower():
            details["linkedin"] = line.strip()
        if "@" in line and ("gmail" in line or "yahoo" in line):
            details["contact"] = line.strip()
    return details


def extract_sections(text: str) -> Dict:
    # Dummy logic, split by keywords
    sections = {"education": "", "work_experience": "", "projects": "", "skills": ""}
    lower = text.lower()
    for key in sections:
        idx = lower.find(key)
        if idx != -1:
            sections[key] = text[idx:]
    return sections


def parse_pdf(file_path: str) -> Dict:
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    details = extract_personal_details(text)
    sections = extract_sections(text)
    return {"personal_details": details, **sections}


def parse_docx(file_path: str) -> Dict:
    doc = Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    details = extract_personal_details(text)
    sections = extract_sections(text)
    return {"personal_details": details, **sections}


def parse_resume(file_path: str) -> Dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    else:
        return {"error": "Unsupported file type"}
