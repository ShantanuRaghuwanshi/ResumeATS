from typing import Dict, Any, Optional, List
from app.services.llm_provider import LLMProviderFactory
from app.configs.config import get_logger
import asyncio

logger = get_logger(__name__)


async def optimize_resume_for_jd(
    parsed: Dict[str, Any],
    jd: str,
    provider_name: str = "ollama",
    provider_config: Optional[Dict[str, Any]] = None,
    optimization_goals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Optimize resume for job description using AI/LLM providers.

    Args:
        parsed: Parsed resume data dictionary
        jd: Job description text
        provider_name: LLM provider to use ("ollama", "openai", "claude", "gemini")
        provider_config: Configuration for the LLM provider
        optimization_goals: List of optimization goals

    Returns:
        Optimized resume data with metadata
    """
    try:
        # Default provider config if none provided
        if provider_config is None:
            provider_config = {"model": "gemma3n:e4b", "url": "http://localhost:11434"}

        # Create LLM provider
        provider = LLMProviderFactory.create(provider_name, provider_config)

        # Use the new optimize_resume method
        optimized_resume = await provider.optimize_resume(
            resume_data=parsed,
            job_description=jd,
            optimization_goals=optimization_goals,
        )

        return optimized_resume

    except Exception as e:
        logger.error(f"Error optimizing resume with {provider_name}: {e}")

        # Fallback to simple keyword matching if LLM fails
        return _fallback_optimization(parsed, jd)


def _fallback_optimization(parsed: Dict[str, Any], jd: str) -> Dict[str, Any]:
    """
    Fallback optimization using simple keyword matching.
    Used when LLM optimization fails.
    """
    import re

    logger.info("Using fallback optimization method")

    # Extract keywords from job description
    jd_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", jd.lower()))

    # Common technical and professional keywords to prioritize
    priority_keywords = {
        "python",
        "javascript",
        "react",
        "node",
        "sql",
        "aws",
        "docker",
        "kubernetes",
        "agile",
        "scrum",
        "api",
        "rest",
        "microservices",
        "machine learning",
        "data science",
        "analytics",
        "visualization",
        "leadership",
        "management",
        "communication",
        "collaboration",
        "problem solving",
        "critical thinking",
        "innovation",
    }

    # Find relevant keywords
    relevant_keywords = jd_words.intersection(priority_keywords)

    # Enhance skills section
    if "skills" in parsed:
        current_skills = parsed.get("skills", "").lower()
        missing_skills = [kw for kw in relevant_keywords if kw not in current_skills]

        if missing_skills:
            enhanced_skills = (
                parsed["skills"]
                + "\n"
                + "Additional relevant skills: "
                + ", ".join(missing_skills)
            )
            parsed["skills"] = enhanced_skills

    # Add optimization metadata
    parsed["optimization_metadata"] = {
        "optimization_method": "fallback_keyword_matching",
        "keywords_added": list(relevant_keywords),
        "optimization_timestamp": "fallback_applied",
        "fallback_reason": "LLM optimization failed",
    }

    return parsed


def optimize_resume_for_jd_sync(parsed: dict, jd: str) -> dict:
    """
    Synchronous wrapper for backward compatibility.
    This will be deprecated in favor of the async version.
    """
    try:
        # Run the async function in a new event loop
        return asyncio.run(optimize_resume_for_jd(parsed, jd))
    except Exception as e:
        logger.error(f"Error in sync optimization wrapper: {e}")
        return _fallback_optimization(parsed, jd)


# Backward compatibility - keep the original function name
def optimize_resume_for_jd_old(parsed: dict, jd: str) -> dict:
    """
    Original simple optimization function for backward compatibility.
    """
    return _fallback_optimization(parsed, jd)
