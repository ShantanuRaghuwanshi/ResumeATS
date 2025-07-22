"""
Section Optimization API endpoints for AI-powered resume section improvements
"""

from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from services.section_optimizer import SectionOptimizer
from models.conversation import ResumeContext
from models.optimization_request import OptimizationResult, ValidationResult
from configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global section optimizer instance
section_optimizer = SectionOptimizer()


@router.post("/section/optimize")
async def optimize_section(
    resume_id: str = Body(...),
    user_id: str = Body(...),
    section: str = Body(...),
    section_data: Any = Body(...),
    job_description: Optional[str] = Body(None),
    optimization_type: str = Body("general"),
    llm_provider: str = Body("openai"),
    llm_config: Dict[str, Any] = Body({}),
):
    """Optimize a specific resume section with AI assistance"""

    try:
        # Create resume context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data={"current_section_data": section_data},
        )

        # Optimize the section
        result = await section_optimizer.optimize_section(
            section_data=section_data,
            context=context,
            job_description=job_description,
            optimization_type=optimization_type,
            llm_provider=llm_provider,
            llm_config=llm_config,
        )

        return JSONResponse(
            {
                "success": True,
                "optimization_result": {
                    "request_id": result.request_id,
                    "optimized_content": result.optimized_content,
                    "suggestions": result.suggestions,
                    "improvement_score": result.improvement_score,
                    "ats_score": result.ats_score,
                    "keyword_density": result.keyword_density,
                    "readability_score": result.readability_score,
                    "changes_summary": result.changes_summary,
                    "processing_time": result.processing_time_seconds,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to optimize section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/section/suggestions")
async def get_section_suggestions(
    resume_id: str = Body(...),
    user_id: str = Body(...),
    section: str = Body(...),
    content: Any = Body(...),
    focus_areas: Optional[List[str]] = Body(None),
):
    """Generate improvement suggestions for a resume section"""

    try:
        # Create resume context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data={"current_section_data": content},
        )

        # Generate suggestions
        suggestions = await section_optimizer.suggest_improvements(
            section=section, content=content, context=context, focus_areas=focus_areas
        )

        return JSONResponse(
            {
                "success": True,
                "suggestions": [
                    {
                        "id": suggestion.id,
                        "type": suggestion.type,
                        "title": suggestion.title,
                        "description": suggestion.description,
                        "original_text": suggestion.original_text,
                        "suggested_text": suggestion.suggested_text,
                        "impact_score": suggestion.impact_score,
                        "reasoning": suggestion.reasoning,
                        "section": suggestion.section,
                        "confidence": suggestion.confidence,
                        "created_at": suggestion.created_at.isoformat(),
                    }
                    for suggestion in suggestions
                ],
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/section/validate")
async def validate_section_changes(
    resume_id: str = Body(...),
    user_id: str = Body(...),
    section: str = Body(...),
    original_content: Any = Body(...),
    modified_content: Any = Body(...),
):
    """Validate changes made to a resume section"""

    try:
        # Create resume context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data={
                "original": original_content,
                "modified": modified_content,
            },
        )

        # Validate changes
        validation_result = await section_optimizer.validate_changes(
            original=original_content, modified=modified_content, context=context
        )

        return JSONResponse(
            {
                "success": True,
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "suggestions": validation_result.suggestions,
                    "consistency_issues": validation_result.consistency_issues,
                    "ats_issues": validation_result.ats_issues,
                    "formatting_issues": validation_result.formatting_issues,
                    "overall_quality_score": validation_result.overall_quality_score,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to validate changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/analysis/{section}")
async def analyze_section(
    section: str,
    resume_id: str = Query(...),
    user_id: str = Query(...),
    content: str = Query(...),  # JSON string of section content
):
    """Analyze a specific resume section for strengths and weaknesses"""

    try:
        # Parse content from JSON string
        try:
            section_content = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON in content parameter"
            )

        # Create resume context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data={"current_section_data": section_content},
        )

        # Analyze section
        analysis = await section_optimizer._analyze_section(
            section_data=section_content, context=context
        )

        return JSONResponse(
            {
                "success": True,
                "analysis": {
                    "section": analysis.section,
                    "strengths": analysis.strengths,
                    "weaknesses": analysis.weaknesses,
                    "missing_elements": analysis.missing_elements,
                    "keyword_gaps": analysis.keyword_gaps,
                    "improvement_opportunities": analysis.improvement_opportunities,
                    "ats_compatibility_score": analysis.ats_compatibility_score,
                    "content_quality_score": analysis.content_quality_score,
                    "relevance_score": analysis.relevance_score,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/strategies")
async def get_optimization_strategies():
    """Get available optimization strategies for different sections"""

    try:
        strategies = {}

        for section_name, strategy in section_optimizer.optimization_strategies.items():
            strategies[section_name] = {
                "section_name": strategy.section_name,
                "key_elements": strategy.key_elements,
                "optimization_focus": strategy.optimization_focus,
                "common_issues": strategy.common_issues,
                "best_practices": strategy.best_practices,
                "ats_considerations": strategy.ats_considerations,
            }

        return JSONResponse({"success": True, "strategies": strategies})

    except Exception as e:
        logger.error(f"Failed to get optimization strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/action-verbs")
async def get_action_verbs():
    """Get categorized action verbs for resume improvement"""

    try:
        return JSONResponse(
            {"success": True, "action_verbs": section_optimizer.action_verbs}
        )

    except Exception as e:
        logger.error(f"Failed to get action verbs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/industry-keywords")
async def get_industry_keywords():
    """Get industry-specific keywords for optimization"""

    try:
        return JSONResponse(
            {"success": True, "industry_keywords": section_optimizer.industry_keywords}
        )

    except Exception as e:
        logger.error(f"Failed to get industry keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/section/batch-optimize")
async def batch_optimize_sections(
    resume_id: str = Body(...),
    user_id: str = Body(...),
    sections: Dict[str, Any] = Body(...),  # section_name -> section_data
    job_description: Optional[str] = Body(None),
    optimization_type: str = Body("general"),
    llm_provider: str = Body("openai"),
    llm_config: Dict[str, Any] = Body({}),
):
    """Optimize multiple resume sections in batch"""

    try:
        results = {}

        for section_name, section_data in sections.items():
            try:
                # Create context for this section
                context = ResumeContext(
                    resume_id=resume_id,
                    user_id=user_id,
                    current_section=section_name,
                    full_resume_data=sections,
                )

                # Optimize section
                result = await section_optimizer.optimize_section(
                    section_data=section_data,
                    context=context,
                    job_description=job_description,
                    optimization_type=optimization_type,
                    llm_provider=llm_provider,
                    llm_config=llm_config,
                )

                results[section_name] = {
                    "success": True,
                    "optimized_content": result.optimized_content,
                    "suggestions": result.suggestions,
                    "improvement_score": result.improvement_score,
                    "ats_score": result.ats_score,
                    "changes_summary": result.changes_summary,
                }

            except Exception as section_error:
                logger.error(
                    f"Failed to optimize section {section_name}: {section_error}"
                )
                results[section_name] = {"success": False, "error": str(section_error)}

        return JSONResponse({"success": True, "results": results})

    except Exception as e:
        logger.error(f"Failed to batch optimize sections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/section/compare")
async def compare_section_versions(
    section: str = Body(...),
    version1: Any = Body(...),
    version2: Any = Body(...),
    resume_id: str = Body(...),
    user_id: str = Body(...),
):
    """Compare two versions of a resume section"""

    try:
        # Create context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data={"version1": version1, "version2": version2},
        )

        # Analyze both versions
        analysis1 = await section_optimizer._analyze_section(version1, context)
        analysis2 = await section_optimizer._analyze_section(version2, context)

        # Calculate improvement metrics
        improvement_metrics = await section_optimizer._calculate_improvement_metrics(
            version1, version2, context
        )

        return JSONResponse(
            {
                "success": True,
                "comparison": {
                    "version1_analysis": {
                        "ats_score": analysis1.ats_compatibility_score,
                        "quality_score": analysis1.content_quality_score,
                        "relevance_score": analysis1.relevance_score,
                        "strengths": analysis1.strengths,
                        "weaknesses": analysis1.weaknesses,
                    },
                    "version2_analysis": {
                        "ats_score": analysis2.ats_compatibility_score,
                        "quality_score": analysis2.content_quality_score,
                        "relevance_score": analysis2.relevance_score,
                        "strengths": analysis2.strengths,
                        "weaknesses": analysis2.weaknesses,
                    },
                    "improvement_metrics": {
                        "before_score": improvement_metrics.before_score,
                        "after_score": improvement_metrics.after_score,
                        "improvement_percentage": improvement_metrics.improvement_percentage,
                        "ats_improvement": improvement_metrics.ats_improvement,
                        "keyword_improvement": improvement_metrics.keyword_improvement,
                        "readability_improvement": improvement_metrics.readability_improvement,
                        "content_quality_improvement": improvement_metrics.content_quality_improvement,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to compare section versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/section/health")
async def health_check():
    """Health check for section optimization service"""

    return JSONResponse(
        {
            "status": "healthy",
            "service": "section_optimization_api",
            "timestamp": datetime.utcnow().isoformat(),
            "available_sections": list(
                section_optimizer.optimization_strategies.keys()
            ),
        }
    )
