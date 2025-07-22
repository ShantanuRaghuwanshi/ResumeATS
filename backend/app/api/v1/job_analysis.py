"""
Job Analysis API endpoints for enhanced job description analysis and resume matching.

This module provides endpoints for:
- Job description analysis and parsing
- Resume-to-job matching with detailed scoring
- Batch processing of multiple job descriptions
- Job comparison and ranking functionality
- Recommendation generation for resume improvements
"""

from fastapi import APIRouter, HTTPException, Body, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from models.job_analysis import (
    JobDescription,
    JobAnalysis,
    ResumeJobMatch,
    JobMatchRecommendation,
    JobComparisonResult,
)
from models.resume import ResumeDocument
from services.job_matcher import JobMatcher
from services.llm_provider import LLMProviderFactory
from configs.config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# In-memory storage for demo purposes - replace with proper database in production
job_analyses_store: Dict[str, JobAnalysis] = {}
job_matches_store: Dict[str, ResumeJobMatch] = {}
batch_results_store: Dict[str, Dict[str, Any]] = {}


@router.post("/job-analysis/analyze", response_model=JobAnalysis)
async def analyze_job_description(
    job_description: str = Body(..., embed=True),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Analyze a job description and extract comprehensive information.

    Args:
        job_description: Raw job description text
        provider_name: LLM provider to use (ollama, openai, claude, gemini)
        provider_config: Configuration for the LLM provider

    Returns:
        JobAnalysis object with extracted information
    """
    try:
        # Create LLM provider
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)

        # Create JobMatcher service
        job_matcher = JobMatcher(llm_provider)

        # Analyze job description
        job_analysis = await job_matcher.analyze_job_description(job_description)

        # Store the analysis
        job_analyses_store[job_analysis.id] = job_analysis

        logger.info(f"Successfully analyzed job description: {job_analysis.job_title}")
        return job_analysis

    except Exception as e:
        logger.error(f"Error analyzing job description: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze job description: {str(e)}"
        )


@router.get("/job-analysis/{analysis_id}", response_model=JobAnalysis)
async def get_job_analysis(analysis_id: str):
    """
    Retrieve a previously created job analysis.

    Args:
        analysis_id: ID of the job analysis to retrieve

    Returns:
        JobAnalysis object
    """
    if analysis_id not in job_analyses_store:
        raise HTTPException(status_code=404, detail="Job analysis not found")

    return job_analyses_store[analysis_id]


@router.get("/job-analysis", response_model=List[JobAnalysis])
async def list_job_analyses(
    limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)
):
    """
    List all job analyses with pagination.

    Args:
        limit: Maximum number of analyses to return
        offset: Number of analyses to skip

    Returns:
        List of JobAnalysis objects
    """
    analyses = list(job_analyses_store.values())
    total = len(analyses)

    # Sort by creation date (most recent first)
    analyses.sort(key=lambda x: x.analysis_date, reverse=True)

    # Apply pagination
    paginated_analyses = analyses[offset : offset + limit]

    return paginated_analyses


@router.post("/job-analysis/match", response_model=ResumeJobMatch)
async def match_resume_to_job(
    resume_data: Dict[str, Any] = Body(...),
    job_analysis_id: str = Body(..., embed=True),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Match a resume against a job analysis and generate detailed scoring.

    Args:
        resume_data: Resume data in structured format
        job_analysis_id: ID of the job analysis to match against
        provider_name: LLM provider to use
        provider_config: Configuration for the LLM provider

    Returns:
        ResumeJobMatch with detailed scoring and analysis
    """
    try:
        # Check if job analysis exists
        if job_analysis_id not in job_analyses_store:
            raise HTTPException(status_code=404, detail="Job analysis not found")

        job_analysis = job_analyses_store[job_analysis_id]

        # Create resume document from data
        resume = ResumeDocument(
            user_id="temp_user",  # In production, get from authentication
            sections=resume_data,
        )

        # Create LLM provider and JobMatcher
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)
        job_matcher = JobMatcher(llm_provider)

        # Perform matching
        match_result = await job_matcher.match_resume_to_job(resume, job_analysis)

        # Store the match result
        job_matches_store[match_result.id] = match_result

        logger.info(
            f"Successfully matched resume to job: {match_result.overall_match_score:.2f}"
        )
        return match_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error matching resume to job: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to match resume to job: {str(e)}"
        )


