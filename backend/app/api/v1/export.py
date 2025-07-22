from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional, Dict, Any
import os
import json
from datetime import datetime, timedelta
import asyncio

from models.export import (
    ExportRequest,
    BatchExportRequest,
    ExportHistory,
    ExportPreview,
    ExportAnalytics,
    ExportConfiguration,
    ExportError,
    ExportNotification,
)
from models.resume_version import ResumeVersion
from services.resume_generator import (
    EnhancedResumeGenerator,
    ExportOptions,
    BatchExportRequest as ServiceBatchRequest,
    ResumeExportFormat,
)
from services.version_manager import VersionManager

router = APIRouter(prefix="/export", tags=["export"])

# Initialize services
resume_generator = EnhancedResumeGenerator()
version_manager = VersionManager()

# In-memory storage for demo (replace with database in production)
export_requests_store = {}
batch_requests_store = {}
export_history_store = {}
export_analytics_store = {}


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    formats = [
        {
            "name": "Microsoft Word",
            "extension": "docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "description": "Editable Word document format",
            "supports_templates": True,
            "supports_styling": True,
            "ats_friendly": True,
        },
        {
            "name": "PDF",
            "extension": "pdf",
            "mime_type": "application/pdf",
            "description": "Portable Document Format",
            "supports_templates": True,
            "supports_styling": True,
            "ats_friendly": False,
        },
        {
            "name": "Plain Text",
            "extension": "txt",
            "mime_type": "text/plain",
            "description": "ATS-friendly plain text format",
            "supports_templates": False,
            "supports_styling": False,
            "ats_friendly": True,
        },
        {
            "name": "JSON",
            "extension": "json",
            "mime_type": "application/json",
            "description": "Structured data format",
            "supports_templates": False,
            "supports_styling": False,
            "ats_friendly": False,
        },
        {
            "name": "HTML",
            "extension": "html",
            "mime_type": "text/html",
            "description": "Web-friendly HTML format",
            "supports_templates": True,
            "supports_styling": True,
            "ats_friendly": False,
        },
    ]
    return {"formats": formats}


@router.get("/templates")
async def get_available_templates():
    """Get list of available resume templates"""
    templates = [
        {
            "id": "modern",
            "name": "Modern",
            "description": "Clean, professional design with subtle colors",
            "category": "professional",
            "industry": "general",
            "experience_level": "all",
            "preview_url": "/templates/previews/modern.png",
            "customizable_sections": [
                "personal_details",
                "summary",
                "work_experience",
                "skills",
                "education",
                "projects",
            ],
            "styling_options": {
                "color_scheme": ["blue", "green", "purple", "gray"],
                "font_family": ["Calibri", "Arial", "Helvetica"],
                "spacing": ["compact", "standard", "wide"],
            },
        },
        {
            "id": "classic",
            "name": "Classic",
            "description": "Traditional resume format",
            "category": "traditional",
            "industry": "general",
            "experience_level": "all",
            "preview_url": "/templates/previews/classic.png",
            "customizable_sections": [
                "personal_details",
                "work_experience",
                "education",
                "skills",
                "projects",
            ],
            "styling_options": {
                "color_scheme": ["black", "navy", "gray"],
                "font_family": ["Times New Roman", "Georgia", "Garamond"],
                "spacing": ["compact", "standard"],
            },
        },
        {
            "id": "minimal",
            "name": "Minimal",
            "description": "Simple, clean design focusing on content",
            "category": "minimal",
            "industry": "tech",
            "experience_level": "all",
            "preview_url": "/templates/previews/minimal.png",
            "customizable_sections": [
                "personal_details",
                "work_experience",
                "education",
                "skills",
            ],
            "styling_options": {
                "color_scheme": ["gray", "black"],
                "font_family": ["Arial", "Helvetica", "Roboto"],
                "spacing": ["standard", "wide"],
            },
        },
        {
            "id": "creative",
            "name": "Creative",
            "description": "Eye-catching design for creative professionals",
            "category": "creative",
            "industry": "design",
            "experience_level": "mid-senior",
            "preview_url": "/templates/previews/creative.png",
            "customizable_sections": [
                "personal_details",
                "summary",
                "skills",
                "work_experience",
                "projects",
                "education",
            ],
            "styling_options": {
                "color_scheme": ["teal", "orange", "purple", "red"],
                "font_family": ["Helvetica", "Montserrat", "Open Sans"],
                "spacing": ["standard", "wide"],
            },
        },
        {
            "id": "ats_friendly",
            "name": "ATS Friendly",
            "description": "Optimized for Applicant Tracking Systems",
            "category": "ats",
            "industry": "general",
            "experience_level": "all",
            "preview_url": "/templates/previews/ats_friendly.png",
            "customizable_sections": [
                "personal_details",
                "summary",
                "work_experience",
                "education",
                "skills",
                "projects",
            ],
            "styling_options": {
                "color_scheme": ["none"],
                "font_family": ["Arial", "Calibri"],
                "spacing": ["standard"],
            },
        },
    ]
    return {"templates": templates}


