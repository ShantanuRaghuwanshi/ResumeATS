import pdfplumber
from docx import Document
from typing import Dict
import os
import requests
from ollama_utils import ollama_extract_personal_details, ollama_extract_sections
import logging

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Set up logging
log_messages = []
logging.basicConfig(level=logging.INFO)


def log(msg):
    log_messages.append(msg)
    logging.info(msg)


# Helper functions to extract info from text
async def extract_personal_details(text: str) -> Dict:
    """
    Extract personal details using Ollama LLM utility.
    """
    return await ollama_extract_personal_details(text)


async def extract_sections(text: str) -> Dict:
    """
    Extract resume sections using Ollama LLM utility.
    Returns a nested structure for sections.
    """
    # Use ollama_extract_sections as before, but parse into nested structure
    flat_sections = await ollama_extract_sections(text)

    # Example: parse work_experience and projects into lists of dicts if possible
    def parse_list_section(section_text):
        # If already a list, return as-is (or process items if needed)
        if isinstance(section_text, list):
            return section_text
        # If string, split by newlines or bullets, filter empty
        items = [item.strip() for item in section_text.split("\n") if item.strip()]
        # Try to parse as dict if possible (e.g., 'Company: X, Role: Y')
        result = []
        for item in items:
            if ":" in item:
                parts = [p.strip() for p in item.split(",")]
                entry = {}
                for part in parts:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        entry[k.strip().lower().replace(" ", "_")] = v.strip()
                if entry:
                    result.append(entry)
                else:
                    result.append({"description": item})
            else:
                result.append({"description": item})
        return result

    return {
        "education": flat_sections.get("education", ""),
        "work_experience": parse_list_section(flat_sections.get("work_experience", "")),
        "projects": parse_list_section(flat_sections.get("projects", "")),
        "skills": flat_sections.get("skills", ""),
    }


def parse_pdf(file_path: str) -> Dict:
    log(f"Parsing PDF: {file_path}")
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    log(f"Extracted text length: {len(text)}")
    return {"text": text}


def parse_docx(file_path: str) -> Dict:
    log(f"Parsing DOCX: {file_path}")
    doc = Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    log(f"Extracted text length: {len(text)}")
    # Synchronous wrapper for async extraction
    import asyncio

    details = asyncio.run(extract_personal_details(text))
    log(f"Personal details extracted: {details}")
    sections = asyncio.run(extract_sections(text))
    log(f"Sections extracted: {sections}")
    return {"personal_details": details, **sections}


def parse_resume(file_path: str) -> Dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    else:
        return {"error": "Unsupported file type"}


def get_logs():
    return log_messages
