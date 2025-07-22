"""
Feedback API endpoints for real-time resume feedback functionality
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Body,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime

from services.feedback_analyzer import FeedbackAnalyzer
from models.feedback import (
    ATSCompatibilityResult,
    ConsistencyReport,
    ChangeImpactAnalysis,
    RealTimeFeedback,
    UserFeedback,
)
from models.conversation import ResumeContext
from configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global feedback analyzer instance
feedback_analyzer = FeedbackAnalyzer()


# WebSocket connection manager for real-time feedback
class FeedbackConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_contexts: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Feedback WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
        logger.info(f"Feedback WebSocket disconnected for session {session_id}")

    async def send_feedback(self, session_id: str, feedback: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "real_time_feedback",
                            "feedback": feedback,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send feedback via WebSocket: {e}")
                self.disconnect(session_id)

    def set_session_context(self, session_id: str, context: Dict[str, Any]):
        self.session_contexts[session_id] = context

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.session_contexts.get(session_id)


feedback_connection_manager = FeedbackConnectionManager()


@router.post("/feedback/change-impact")
async def analyze_change_impact(
    before_content: Dict[str, Any] = Body(...),
    after_content: Dict[str, Any] = Body(...),
    resume_id: str = Body(...),
    user_id: str = Body(...),
    section: str = Body(...),
    full_resume_data: Dict[str, Any] = Body(...),
    job_description: Optional[str] = Body(None),
):
    """Analyze the impact of changes made to resume content"""

    try:
        # Create resume context
        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section=section,
            full_resume_data=full_resume_data,
            job_description=job_description,
        )

        # Analyze change impact
        analysis = await feedback_analyzer.analyze_change_impact(
            before=before_content, after=after_content, context=context
        )

        return JSONResponse(
            {
                "success": True,
                "analysis": {
                    "change_id": analysis.change_id,
                    "section": analysis.section,
                    "change_type": analysis.change_type,
                    "overall_impact": analysis.overall_impact,
                    "ats_impact": analysis.ats_impact,
                    "keyword_impact": analysis.keyword_impact,
                    "readability_impact": analysis.readability_impact,
                    "relevance_impact": analysis.relevance_impact,
                    "positive_changes": analysis.positive_changes,
                    "negative_changes": analysis.negative_changes,
                    "neutral_changes": analysis.neutral_changes,
                    "further_improvements": analysis.further_improvements,
                    "warnings": analysis.warnings,
                    "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to analyze change impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/ats-compatibility")
async def check_ats_compatibility(
    content: Dict[str, Any] = Body(...),
    section: Optional[str] = Body(None),
):
    """Check ATS compatibility of resume content"""

    try:
        result = await feedback_analyzer.check_ats_compatibility(
            content=content, section=section
        )

        return JSONResponse(
            {
                "success": True,
                "ats_compatibility": {
                    "overall_score": result.overall_score,
                    "parsing_score": result.parsing_score,
                    "formatting_score": result.formatting_score,
                    "keyword_score": result.keyword_score,
                    "structure_score": result.structure_score,
                    "formatting_issues": result.formatting_issues,
                    "parsing_issues": result.parsing_issues,
                    "missing_sections": result.missing_sections,
                    "problematic_elements": result.problematic_elements,
                    "recommendations": result.recommendations,
                    "quick_fixes": result.quick_fixes,
                    "analysis_date": result.analysis_date.isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to check ATS compatibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/consistency-validation")
async def validate_consistency(
    resume: Dict[str, Any] = Body(...),
):
    """Validate consistency across resume sections"""

    try:
        report = await feedback_analyzer.validate_consistency(resume)

        return JSONResponse(
            {
                "success": True,
                "consistency_report": {
                    "overall_consistency_score": report.overall_consistency_score,
                    "date_consistency": report.date_consistency,
                    "formatting_consistency": report.formatting_consistency,
                    "tone_consistency": report.tone_consistency,
                    "terminology_consistency": report.terminology_consistency,
                    "date_conflicts": report.date_conflicts,
                    "formatting_inconsistencies": report.formatting_inconsistencies,
                    "tone_variations": report.tone_variations,
                    "terminology_conflicts": report.terminology_conflicts,
                    "skill_redundancy": report.skill_redundancy,
                    "missing_cross_references": report.missing_cross_references,
                    "contradictory_information": report.contradictory_information,
                    "recommendations": report.recommendations,
                    "created_at": report.created_at.isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to validate consistency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/real-time")
async def generate_real_time_feedback(
    session_id: str = Body(...),
    section: str = Body(...),
    current_content: str = Body(...),
    previous_content: Optional[str] = Body(None),
):
    """Generate real-time feedback for live editing"""

    try:
        feedback = await feedback_analyzer.generate_real_time_feedback(
            session_id=session_id,
            section=section,
            current_content=current_content,
            previous_content=previous_content,
        )

        # Send feedback via WebSocket if connected
        feedback_data = {
            "session_id": feedback.session_id,
            "section": feedback.section,
            "character_count": feedback.character_count,
            "word_count": feedback.word_count,
            "readability_score": feedback.readability_score,
            "keyword_density": feedback.keyword_density,
            "grammar_issues": feedback.grammar_issues,
            "style_suggestions": feedback.style_suggestions,
            "keyword_suggestions": feedback.keyword_suggestions,
            "current_quality_score": feedback.current_quality_score,
            "ats_compatibility": feedback.ats_compatibility,
            "improvement_since_last": feedback.improvement_since_last,
            "timestamp": feedback.timestamp.isoformat(),
        }

        await feedback_connection_manager.send_feedback(session_id, feedback_data)

        return JSONResponse({"success": True, "feedback": feedback_data})

    except Exception as e:
        logger.error(f"Failed to generate real-time feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/aggregate-scores")
async def calculate_aggregate_scores(
    resume: Dict[str, Any] = Body(...),
    job_description: Optional[str] = Body(None),
):
    """Calculate aggregated feedback scores for the entire resume"""

    try:
        # Calculate overall scores
        ats_result = await feedback_analyzer.check_ats_compatibility(resume)
        consistency_report = await feedback_analyzer.validate_consistency(resume)

        # Calculate section-specific scores
        section_scores = {}
        for section_name, section_content in resume.items():
            if section_content and section_name in [
                "work_experience",
                "education",
                "skills",
                "summary",
            ]:
                content_str = str(section_content)
                quality_score = (
                    await feedback_analyzer._calculate_content_quality_score(
                        content_str, section_name
                    )
                )
                ats_score = await feedback_analyzer._calculate_ats_score(
                    content_str, section_name
                )

                section_scores[section_name] = {
                    "quality_score": quality_score,
                    "ats_score": ats_score,
                    "character_count": len(content_str),
                    "word_count": len(content_str.split()),
                }

        # Calculate overall resume score
        overall_quality = sum(
            scores["quality_score"] for scores in section_scores.values()
        ) / max(1, len(section_scores))
        overall_ats = ats_result.overall_score
        overall_consistency = consistency_report.overall_consistency_score

        # Weighted overall score
        overall_score = (
            overall_quality * 0.4 + overall_ats * 0.35 + overall_consistency * 0.25
        )

        return JSONResponse(
            {
                "success": True,
                "aggregate_scores": {
                    "overall_score": overall_score,
                    "overall_quality": overall_quality,
                    "overall_ats": overall_ats,
                    "overall_consistency": overall_consistency,
                    "section_scores": section_scores,
                    "total_character_count": sum(
                        scores["character_count"] for scores in section_scores.values()
                    ),
                    "total_word_count": sum(
                        scores["word_count"] for scores in section_scores.values()
                    ),
                    "calculated_at": datetime.utcnow().isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to calculate aggregate scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/performance-metrics")
async def track_performance_metrics(
    session_id: str = Body(...),
    user_id: str = Body(...),
    action: str = Body(...),  # "edit", "suggestion_applied", "feedback_viewed", etc.
    section: str = Body(...),
    metrics: Dict[str, Any] = Body(...),  # Custom metrics data
):
    """Track performance metrics for feedback system"""

    try:
        # Store performance metrics
        from database import get_database

        db = get_database()

        metric_data = {
            "session_id": session_id,
            "user_id": user_id,
            "action": action,
            "section": section,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in performance_metrics collection
        metric_id = f"{session_id}_{action}_{datetime.utcnow().timestamp()}"
        db.create("performance_metrics", metric_id, metric_data)

        return JSONResponse(
            {
                "success": True,
                "message": "Performance metrics tracked successfully",
                "metric_id": metric_id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to track performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/performance-metrics/{user_id}")
async def get_performance_metrics(
    user_id: str,
    session_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Get performance metrics for analysis"""

    try:
        from database import get_database

        db = get_database()

        # Build filter criteria
        filter_criteria = {"user_id": user_id}
        if session_id:
            filter_criteria["session_id"] = session_id
        if action:
            filter_criteria["action"] = action
        if section:
            filter_criteria["section"] = section

        # Get metrics
        metrics = db.find("performance_metrics", **filter_criteria)

        # Sort by timestamp and limit
        metrics.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        metrics = metrics[:limit]

        return JSONResponse(
            {"success": True, "metrics": metrics, "total_count": len(metrics)}
        )

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/user-feedback")
async def submit_user_feedback(
    user_id: str = Body(...),
    rating: int = Body(..., ge=1, le=5),
    feedback_type: str = Body(...),
    comment: Optional[str] = Body(None),
    suggestion_id: Optional[str] = Body(None),
    session_id: Optional[str] = Body(None),
    section: Optional[str] = Body(None),
    feature_used: Optional[str] = Body(None),
    helpful: Optional[bool] = Body(None),
    would_recommend: Optional[bool] = Body(None),
):
    """Submit user feedback on AI suggestions and system performance"""

    try:
        from database import get_database

        db = get_database()

        feedback = UserFeedback(
            user_id=user_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
            suggestion_id=suggestion_id,
            session_id=session_id,
            section=section,
            feature_used=feature_used,
            helpful=helpful,
            would_recommend=would_recommend,
        )

        # Store feedback
        db.create("user_feedback", feedback.id, feedback.model_dump())

        return JSONResponse(
            {
                "success": True,
                "message": "User feedback submitted successfully",
                "feedback_id": feedback.id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to submit user feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/feedback/{session_id}/ws")
async def feedback_websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time feedback delivery"""

    try:
        await feedback_connection_manager.connect(websocket, session_id)

        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "feedback_connection_established",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                if message_data.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        )
                    )

                elif message_data.get("type") == "set_context":
                    # Set session context for feedback
                    context = message_data.get("context", {})
                    feedback_connection_manager.set_session_context(session_id, context)

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "context_set",
                                "message": "Session context updated successfully",
                            }
                        )
                    )

                elif message_data.get("type") == "request_feedback":
                    # Generate real-time feedback
                    section = message_data.get("section", "")
                    current_content = message_data.get("current_content", "")
                    previous_content = message_data.get("previous_content")

                    if section and current_content:
                        feedback = await feedback_analyzer.generate_real_time_feedback(
                            session_id=session_id,
                            section=section,
                            current_content=current_content,
                            previous_content=previous_content,
                        )

                        feedback_data = {
                            "session_id": feedback.session_id,
                            "section": feedback.section,
                            "character_count": feedback.character_count,
                            "word_count": feedback.word_count,
                            "readability_score": feedback.readability_score,
                            "keyword_density": feedback.keyword_density,
                            "grammar_issues": feedback.grammar_issues,
                            "style_suggestions": feedback.style_suggestions,
                            "keyword_suggestions": feedback.keyword_suggestions,
                            "current_quality_score": feedback.current_quality_score,
                            "ats_compatibility": feedback.ats_compatibility,
                            "improvement_since_last": feedback.improvement_since_last,
                            "timestamp": feedback.timestamp.isoformat(),
                        }

                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "real_time_feedback",
                                    "feedback": feedback_data,
                                }
                            )
                        )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Feedback WebSocket error: {e}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": str(e)})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Feedback WebSocket connection error: {e}")
    finally:
        feedback_connection_manager.disconnect(session_id)


# Health check endpoint
@router.get("/feedback/health")
async def health_check():
    """Health check for feedback service"""

    return JSONResponse(
        {
            "status": "healthy",
            "service": "feedback_api",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(feedback_connection_manager.active_connections),
        }
    )