@router.post("/single", response_model=ExportRequest)
async def create_export_request(
    user_id: str,
    resume_id: str,
    format: str,
    template: str = "modern",
    filename: Optional[str] = None,
    include_metadata: bool = True,
    ats_optimized: bool = False,
    custom_styling: Dict[str, Any] = {},
    sections_to_include: List[str] = [],
    apply_optimizations: bool = True,
    optimization_results: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Create a single resume export request"""

    # Create export request
    export_request = ExportRequest(
        user_id=user_id,
        resume_id=resume_id,
        format=format,
        template=template,
        filename=filename,
        include_metadata=include_metadata,
        ats_optimized=ats_optimized,
        custom_styling=custom_styling,
        sections_to_include=sections_to_include,
        apply_optimizations=apply_optimizations,
        optimization_results=optimization_results,
    )

    # Store request
    export_requests_store[export_request.id] = export_request

    # Process export in background
    background_tasks.add_task(process_single_export, export_request.id)

    return export_request


@router.post("/batch", response_model=BatchExportRequest)
async def create_batch_export_request(
    user_id: str,
    batch_name: str,
    version_ids: List[str],
    export_configs: List[Dict[str, Any]],
    output_format: str = "zip",
    include_manifest: bool = True,
    compress_output: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Create a batch export request for multiple resume versions"""

    # Create individual export requests
    export_requests = []
    for i, (version_id, config) in enumerate(zip(version_ids, export_configs)):
        export_request = ExportRequest(
            user_id=user_id,
            resume_id=version_id,
            format=config.get("format", "docx"),
            template=config.get("template", "modern"),
            filename=config.get("filename", f"{batch_name}_version_{i+1}"),
            include_metadata=config.get("include_metadata", True),
            ats_optimized=config.get("ats_optimized", False),
            custom_styling=config.get("custom_styling", {}),
            sections_to_include=config.get("sections_to_include", []),
            apply_optimizations=config.get("apply_optimizations", True),
            optimization_results=config.get("optimization_results"),
        )
        export_requests.append(export_request)

    # Create batch request
    batch_request = BatchExportRequest(
        user_id=user_id,
        batch_name=batch_name,
        export_requests=export_requests,
        output_format=output_format,
        include_manifest=include_manifest,
        compress_output=compress_output,
        total_items=len(export_requests),
    )

    # Store requests
    batch_requests_store[batch_request.id] = batch_request
    for req in export_requests:
        export_requests_store[req.id] = req

    # Process batch in background
    background_tasks.add_task(process_batch_export, batch_request.id)

    return batch_request


@router.get("/request/{request_id}", response_model=ExportRequest)
async def get_export_request(request_id: str):
    """Get export request status"""
    if request_id not in export_requests_store:
        raise HTTPException(status_code=404, detail="Export request not found")

    return export_requests_store[request_id]


@router.get("/batch/{batch_id}", response_model=BatchExportRequest)
async def get_batch_export_request(batch_id: str):
    """Get batch export request status"""
    if batch_id not in batch_requests_store:
        raise HTTPException(status_code=404, detail="Batch export request not found")

    return batch_requests_store[batch_id]


@router.get("/download/{request_id}")
async def download_export(request_id: str):
    """Download exported resume file"""
    if request_id not in export_requests_store:
        raise HTTPException(status_code=404, detail="Export request not found")

    export_request = export_requests_store[request_id]

    if export_request.status != "completed":
        raise HTTPException(status_code=400, detail="Export not completed yet")

    if not export_request.output_path or not os.path.exists(export_request.output_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Update download history
    if request_id not in export_history_store:
        export_history_store[request_id] = ExportHistory(
            user_id=export_request.user_id,
            export_request_id=request_id,
            format=export_request.format,
            template=export_request.template,
            filename=export_request.filename or "resume",
            file_size=export_request.file_size or 0,
            file_path=export_request.output_path,
        )

    history = export_history_store[request_id]
    history.download_count += 1
    history.last_downloaded = datetime.utcnow()
    history.download_history.append(datetime.utcnow())

    return FileResponse(
        path=export_request.output_path,
        filename=f"{export_request.filename}.{export_request.format}",
        media_type=get_media_type(export_request.format),
    )


@router.get("/download/batch/{batch_id}")
async def download_batch_export(batch_id: str):
    """Download batch export file"""
    if batch_id not in batch_requests_store:
        raise HTTPException(status_code=404, detail="Batch export request not found")

    batch_request = batch_requests_store[batch_id]

    if batch_request.status != "completed":
        raise HTTPException(status_code=400, detail="Batch export not completed yet")

    if not batch_request.output_path or not os.path.exists(batch_request.output_path):
        raise HTTPException(status_code=404, detail="Batch export file not found")

    filename = (
        f"{batch_request.batch_name}.zip"
        if batch_request.output_format == "zip"
        else batch_request.batch_name
    )
    media_type = (
        "application/zip"
        if batch_request.output_format == "zip"
        else "application/octet-stream"
    )

    return FileResponse(
        path=batch_request.output_path, filename=filename, media_type=media_type
    )


@router.get("/history/{user_id}")
async def get_export_history(user_id: str, limit: int = Query(50, le=100)):
    """Get user's export history"""
    user_history = [
        history
        for history in export_history_store.values()
        if history.user_id == user_id
    ]

    # Sort by creation date, most recent first
    user_history.sort(key=lambda x: x.created_at, reverse=True)

    return {"history": user_history[:limit]}


@router.get("/analytics/{user_id}")
async def get_export_analytics(user_id: str):
    """Get user's export analytics"""
    if user_id not in export_analytics_store:
        export_analytics_store[user_id] = ExportAnalytics(user_id=user_id)

    return export_analytics_store[user_id]


@router.post("/preview")
async def create_export_preview(
    resume_data: Dict[str, Any],
    format: str = "html",
    template: str = "modern",
    custom_styling: Dict[str, Any] = {},
):
    """Create a preview of the resume export"""

    try:
        # Create temporary export options for preview
        export_options = ExportOptions(
            format="html",  # Always use HTML for preview
            template=template,
            filename="preview",
            custom_styling=custom_styling,
        )

        # Generate preview
        preview_path = await resume_generator.generate_resume(
            resume_data, export_options
        )

        # Read preview content
        with open(preview_path, "r", encoding="utf-8") as f:
            preview_content = f.read()

        # Clean up preview file
        if os.path.exists(preview_path):
            os.remove(preview_path)

        preview = ExportPreview(
            export_request_id="preview",
            preview_type="html",
            preview_content=preview_content[:5000],  # Limit content length
        )

        return preview

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate preview: {str(e)}"
        )


# Background task functions
async def process_single_export(request_id: str):
    """Process a single export request"""
    try:
        export_request = export_requests_store[request_id]
        export_request.status = "processing"

        # Get resume data (mock for now)
        resume_data = await get_resume_data(export_request.resume_id)

        # Create export options
        export_options = ExportOptions(
            format=export_request.format,
            template=export_request.template,
            filename=export_request.filename,
            include_metadata=export_request.include_metadata,
            ats_optimized=export_request.ats_optimized,
            custom_styling=export_request.custom_styling,
            sections_to_include=export_request.sections_to_include,
        )

        # Generate resume
        output_path = await resume_generator.generate_resume(
            resume_data, export_options, export_request.optimization_results
        )

        # Update request
        export_request.status = "completed"
        export_request.completed_at = datetime.utcnow()
        export_request.output_path = output_path
        export_request.file_size = (
            os.path.getsize(output_path) if os.path.exists(output_path) else 0
        )

        # Update analytics
        await update_export_analytics(export_request)

    except Exception as e:
        export_request.status = "failed"
        export_request.error_message = str(e)


async def process_batch_export(batch_id: str):
    """Process a batch export request"""
    try:
        batch_request = batch_requests_store[batch_id]
        batch_request.status = "processing"
        batch_request.started_at = datetime.utcnow()

        # Process individual exports
        versions = []
        export_options_list = []

        for export_req in batch_request.export_requests:
            try:
                # Get resume data
                resume_data = await get_resume_data(export_req.resume_id)
                versions.append(resume_data)

                # Create export options
                export_options = ExportOptions(
                    format=export_req.format,
                    template=export_req.template,
                    filename=export_req.filename,
                    include_metadata=export_req.include_metadata,
                    ats_optimized=export_req.ats_optimized,
                    custom_styling=export_req.custom_styling,
                    sections_to_include=export_req.sections_to_include,
                )
                export_options_list.append(export_options)

                export_req.status = "completed"
                batch_request.completed_items += 1

            except Exception as e:
                export_req.status = "failed"
                export_req.error_message = str(e)
                batch_request.failed_items += 1

        # Create batch export request for service
        service_batch_request = ServiceBatchRequest(
            versions=versions,
            export_options=export_options_list,
            output_format=batch_request.output_format,
            batch_name=batch_request.batch_name,
        )

        # Generate batch export
        output_path = await resume_generator.batch_export(service_batch_request)

        # Update batch request
        batch_request.status = (
            "completed" if batch_request.failed_items == 0 else "partial"
        )
        batch_request.completed_at = datetime.utcnow()
        batch_request.output_path = output_path
        batch_request.total_size = (
            get_directory_size(output_path) if os.path.exists(output_path) else 0
        )
        batch_request.progress_percentage = 100.0

    except Exception as e:
        batch_request.status = "failed"
        batch_request.error_message = str(e)


async def get_resume_data(resume_id: str) -> Dict[str, Any]:
    """Get resume data by ID (mock implementation)"""
    # This would typically fetch from database
    # For now, return mock data
    return {
        "personal_details": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-0123",
            "linkedin": "linkedin.com/in/johndoe",
            "summary": "Experienced software developer with 5+ years of experience in full-stack development.",
        },
        "work_experience": [
            {
                "title": "Senior Software Developer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "to_date": "Present",
                "summary": "Lead development of web applications using React and Node.js",
                "achievements": [
                    "Improved application performance by 40%",
                    "Led team of 5 developers",
                    "Implemented CI/CD pipeline",
                ],
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "university": "State University",
                "from_year": "2015",
                "to_year": "2019",
            }
        ],
        "skills": [
            {
                "category": "Programming Languages",
                "skills": ["JavaScript", "Python", "Java", "TypeScript"],
            },
            {
                "category": "Frameworks",
                "skills": ["React", "Node.js", "Express", "Django"],
            },
        ],
        "projects": [
            {
                "name": "E-commerce Platform",
                "summary": "Full-stack e-commerce application with payment integration",
                "bullets": [
                    "Built with React and Node.js",
                    "Integrated Stripe payment processing",
                    "Deployed on AWS",
                ],
            }
        ],
    }


async def update_export_analytics(export_request: ExportRequest):
    """Update export analytics for user"""
    user_id = export_request.user_id

    if user_id not in export_analytics_store:
        export_analytics_store[user_id] = ExportAnalytics(user_id=user_id)

    analytics = export_analytics_store[user_id]
    analytics.total_exports += 1

    # Update format statistics
    if export_request.format not in analytics.exports_by_format:
        analytics.exports_by_format[export_request.format] = 0
    analytics.exports_by_format[export_request.format] += 1

    # Update template statistics
    if export_request.template not in analytics.exports_by_template:
        analytics.exports_by_template[export_request.template] = 0
    analytics.exports_by_template[export_request.template] += 1

    analytics.last_updated = datetime.utcnow()


def get_media_type(format: str) -> str:
    """Get media type for file format"""
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "txt": "text/plain",
        "json": "application/json",
        "html": "text/html",
    }
    return media_types.get(format, "application/octet-stream")


def get_directory_size(path: str) -> int:
    """Get total size of directory"""
    total_size = 0
    if os.path.isfile(path):
        return os.path.getsize(path)

    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    return total_size