@router.get("/job-analysis/match/{match_id}", response_model=ResumeJobMatch)
async def get_job_match(match_id: str):
    """
    Retrieve a previously created job match result.

    Args:
        match_id: ID of the job match to retrieve

    Returns:
        ResumeJobMatch object
    """
    if match_id not in job_matches_store:
        raise HTTPException(status_code=404, detail="Job match not found")

    return job_matches_store[match_id]


@router.post(
    "/job-analysis/recommendations", response_model=List[JobMatchRecommendation]
)
async def generate_recommendations(
    section: str = Body(..., embed=True),
    job_analysis_id: str = Body(..., embed=True),
    current_content: Dict[str, Any] = Body(...),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Generate specific recommendations for improving a resume section based on job analysis.

    Args:
        section: Resume section name (work_experience, skills, projects, etc.)
        job_analysis_id: ID of the job analysis to base recommendations on
        current_content: Current content of the resume section
        provider_name: LLM provider to use
        provider_config: Configuration for the LLM provider

    Returns:
        List of specific recommendations
    """
    try:
        # Check if job analysis exists
        if job_analysis_id not in job_analyses_store:
            raise HTTPException(status_code=404, detail="Job analysis not found")

        job_analysis = job_analyses_store[job_analysis_id]

        # Create LLM provider and JobMatcher
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)
        job_matcher = JobMatcher(llm_provider)

        # Generate recommendations
        recommendations = await job_matcher.generate_section_recommendations(
            section, job_analysis, current_content
        )

        # Set match_id for all recommendations (in production, this would be from a real match)
        for rec in recommendations:
            rec.match_id = f"temp_match_{job_analysis_id}"

        logger.info(
            f"Generated {len(recommendations)} recommendations for section: {section}"
        )
        return recommendations

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.post("/job-analysis/batch-analyze")
async def batch_analyze_jobs(
    background_tasks: BackgroundTasks,
    job_descriptions: List[str] = Body(...),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Analyze multiple job descriptions in batch.

    Args:
        job_descriptions: List of job description texts
        provider_name: LLM provider to use
        provider_config: Configuration for the LLM provider

    Returns:
        Batch job ID for tracking progress
    """
    try:
        # Generate batch ID
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Initialize batch result
        batch_results_store[batch_id] = {
            "status": "processing",
            "total": len(job_descriptions),
            "completed": 0,
            "results": [],
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        # Start background processing
        background_tasks.add_task(
            _process_batch_job_analysis,
            batch_id,
            job_descriptions,
            provider_name,
            provider_config,
        )

        return JSONResponse(
            {
                "batch_id": batch_id,
                "status": "processing",
                "total_jobs": len(job_descriptions),
                "message": "Batch processing started. Use GET /job-analysis/batch/{batch_id} to check progress.",
            }
        )

    except Exception as e:
        logger.error(f"Error starting batch job analysis: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start batch processing: {str(e)}"
        )


@router.get("/job-analysis/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """
    Get the status of a batch job analysis.

    Args:
        batch_id: ID of the batch job

    Returns:
        Batch status and results
    """
    if batch_id not in batch_results_store:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return JSONResponse(batch_results_store[batch_id])


@router.post("/job-analysis/compare", response_model=JobComparisonResult)
async def compare_job_descriptions(
    job_analysis_ids: List[str] = Body(...),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Compare multiple job descriptions and find common requirements.

    Args:
        job_analysis_ids: List of job analysis IDs to compare
        provider_name: LLM provider to use
        provider_config: Configuration for the LLM provider

    Returns:
        JobComparisonResult with common skills, keywords, and trends
    """
    try:
        # Validate all job analyses exist
        job_analyses = []
        for job_id in job_analysis_ids:
            if job_id not in job_analyses_store:
                raise HTTPException(
                    status_code=404, detail=f"Job analysis {job_id} not found"
                )
            job_analyses.append(job_analyses_store[job_id])

        if len(job_analyses) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 job analyses required for comparison",
            )

        # Create LLM provider and JobMatcher
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)
        job_matcher = JobMatcher(llm_provider)

        # Perform comparison
        comparison_result = await _compare_job_analyses(job_analyses, job_matcher)

        logger.info(f"Successfully compared {len(job_analyses)} job descriptions")
        return comparison_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing job descriptions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to compare job descriptions: {str(e)}"
        )


