"""
Version Management API endpoints for resume version control
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Body,
    Query,
    Path,
    Depends,
)
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from services.version_manager import VersionManager
from models.resume_version import (
    ResumeVersion,
    VersionComparison,
    VersionHistory,
    VersionTemplate,
    VersionAnalytics,
)
from configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global version manager instance
version_manager = VersionManager()


@router.post("/versions")
async def create_version(
    user_id: str = Body(...),
    resume_data: Dict[str, Any] = Body(...),
    name: str = Body(...),
    description: Optional[str] = Body(None),
    job_target: Optional[str] = Body(None),
    optimization_type: Optional[str] = Body(None),
    tags: List[str] = Body([]),
):
    """Create a new resume version"""

    try:
        version = await version_manager.create_version(
            user_id=user_id,
            resume_data=resume_data,
            name=name,
            description=description,
            job_target=job_target,
            optimization_type=optimization_type,
            tags=tags,
        )

        return JSONResponse(
            {
                "success": True,
                "version": {
                    "id": version.id,
                    "name": version.name,
                    "description": version.description,
                    "version_number": version.version_number,
                    "created_at": version.created_at.isoformat(),
                    "overall_score": version.overall_score,
                    "ats_score": version.ats_score,
                    "keyword_score": version.keyword_score,
                    "tags": version.tags,
                    "job_target": version.job_target,
                    "optimization_type": version.optimization_type,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}")
async def get_version(
    version_id: str = Path(...),
    user_id: str = Query(...),
):
    """Get a specific version by ID"""

    try:
        version = await version_manager.get_version(version_id, user_id)

        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "version": {
                    "id": version.id,
                    "name": version.name,
                    "description": version.description,
                    "resume_data": version.resume_data,
                    "version_number": version.version_number,
                    "is_current": version.is_current,
                    "is_template": version.is_template,
                    "job_target": version.job_target,
                    "target_industry": version.target_industry,
                    "optimization_type": version.optimization_type,
                    "overall_score": version.overall_score,
                    "ats_score": version.ats_score,
                    "keyword_score": version.keyword_score,
                    "created_at": version.created_at.isoformat(),
                    "last_modified": version.last_modified.isoformat(),
                    "download_count": version.download_count,
                    "last_downloaded": (
                        version.last_downloaded.isoformat()
                        if version.last_downloaded
                        else None
                    ),
                    "tags": version.tags,
                    "category": version.category,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/versions")
async def list_versions(
    user_id: str = Path(...),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query(
        "created_at", regex="^(created_at|name|overall_score|version_number)$"
    ),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    tags: Optional[str] = Query(None),  # Comma-separated tags
    category: Optional[str] = Query(None),
):
    """List all versions for a user with filtering and sorting"""

    try:
        # Parse tags if provided
        tag_list = tags.split(",") if tags else None

        versions = await version_manager.list_versions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            tags=tag_list,
            category=category,
        )

        return JSONResponse(
            {
                "success": True,
                "versions": [
                    {
                        "id": version.id,
                        "name": version.name,
                        "description": version.description,
                        "version_number": version.version_number,
                        "is_current": version.is_current,
                        "is_template": version.is_template,
                        "job_target": version.job_target,
                        "optimization_type": version.optimization_type,
                        "overall_score": version.overall_score,
                        "ats_score": version.ats_score,
                        "keyword_score": version.keyword_score,
                        "created_at": version.created_at.isoformat(),
                        "last_modified": version.last_modified.isoformat(),
                        "download_count": version.download_count,
                        "tags": version.tags,
                        "category": version.category,
                    }
                    for version in versions
                ],
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": len(versions),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to list versions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/versions/{version_id}")
async def update_version(
    version_id: str = Path(...),
    user_id: str = Body(...),
    name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    job_target: Optional[str] = Body(None),
    optimization_type: Optional[str] = Body(None),
    tags: Optional[List[str]] = Body(None),
    category: Optional[str] = Body(None),
    is_current: Optional[bool] = Body(None),
    is_template: Optional[bool] = Body(None),
):
    """Update version metadata"""

    try:
        # Build updates dictionary
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if job_target is not None:
            updates["job_target"] = job_target
        if optimization_type is not None:
            updates["optimization_type"] = optimization_type
        if tags is not None:
            updates["tags"] = tags
        if category is not None:
            updates["category"] = category
        if is_current is not None:
            updates["is_current"] = is_current
        if is_template is not None:
            updates["is_template"] = is_template

        version = await version_manager.update_version(version_id, user_id, updates)

        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "version": {
                    "id": version.id,
                    "name": version.name,
                    "description": version.description,
                    "job_target": version.job_target,
                    "optimization_type": version.optimization_type,
                    "tags": version.tags,
                    "category": version.category,
                    "is_current": version.is_current,
                    "is_template": version.is_template,
                    "last_modified": version.last_modified.isoformat(),
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/versions/{version_id}")
async def delete_version(
    version_id: str = Path(...),
    user_id: str = Query(...),
):
    """Delete a version"""

    try:
        success = await version_manager.delete_version(version_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "message": f"Version {version_id} deleted successfully",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/compare")
async def compare_versions(
    version1_id: str = Body(...),
    version2_id: str = Body(...),
    user_id: str = Body(...),
):
    """Compare two versions and return detailed differences"""

    try:
        comparison = await version_manager.compare_versions(
            version1_id, version2_id, user_id
        )

        if not comparison:
            raise HTTPException(
                status_code=404, detail="One or both versions not found"
            )

        return JSONResponse(
            {
                "success": True,
                "comparison": {
                    "id": comparison.id,
                    "version1_id": comparison.version1_id,
                    "version2_id": comparison.version2_id,
                    "overall_similarity": comparison.overall_similarity,
                    "quality_difference": comparison.quality_difference,
                    "section_differences": comparison.section_differences,
                    "changes": {
                        "additions": comparison.additions,
                        "deletions": comparison.deletions,
                        "modifications": comparison.modifications,
                    },
                    "analysis": {
                        "improvements": comparison.improvements,
                        "regressions": comparison.regressions,
                        "neutral_changes": comparison.neutral_changes,
                    },
                    "recommendations": {
                        "merge_suggestions": comparison.merge_suggestions,
                        "rollback_recommendations": comparison.rollback_recommendations,
                    },
                    "comparison_date": comparison.comparison_date.isoformat(),
                },
                "versions": {
                    "version1": {
                        "id": comparison.version1.id,
                        "name": comparison.version1.name,
                        "created_at": comparison.version1.created_at.isoformat(),
                        "overall_score": comparison.version1.overall_score,
                    },
                    "version2": {
                        "id": comparison.version2.id,
                        "name": comparison.version2.name,
                        "created_at": comparison.version2.created_at.isoformat(),
                        "overall_score": comparison.version2.overall_score,
                    },
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/{version_id}/restore")
async def restore_version(
    version_id: str = Path(...),
    user_id: str = Body(...),
    create_backup: bool = Body(True),
):
    """Restore a version as the current active version"""

    try:
        restored_version = await version_manager.restore_version(
            version_id, user_id, create_backup
        )

        if not restored_version:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "message": f"Version {version_id} restored successfully",
                "restored_version": {
                    "id": restored_version.id,
                    "name": restored_version.name,
                    "description": restored_version.description,
                    "created_at": restored_version.created_at.isoformat(),
                    "is_current": restored_version.is_current,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}/history")
async def get_version_history(
    version_id: str = Path(...),
    user_id: str = Query(...),
):
    """Get detailed history for a version"""

    try:
        history = await version_manager.get_version_history(version_id, user_id)

        if not history:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "history": {
                    "version_id": history.version_id,
                    "total_changes": history.total_changes,
                    "major_revisions": history.major_revisions,
                    "minor_revisions": history.minor_revisions,
                    "sections_modified": history.sections_modified,
                    "most_changed_section": history.most_changed_section,
                    "change_frequency": history.change_frequency,
                    "first_created": history.first_created.isoformat(),
                    "last_modified": history.last_modified.isoformat(),
                    "modification_timeline": history.modification_timeline,
                    "changes": history.changes,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/{version_id}/template")
async def create_template(
    version_id: str = Path(...),
    user_id: str = Body(...),
    template_name: str = Body(...),
    template_description: str = Body(...),
    industry: Optional[str] = Body(None),
    experience_level: Optional[str] = Body(None),
    is_public: bool = Body(False),
):
    """Create a template from a successful version"""

    try:
        template = await version_manager.create_template(
            version_id=version_id,
            user_id=user_id,
            template_name=template_name,
            template_description=template_description,
            industry=industry,
            experience_level=experience_level,
            is_public=is_public,
        )

        if not template:
            raise HTTPException(status_code=404, detail="Version not found")

        return JSONResponse(
            {
                "success": True,
                "template": {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "industry": template.industry,
                    "experience_level": template.experience_level,
                    "is_public": template.is_public,
                    "created_at": template.created_at.isoformat(),
                    "created_by": template.created_by,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create template from version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}/analytics")
async def get_version_analytics(
    version_id: str = Path(...),
    user_id: str = Query(...),
):
    """Get analytics for a specific version"""

    try:
        analytics = await version_manager.get_analytics(user_id, version_id)

        if not analytics:
            # Initialize analytics if not found
            await version_manager._initialize_analytics(user_id, version_id)
            analytics = await version_manager.get_analytics(user_id, version_id)

        return JSONResponse(
            {
                "success": True,
                "analytics": {
                    "version_id": analytics.version_id,
                    "usage_metrics": {
                        "view_count": analytics.view_count,
                        "edit_count": analytics.edit_count,
                        "download_count": analytics.download_count,
                        "share_count": analytics.share_count,
                    },
                    "performance_metrics": {
                        "average_session_duration": analytics.average_session_duration,
                        "bounce_rate": analytics.bounce_rate,
                        "completion_rate": analytics.completion_rate,
                    },
                    "success_metrics": {
                        "job_applications": analytics.job_applications,
                        "interview_callbacks": analytics.interview_callbacks,
                        "job_offers": analytics.job_offers,
                    },
                    "tracking_period": {
                        "tracking_start": analytics.tracking_start.isoformat(),
                        "last_updated": analytics.last_updated.isoformat(),
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get analytics for version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/{version_id}/download")
async def track_download(
    version_id: str = Path(...),
    user_id: str = Body(...),
):
    """Track a version download for analytics"""

    try:
        # Update analytics
        await version_manager._update_analytics(user_id, version_id, "download")

        # Update version download count
        version = await version_manager.get_version(version_id, user_id)
        if version:
            await version_manager.update_version(
                version_id,
                user_id,
                {
                    "download_count": version.download_count + 1,
                    "last_downloaded": datetime.utcnow(),
                },
            )

        return JSONResponse(
            {
                "success": True,
                "message": "Download tracked successfully",
            }
        )

    except Exception as e:
        logger.error(f"Failed to track download for version {version_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/bulk-operations")
async def bulk_operations(
    user_id: str = Body(...),
    operation: str = Body(..., regex="^(delete|tag|categorize|export)$"),
    version_ids: List[str] = Body(...),
    parameters: Dict[str, Any] = Body({}),
):
    """Perform bulk operations on multiple versions"""

    try:
        results = []

        for version_id in version_ids:
            try:
                if operation == "delete":
                    success = await version_manager.delete_version(version_id, user_id)
                    results.append({"version_id": version_id, "success": success})

                elif operation == "tag":
                    tags = parameters.get("tags", [])
                    version = await version_manager.update_version(
                        version_id, user_id, {"tags": tags}
                    )
                    results.append(
                        {
                            "version_id": version_id,
                            "success": version is not None,
                            "tags": tags,
                        }
                    )

                elif operation == "categorize":
                    category = parameters.get("category")
                    version = await version_manager.update_version(
                        version_id, user_id, {"category": category}
                    )
                    results.append(
                        {
                            "version_id": version_id,
                            "success": version is not None,
                            "category": category,
                        }
                    )

                elif operation == "export":
                    # For export, we just return the version data
                    version = await version_manager.get_version(version_id, user_id)
                    results.append(
                        {
                            "version_id": version_id,
                            "success": version is not None,
                            "data": version.resume_data if version else None,
                        }
                    )

            except Exception as e:
                results.append(
                    {
                        "version_id": version_id,
                        "success": False,
                        "error": str(e),
                    }
                )

        return JSONResponse(
            {
                "success": True,
                "operation": operation,
                "results": results,
                "summary": {
                    "total": len(version_ids),
                    "successful": len([r for r in results if r["success"]]),
                    "failed": len([r for r in results if not r["success"]]),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to perform bulk operation {operation}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/cleanup")
async def cleanup_old_versions(
    user_id: str = Body(...),
    keep_count: int = Body(20, ge=5, le=100),
):
    """Clean up old versions for a user (keep most recent N versions)"""

    try:
        # Get all versions sorted by creation date
        versions = await version_manager.list_versions(
            user_id, sort_by="created_at", sort_order="desc"
        )

        # Keep current and template versions, plus the most recent ones
        versions_to_keep = []
        versions_to_delete = []

        for version in versions:
            if version.is_current or version.is_template:
                versions_to_keep.append(version)
            elif len(versions_to_keep) < keep_count:
                versions_to_keep.append(version)
            else:
                versions_to_delete.append(version)

        # Delete old versions
        deleted_count = 0
        for version in versions_to_delete:
            try:
                success = await version_manager.delete_version(version.id, user_id)
                if success:
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete version {version.id}: {e}")

        return JSONResponse(
            {
                "success": True,
                "message": f"Cleanup completed successfully",
                "summary": {
                    "total_versions": len(versions),
                    "kept_versions": len(versions_to_keep),
                    "deleted_versions": deleted_count,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to cleanup versions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/versions/health")
async def health_check():
    """Health check for version management service"""

    return JSONResponse(
        {
            "status": "healthy",
            "service": "version_management_api",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
