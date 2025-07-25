"""
API endpoints for user preference learning
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.user_preferences import UserProfile, SuggestionFeedback, LearningInsight
from models.conversation import ResumeContext, Suggestion
from services.preference_learning import preference_learning_service

router = APIRouter(prefix="/preference-learning", tags=["preference-learning"])


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback"""

    feedback: SuggestionFeedback
    user_profile: UserProfile


class PersonalizationRequest(BaseModel):
    """Request model for personalizing suggestions"""

    suggestions: List[Suggestion]
    user_profile: UserProfile
    context: ResumeContext


class PredictionRequest(BaseModel):
    """Request model for predicting user response"""

    suggestion: Suggestion
    user_profile: UserProfile
    context: ResumeContext


@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback for learning"""
    try:
        result = await preference_learning_service.process_feedback(
            request.feedback, request.user_profile
        )
        return {
            "success": True,
            "message": "Feedback processed successfully",
            "learning_results": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process feedback: {str(e)}"
        )


@router.post("/personalize", response_model=List[Suggestion])
async def personalize_suggestions(request: PersonalizationRequest):
    """Personalize suggestions based on user preferences"""
    try:
        personalized_suggestions = (
            await preference_learning_service.personalize_suggestions(
                request.suggestions, request.user_profile, request.context
            )
        )
        return personalized_suggestions
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to personalize suggestions: {str(e)}"
        )


@router.post("/predict", response_model=Dict[str, float])
async def predict_user_response(request: PredictionRequest):
    """Predict how user will likely respond to a suggestion"""
    try:
        prediction = await preference_learning_service.predict_user_preference(
            request.suggestion, request.user_profile, request.context
        )
        return prediction
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to predict user response: {str(e)}"
        )


@router.get("/insights/{user_id}", response_model=List[LearningInsight])
async def get_learning_insights(user_id: str):
    """Get learning insights for a user"""
    try:
        insights = await preference_learning_service.generate_learning_insights(user_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/confidence/{user_id}", response_model=Dict[str, float])
async def get_learning_confidence(user_id: str):
    """Get learning confidence for a user"""
    try:
        confidence = await preference_learning_service._calculate_learning_confidence(
            user_id
        )
        return {
            "user_id": user_id,
            "learning_confidence": confidence,
            "confidence_level": (
                "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get learning confidence: {str(e)}"
        )


@router.get("/patterns/{user_id}", response_model=Dict[str, Any])
async def get_user_patterns(user_id: str):
    """Get learned patterns for a user"""
    try:
        user_patterns = preference_learning_service.user_patterns.get(user_id, {})

        # Convert patterns to serializable format
        serializable_patterns = {}
        for pattern_name, pattern in user_patterns.items():
            serializable_patterns[pattern_name] = {
                "pattern_type": pattern.pattern_type,
                "confidence": pattern.confidence,
                "frequency": pattern.frequency,
                "last_seen": pattern.last_seen.isoformat(),
                "context": pattern.context,
            }

        return {
            "user_id": user_id,
            "patterns": serializable_patterns,
            "total_patterns": len(serializable_patterns),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user patterns: {str(e)}"
        )


@router.delete("/patterns/{user_id}")
async def reset_user_patterns(user_id: str):
    """Reset learned patterns for a user"""
    try:
        # Clear user patterns
        if user_id in preference_learning_service.user_patterns:
            del preference_learning_service.user_patterns[user_id]

        # Clear feedback history
        if user_id in preference_learning_service.feedback_history:
            del preference_learning_service.feedback_history[user_id]

        return {"success": True, "message": f"Reset learning data for user {user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset patterns: {str(e)}"
        )


@router.get("/stats/{user_id}", response_model=Dict[str, Any])
async def get_learning_stats(user_id: str):
    """Get comprehensive learning statistics for a user"""
    try:
        feedback_history = preference_learning_service.feedback_history.get(user_id, [])
        user_patterns = preference_learning_service.user_patterns.get(user_id, {})
        confidence = await preference_learning_service._calculate_learning_confidence(
            user_id
        )

        # Calculate statistics
        total_feedback = len(feedback_history)
        accepted_feedback = len(
            [fb for fb in feedback_history if fb.action == "accepted"]
        )
        rejected_feedback = len(
            [fb for fb in feedback_history if fb.action == "rejected"]
        )
        modified_feedback = len(
            [fb for fb in feedback_history if fb.action == "modified"]
        )

        acceptance_rate = (
            accepted_feedback / total_feedback if total_feedback > 0 else 0
        )

        # Section statistics
        section_stats = {}
        for fb in feedback_history:
            if fb.section not in section_stats:
                section_stats[fb.section] = {"total": 0, "accepted": 0}
            section_stats[fb.section]["total"] += 1
            if fb.action == "accepted":
                section_stats[fb.section]["accepted"] += 1

        # Add acceptance rates
        for section in section_stats:
            section_stats[section]["acceptance_rate"] = (
                section_stats[section]["accepted"] / section_stats[section]["total"]
            )

        return {
            "user_id": user_id,
            "learning_confidence": confidence,
            "total_feedback": total_feedback,
            "acceptance_rate": acceptance_rate,
            "feedback_breakdown": {
                "accepted": accepted_feedback,
                "rejected": rejected_feedback,
                "modified": modified_feedback,
            },
            "total_patterns": len(user_patterns),
            "section_statistics": section_stats,
            "most_active_sections": (
                sorted(
                    section_stats.keys(),
                    key=lambda x: section_stats[x]["total"],
                    reverse=True,
                )[:3]
                if section_stats
                else []
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get learning stats: {str(e)}"
        )