@router.post("/job-analysis/rank-matches")
async def rank_resume_matches(
    resume_data: Dict[str, Any] = Body(...),
    job_analysis_ids: List[str] = Body(...),
    provider_name: str = Body("ollama", embed=True),
    provider_config: Dict[str, Any] = Body({}, embed=True),
):
    """
    Rank multiple job descriptions by how well they match a resume.

    Args:
        resume_data: Resume data in structured format
        job_analysis_ids: List of job analysis IDs to rank
        provider_name: LLM provider to use
        provider_config: Configuration for the LLM provider

    Returns:
        List of job matches ranked by score
    """
    try:
        # Validate all job analyses exist
        job_analyses = []
        for job_id in job_analysis_ids:
            if job_id not in job_analyses_store:
                raise HTTPException(
                    status_code=404, detail=f"Job analysis {job_id} not found"
                )
            job_analyses.append(job_analyses_store[job_id])

        # Create resume document
        resume = ResumeDocument(user_id="temp_user", sections=resume_data)

        # Create LLM provider and JobMatcher
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)
        job_matcher = JobMatcher(llm_provider)

        # Calculate match scores for all jobs
        ranked_matches = []
        for job_analysis in job_analyses:
            match_result = await job_matcher.match_resume_to_job(resume, job_analysis)
            ranked_matches.append(
                {
                    "job_analysis_id": job_analysis.id,
                    "job_title": job_analysis.job_title,
                    "company": job_analysis.company,
                    "match_score": match_result.overall_match_score,
                    "recommendation": match_result.recommendation,
                    "skill_match_percentage": match_result.skill_match_percentage,
                    "missing_required_skills": match_result.missing_required_skills,
                    "match_details": match_result,
                }
            )

        # Sort by match score (highest first)
        ranked_matches.sort(key=lambda x: x["match_score"], reverse=True)

        logger.info(f"Successfully ranked {len(ranked_matches)} job matches")
        return JSONResponse(
            {
                "total_jobs": len(ranked_matches),
                "ranked_matches": ranked_matches,
                "best_match": ranked_matches[0] if ranked_matches else None,
                "average_score": (
                    sum(match["match_score"] for match in ranked_matches)
                    / len(ranked_matches)
                    if ranked_matches
                    else 0
                ),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ranking resume matches: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to rank resume matches: {str(e)}"
        )


# Background task functions


async def _process_batch_job_analysis(
    batch_id: str,
    job_descriptions: List[str],
    provider_name: str,
    provider_config: Dict[str, Any],
):
    """Background task to process batch job analysis."""
    try:
        # Create LLM provider and JobMatcher
        llm_provider = LLMProviderFactory.create(provider_name, provider_config)
        job_matcher = JobMatcher(llm_provider)

        results = []
        errors = []

        for i, job_desc in enumerate(job_descriptions):
            try:
                # Analyze job description
                job_analysis = await job_matcher.analyze_job_description(job_desc)

                # Store the analysis
                job_analyses_store[job_analysis.id] = job_analysis

                results.append(
                    {
                        "index": i,
                        "job_analysis_id": job_analysis.id,
                        "job_title": job_analysis.job_title,
                        "company": job_analysis.company,
                        "confidence_score": job_analysis.confidence_score,
                    }
                )

                # Update progress
                batch_results_store[batch_id]["completed"] = len(results)
                batch_results_store[batch_id]["results"] = results

            except Exception as e:
                error_info = {
                    "index": i,
                    "error": str(e),
                    "job_description_preview": (
                        job_desc[:100] + "..." if len(job_desc) > 100 else job_desc
                    ),
                }
                errors.append(error_info)
                batch_results_store[batch_id]["errors"] = errors

        # Mark as completed
        batch_results_store[batch_id]["status"] = "completed"
        batch_results_store[batch_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"Batch job analysis completed: {batch_id}, {len(results)} successful, {len(errors)} errors"
        )

    except Exception as e:
        # Mark as failed
        batch_results_store[batch_id]["status"] = "failed"
        batch_results_store[batch_id]["error"] = str(e)
        batch_results_store[batch_id]["failed_at"] = datetime.utcnow().isoformat()

        logger.error(f"Batch job analysis failed: {batch_id}, error: {str(e)}")


async def _compare_job_analyses(
    job_analyses: List[JobAnalysis], job_matcher: JobMatcher
) -> JobComparisonResult:
    """Compare multiple job analyses and find common patterns."""

    # Collect all skills and keywords
    all_required_skills = []
    all_preferred_skills = []
    all_keywords = []
    all_responsibilities = []
    experience_requirements = []

    for analysis in job_analyses:
        all_required_skills.extend(
            [skill.name.lower() for skill in analysis.required_skills]
        )
        all_preferred_skills.extend(
            [skill.name.lower() for skill in analysis.preferred_skills]
        )
        all_keywords.extend(analysis.industry_keywords)
        all_responsibilities.extend(analysis.key_responsibilities)

        if analysis.min_years_experience:
            experience_requirements.append(analysis.min_years_experience)

    # Find common elements
    skill_frequency = {}
    for skill in all_required_skills + all_preferred_skills:
        skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

    keyword_frequency = {}
    for keyword in all_keywords:
        keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1

    # Find skills/keywords that appear in at least half of the jobs
    min_frequency = len(job_analyses) // 2 + 1
    common_skills = [
        skill for skill, freq in skill_frequency.items() if freq >= min_frequency
    ]
    common_keywords = [
        keyword for keyword, freq in keyword_frequency.items() if freq >= min_frequency
    ]

    # Find common responsibilities (simplified - look for similar phrases)
    common_responsibilities = []
    responsibility_words = {}
    for resp in all_responsibilities:
        words = resp.lower().split()
        for word in words:
            if len(word) > 4:  # Only consider meaningful words
                responsibility_words[word] = responsibility_words.get(word, 0) + 1

    common_resp_words = [
        word for word, freq in responsibility_words.items() if freq >= min_frequency
    ]
    if common_resp_words:
        common_responsibilities = [
            f"Responsibilities involving: {', '.join(common_resp_words[:5])}"
        ]

    # Calculate average experience requirement
    avg_experience = (
        sum(experience_requirements) / len(experience_requirements)
        if experience_requirements
        else None
    )

    # Create merged requirements (simplified)
    merged_analysis = JobAnalysis(
        job_description_id="merged",
        job_title="Merged Job Analysis",
        industry="Multiple",
        required_skills=[],  # Would need to create SkillRequirement objects
        preferred_skills=[],
        technical_skills=common_skills,
        soft_skills=[],
        industry_keywords=common_keywords,
        key_responsibilities=common_responsibilities,
        min_years_experience=int(avg_experience) if avg_experience else None,
        confidence_score=0.8,
    )

    return JobComparisonResult(
        job_ids=[analysis.id for analysis in job_analyses],
        common_skills=common_skills,
        common_keywords=common_keywords,
        skill_frequency=skill_frequency,
        keyword_frequency=keyword_frequency,
        average_experience_requirement=avg_experience,
        common_responsibilities=common_responsibilities,
        industry_trends=(
            [f"High demand for: {', '.join(common_skills[:5])}"]
            if common_skills
            else []
        ),
        merged_requirements=merged_analysis,
    )
