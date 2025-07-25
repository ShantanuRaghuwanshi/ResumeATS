import pdfplumber
from docx import Document
from typing import Dict, Optional
import os
import requests
from app.models.resume import PersonalDetails, ResumeSections
from app.services.llm_provider import LLMProviderBase, get_llm_provider
from app.configs.config import get_logger

logger = get_logger(__name__)

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Set up logging
log_messages = []
logger.info("Logger initialized for resume_parser")


def log(msg):
    log_messages.append(msg)
    logger.info(msg)


# Helper functions to extract info from text using selected LLM provider
def get_extractor(provider_name: str, provider_config: dict) -> LLMProviderBase:
    provider = get_llm_provider(provider_name, provider_config)
    return provider


async def extract_personal_details(
    text: str, provider_name: str = "ollama", provider_config: Optional[dict] = None
) -> Dict:
    """
    Extract personal details using selected LLM provider utility.
    """
    provider_config = provider_config or {}
    provider = get_extractor(provider_name, provider_config)
    return await provider.extract_personal_details(text)


async def extract_sections(
    text: str, provider_name: str = "ollama", provider_config: Optional[dict] = None
) -> Dict:
    """
    Extract resume sections using selected LLM provider utility.
    Returns a nested structure for sections.
    """
    provider_config = provider_config or {}
    provider = get_extractor(provider_name, provider_config)
    flat_sections = await provider.extract_sections(text)
    if isinstance(flat_sections, ResumeSections):
        flat_sections = flat_sections.model_dump()

    return flat_sections


def parse_pdf(file_path: str) -> Dict:
    log(f"Parsing PDF: {file_path}")
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    log(f"Extracted text length: {len(text)}")
    return {"text": text}


# In parse_docx, allow passing provider_name and config
def parse_docx(
    file_path: str,
    provider_name: str = "ollama",
    provider_config: Optional[dict] = None,
) -> Dict:
    log(f"Parsing DOCX: {file_path}")
    doc = Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs])
    log(f"Extracted text length: {len(text)}")
    # Synchronous wrapper for async extraction
    import asyncio

    details = asyncio.run(
        extract_personal_details(text, provider_name, provider_config)
    )
    log(f"Personal details extracted: {details}")
    sections = asyncio.run(extract_sections(text, provider_name, provider_config))
    log(f"Sections extracted: {sections}")
    return {"personal_details": details, **sections}


# In parse_resume, allow passing provider_name and config
def parse_resume(
    file_path: str,
    provider_name: str = "ollama",
    provider_config: Optional[dict] = None,
) -> Dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path, provider_name, provider_config)
    else:
        return {"error": "Unsupported file type"}


def get_logs():
    return log_messages
