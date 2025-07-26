from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Body,
    HTTPException,
    Request,
    Depends,
)
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
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
from app.middleware.session_middleware import (
    get_session_from_request,
    get_llm_config_from_request,
)
from app.services.session_manager import get_session_manager, SessionManager

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
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Upload and parse resume using session-based LLM configuration.
    Requires valid session with LLM configuration.
    """
    # Apply rate limiting
    await upload_rate_limit(request)
    # Get session information from middleware (already validated by middleware)
    session_id = get_session_from_request(request)
    llm_config = get_llm_config_from_request(request)

    if not llm_config:
        raise HTTPException(
            status_code=500, detail="LLM configuration not available in session"
        )

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

        # Extract LLM configuration from session
        provider_name = llm_config.provider.value
        config = {
            "api_key": llm_config.api_key,
            "base_url": llm_config.base_url,
            "model": llm_config.model_name,
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
            **llm_config.additional_params,
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        # Log upload attempt
        await log_user_action(
            "resume_upload",
            request,
            resource_type="resume",
            details={
                "filename": sanitized_filename,
                "file_size": len(content),
                "provider": provider_name,
                "session_id": session_id,
            },
        )

        # Save file with sanitized name
        file_path = os.path.join(UPLOAD_DIR, sanitized_filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

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

        # Store parsed resume with session association
        resume_id = f"resume_{session_id}_{sanitized_filename.split('.')[0]}"
        parsed_resume_store[resume_id] = structured

        # Add resume to session data
        await session_manager.add_resume_to_session(session_id, resume_id)

        # Log successful upload
        await log_user_action(
            "resume_parsed",
            request,
            resource_type="resume",
            details={
                "filename": sanitized_filename,
                "sections_extracted": list(structured.keys()),
                "session_id": session_id,
                "resume_id": resume_id,
            },
            success=True,
        )

        return JSONResponse(
            {**structured, "resume_id": resume_id, "session_id": session_id}
        )

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
async def get_resume_sections(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get resume sections using session-based approach.
    Returns the latest resume from the current session.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    # Get session data to retrieve resumes
    session_data = await session_manager.get_session_data(session_id)
    if not session_data or not session_data.resume_data:
        raise HTTPException(
            status_code=404, detail="No resume found in current session"
        )

    # Get the most recent resume from session
    latest_resume_id = session_data.resume_data.get("resumes", [])[-1]
    resume = parsed_resume_store.get(latest_resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail="Resume data not found")

    return JSONResponse(
        {
            **resume,
            "resume_id": latest_resume_id,
            "session_id": session_id,
            "total_resumes_in_session": len(
                session_data.resume_data.get("resumes", [])
            ),
        }
    )


@router.patch("/resume_sections/")
async def update_resume_sections(
    request: Request,
    update: dict = Body(...),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Update resume sections using session-based approach.
    Requires valid session with stored resume data.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    # Get session data to retrieve resumes
    session_data = await session_manager.get_session_data(session_id)
    if not session_data or not session_data.resume_data.get("resumes", []):
        raise HTTPException(
            status_code=404, detail="No resume found in current session"
        )

    # Get the most recent resume from session
    latest_resume_id = session_data.resume_data.get("resumes", [])[-1]
    resume = parsed_resume_store.get(latest_resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail="Resume data not found")

    # Update resume sections
    for k, v in update.items():
        resume[k] = v

    # Save updated resume
    parsed_resume_store[latest_resume_id] = resume

    # Log the update
    await log_user_action(
        "resume_sections_updated",
        request,
        resource_type="resume",
        details={
            "session_id": session_id,
            "resume_id": latest_resume_id,
            "updated_sections": list(update.keys()),
        },
        success=True,
    )

    return JSONResponse(
        {**resume, "resume_id": latest_resume_id, "session_id": session_id}
    )


@router.post("/optimize_resume/")
async def optimize_resume(
    request: Request,
    parsed: dict = Body(...),
    jd: str = Body(...),
    optimization_goals: List[str] = Body([]),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Optimize resume for a specific job description using session-based LLM configuration.
    Requires valid session with LLM configuration.

    Request body should include:
    - parsed: Resume data dictionary (or use session's latest resume)
    - jd: Job description text
    - optimization_goals: List of optimization goals (optional)
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)
    llm_config = get_llm_config_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    if not llm_config:
        raise HTTPException(
            status_code=500, detail="LLM configuration not available in session"
        )

    try:
        from app.services.jd_optimizer import optimize_resume_for_jd

        # Extract LLM configuration from session
        provider_name = llm_config.provider.value

        # Prepare provider config from session LLM config
        provider_config = {
            "api_key": llm_config.api_key,
            "base_url": llm_config.base_url,
            "model": llm_config.model_name,
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
            **llm_config.additional_params,
        }
        # Remove None values
        provider_config = {k: v for k, v in provider_config.items() if v is not None}

        # Set default optimization goals if not provided
        if not optimization_goals:
            optimization_goals = ["ats_optimization", "keyword_matching"]

        # Log optimization attempt
        await log_user_action(
            "resume_optimization",
            request,
            resource_type="resume",
            details={
                "session_id": session_id,
                "provider": provider_name,
                "optimization_goals": optimization_goals,
                "jd_length": len(jd),
            },
        )

        # Optimize the resume using session-based LLM config
        updated = await optimize_resume_for_jd(
            parsed=parsed,
            jd=jd,
            provider_name=provider_name,
            provider_config=provider_config,
            optimization_goals=optimization_goals,
        )

        # Log successful optimization
        await log_user_action(
            "resume_optimization_completed",
            request,
            resource_type="resume",
            details={
                "session_id": session_id,
                "provider": provider_name,
                "optimization_goals": optimization_goals,
            },
            success=True,
        )

        return JSONResponse(
            {
                "success": True,
                "optimized_resume": updated,
                "provider_used": provider_name,
                "session_id": session_id,
                "optimization_goals": optimization_goals,
            }
        )

    except Exception as e:
        logger.exception("Failed to optimize resume")

        # Log error
        await log_security_event(
            AuditEventType.ERROR_OCCURRED,
            request,
            details={
                "operation": "resume_optimization",
                "error": str(e),
                "session_id": session_id,
            },
            severity=AuditSeverity.HIGH,
            success=False,
            error_message=str(e),
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(e),
                "message": "Resume optimization failed. Please check your session configuration and try again.",
            },
            status_code=500,
        )


@router.post("/generate_resume/")
async def generate(
    request: Request,
    parsed: Optional[dict] = Body(None),
    template: str = Body("modern"),
    filetype: str = Body("docx"),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Generate resume document using session-based approach.
    Can use provided parsed data or latest resume from session.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    try:
        # If no parsed data provided, get from session
        if not parsed:
            session_data = await session_manager.get_session_data(session_id)
            if not session_data or not session_data.resume_data.get("resumes", []):
                raise HTTPException(
                    status_code=404,
                    detail="No resume data provided and no resume found in session",
                )

            # Get the most recent resume from session
            latest_resume_id = session_data.resume_data.get("resumes", [])[-1]
            parsed = parsed_resume_store.get(latest_resume_id)

            if not parsed:
                raise HTTPException(
                    status_code=404, detail="Resume data not found in session"
                )

        # Log generation attempt
        await log_user_action(
            "resume_generation",
            request,
            resource_type="resume",
            details={
                "session_id": session_id,
                "template": template,
                "filetype": filetype,
            },
        )

        # Generate the resume
        output_path = generate_resume(parsed, template, filetype)

        # Log successful generation
        await log_user_action(
            "resume_generation_completed",
            request,
            resource_type="resume",
            details={
                "session_id": session_id,
                "template": template,
                "filetype": filetype,
                "output_file": os.path.basename(output_path),
            },
            success=True,
        )

        return JSONResponse(
            {
                "success": True,
                "download_url": f"/download/{os.path.basename(output_path)}",
                "session_id": session_id,
                "template": template,
                "filetype": filetype,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to generate resume")

        # Log error
        await log_security_event(
            AuditEventType.ERROR_OCCURRED,
            request,
            details={
                "operation": "resume_generation",
                "error": str(e),
                "session_id": session_id,
            },
            severity=AuditSeverity.HIGH,
            success=False,
            error_message=str(e),
        )

        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/download/{filename}")
async def download(filename: str):
    file_path = os.path.join(GENERATED_DIR, filename)
    return FileResponse(file_path, filename=filename)


@router.get("/logs/")
async def fetch_logs():
    return JSONResponse({"logs": get_logs()})


@router.get("/session/info/")
async def get_session_info(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get current session information including LLM config and resumes.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)
    llm_config = get_llm_config_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    # Get session data
    session_data = await session_manager.get_session_data(session_id)

    # Get validation info
    validation = await session_manager.validate_session(session_id)

    return JSONResponse(
        {
            "session_id": session_id,
            "valid": validation.valid,
            "status": validation.status.value if validation.status else None,
            "llm_config": (
                {
                    "provider": llm_config.provider.value if llm_config else None,
                    "model_name": llm_config.model_name if llm_config else None,
                    "base_url": llm_config.base_url if llm_config else None,
                    "temperature": llm_config.temperature if llm_config else None,
                    "max_tokens": llm_config.max_tokens if llm_config else None,
                }
                if llm_config
                else None
            ),
            "resumes": (
                session_data.resume_data.get("resumes", []) if session_data else []
            ),
            "conversations": session_data.conversations if session_data else [],
            "created_at": session_data.created_at.isoformat() if session_data else None,
            "last_accessed": (
                session_data.last_accessed.isoformat() if session_data else None
            ),
        }
    )


@router.get("/session/resumes/")
async def list_session_resumes(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    List all resumes in the current session with basic metadata.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    # Get session data
    session_data = await session_manager.get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session data not found")

    # Get resume details
    resumes_info = []
    for resume_id in session_data.resume_data.get("resumes", []):
        resume = parsed_resume_store.get(resume_id)
        if resume:
            # Extract basic info
            personal_details = resume.get("personal_details", {})
            resumes_info.append(
                {
                    "resume_id": resume_id,
                    "name": personal_details.get("name", "Unknown"),
                    "email": personal_details.get("email", ""),
                    "sections": list(resume.keys()),
                    "has_work_experience": bool(resume.get("work_experience")),
                    "has_education": bool(resume.get("education")),
                    "has_projects": bool(resume.get("projects")),
                    "has_skills": bool(resume.get("skills")),
                }
            )
        else:
            resumes_info.append(
                {
                    "resume_id": resume_id,
                    "status": "data_not_found",
                }
            )

    return JSONResponse(
        {
            "session_id": session_id,
            "total_resumes": len(session_data.resume_data.get("resumes", [])),
            "resumes": resumes_info,
        }
    )


@router.get("/session/resume/{resume_id}")
async def get_specific_resume(
    resume_id: str,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get a specific resume from the current session by resume_id.
    """
    # Get session information from headers (validated by middleware)
    session_id = get_session_from_request(request)

    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required in headers")

    # Get session data to verify resume belongs to session
    session_data = await session_manager.get_session_data(session_id)
    if not session_data or resume_id not in session_data.resume_data.get("resumes", []):
        raise HTTPException(
            status_code=404, detail="Resume not found in current session"
        )

    # Get the resume data
    resume = parsed_resume_store.get(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume data not found")

    return JSONResponse({**resume, "resume_id": resume_id, "session_id": session_id})


# Resume endpoints will be refactored here from your current main.py
