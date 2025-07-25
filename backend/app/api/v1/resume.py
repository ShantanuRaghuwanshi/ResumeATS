from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import os
from app.configs.config import get_logger

logger = get_logger(__name__)
import aiofiles
import json
from app.services.resume_parser import (
    parse_resume,
    get_logs,
    extract_personal_details,
    extract_sections,
)
from app.services.resume_generator import generate_resume
from app.services.jd_optimizer import optimize_resume_for_jd
from app.services.llm_provider import LLMProviderFactory

from app.security.middleware import upload_rate_limit
from app.security.input_validation import (
    validate_resume_upload,
    InputSanitizer,
    SecureResumeData,
)
from app.security.audit_logging import (
    log_user_action,
    log_security_event,
    AuditEventType,
    AuditSeverity,
)

from app.models.resume import PersonalDetails, ResumeSections

router = APIRouter()

UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

parsed_resume_store = {}


@router.post("/llm/test")
async def test_llm_config(config: dict = Body(...)):
    provider_name = config.get("provider")
    if not provider_name:
        raise HTTPException(status_code=400, detail="Missing 'provider' in config")

    # Extract config from the nested structure if present
    if "config" in config:
        provider_config = config["config"]
        api_key = provider_config.get("apiKey")
        url = provider_config.get("url", "http://localhost:11434")
        model = provider_config.get("model", "gemma3n:e4b")
    else:
        api_key = config.get("apiKey")
        url = config.get("url", "http://localhost:11434")
        model = config.get("model", "gemma3n:e4b")

    # Create provider config with both camelCase and snake_case keys for compatibility
    provider_config_dict = {
        "provider": provider_name,
        "api_key": api_key,
        "apiKey": api_key,  # Support both formats
        "url": url,
        "model": model,
    }

    try:
        provider = LLMProviderFactory.create(provider_name, provider_config_dict)
        dummy_text = "John Doe, johndoe@email.com, linkedin.com/in/johndoe"
        result = await provider.extract_personal_details(dummy_text)

        # Handle both Pydantic models and dictionaries
        if hasattr(result, "model_dump"):
            result_data = result.model_dump()
        elif isinstance(result, dict):
            result_data = result
        else:
            result_data = {"result": str(result)}

        return JSONResponse({"success": True, "result": result_data})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/upload_resume/")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    provider_name: str = Form("ollama"),
    provider_config: str = Form("{}"),
):

    # Apply rate limiting
    await upload_rate_limit(request)

    try:
        # Validate and sanitize filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        sanitized_filename = InputSanitizer.sanitize_filename(file.filename)
        if not sanitized_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Read file content
        content = await file.read()

        # Validate file upload
        validate_resume_upload(content, sanitized_filename)

        # Log upload attempt
        await log_user_action(
            "resume_upload",
            request,
            resource_type="resume",
            details={
                "filename": sanitized_filename,
                "file_size": len(content),
                "provider": provider_name,
            },
        )

        # Save file with sanitized name
        file_path = os.path.join(UPLOAD_DIR, sanitized_filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Validate and sanitize provider config
        try:
            config = json.loads(provider_config) if provider_config else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid provider configuration JSON"
            )

        # Parse resume
        parsed = parse_resume(file_path, provider_name, config)
        text = parsed.get("text", "")

        # Extract and validate personal details
        personal = await extract_personal_details(text, provider_name, config)
        extrac_sections = await extract_sections(text, provider_name, config)

        if isinstance(personal, PersonalDetails):
            personal = personal.model_dump()

        education = extrac_sections.get("education", [])
        work_experience = extrac_sections.get("work_experience", [])
        projects = extrac_sections.get("projects", [])
        skills = extrac_sections.get("skills", [])

        # Create structured data
        structured = {
            "personal_details": personal,
            "education": education,
            "work_experience": work_experience,
            "projects": projects,
            "skills": skills,
        }

        # Store parsed resume
        parsed_resume_store["resume"] = structured

        # Log successful upload
        await log_user_action(
            "resume_parsed",
            request,
            resource_type="resume",
            details={
                "filename": sanitized_filename,
                "sections_extracted": list(structured.keys()),
            },
            success=True,
        )

        return JSONResponse(structured)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to upload or parse resume")

        # Log error
        await log_security_event(
            AuditEventType.ERROR_OCCURRED,
            request,
            details={
                "operation": "resume_upload",
                "error": str(e),
                "filename": file.filename if file else "unknown",
            },
            severity=AuditSeverity.HIGH,
            success=False,
            error_message=str(e),
        )

        return JSONResponse(
            {"error": "Failed to process resume upload"}, status_code=500
        )


@router.get("/resume_sections/")
async def get_resume_sections():
    resume = parsed_resume_store.get("resume")
    if not resume:
        return JSONResponse({"error": "No resume parsed yet."}, status_code=404)
    return JSONResponse(resume)


@router.patch("/resume_sections/")
async def update_resume_sections(update: dict = Body(...)):
    resume = parsed_resume_store.get("resume")
    if not resume:
        return JSONResponse({"error": "No resume parsed yet."}, status_code=404)
    for k, v in update.items():
        resume[k] = v
    parsed_resume_store["resume"] = resume
    return JSONResponse(resume)


@router.post("/optimize_resume/")
async def optimize_resume(parsed: dict = Body(...), jd: str = Body(...)):
    try:
        updated = optimize_resume_for_jd(parsed, jd)
        return JSONResponse(updated)
    except Exception as e:
        logger.exception("Failed to optimize resume")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/generate_resume/")
async def generate(
    parsed: dict = Body(...),
    template: str = Body("modern"),
    filetype: str = Body("docx"),
):
    try:
        output_path = generate_resume(parsed, template, filetype)
        return {"download_url": f"/download/{os.path.basename(output_path)}"}
    except Exception as e:
        logger.exception("Failed to generate resume")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/download/{filename}")
async def download(filename: str):
    file_path = os.path.join(GENERATED_DIR, filename)
    return FileResponse(file_path, filename=filename)


@router.get("/logs/")
async def fetch_logs():
    return JSONResponse(
        {"logs": get_logs()}
    )  # Resume endpoints will be refactored here from your current main.py
