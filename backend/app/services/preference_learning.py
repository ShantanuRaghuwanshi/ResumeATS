"""
User Preference Learning Service

This service implements machine learning capabilities to learn from user feedback
and personalize AI suggestions based on user behavior patterns.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict, Counter
import asyncio
from dataclasses import dataclass

from models.user_preferences import (
    UserProfile,
    SuggestionFeedback,
    UserPreference,
    LearningInsight,
    PersonalizationSettings,
)
from models.conversation import Suggestion, ResumeContext


@dataclass
class PreferencePattern:
    """Represents a learned preference pattern"""

    pattern_type: str
    confidence: float
    frequency: int
    last_seen: datetime
    context: Dict[str, Any]


class PreferenceLearningService:
    """Service for learning user preferences and personalizing suggestions"""

    def __init__(self):
        self.user_patterns: Dict[str, Dict[str, PreferencePattern]] = defaultdict(dict)
        self.feedback_history: Dict[str, List[SuggestionFeedback]] = defaultdict(list)
        self.learning_weights = {
            "acceptance_rate": 0.3,
            "time_to_decision": 0.2,
            "feedback_rating": 0.25,
            "context_similarity": 0.15,
            "recency": 0.1,
        }

    async def process_feedback(
        self, feedback: SuggestionFeedback, user_profile: UserProfile
    ) -> Dict[str, Any]:
        """Process user feedback and update learning patterns"""

        # Store feedback in history
        self.feedback_history[feedback.user_id].append(feedback)

        # Extract patterns from feedback
        patterns = await self._extract_patterns_from_feedback(feedback, user_profile)

        # Update user patterns
        for pattern in patterns:
            await self._update_user_pattern(feedback.user_id, pattern)

        # Generate insights
        insights = await self._generate_insights(feedback.user_id, feedback)

        # Update user profile
        updated_profile = await self._update_user_profile(
            user_profile, feedback, patterns
        )

        return {
            "patterns_learned": len(patterns),
            "insights_generated": len(insights),
            "profile_updated": updated_profile is not None,
            "learning_confidence": await self._calculate_learning_confidence(
                feedback.user_id
            ),
        }

    async def personalize_suggestions(
        self,
        suggestions: List[Suggestion],
        user_profile: UserProfile,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Personalize suggestions based on learned user preferences"""

        if not suggestions:
            return suggestions

        # Get user patterns
        user_patterns = self.user_patterns.get(user_profile.user_id, {})

        # Score and rank suggestions
        scored_suggestions = []
        for suggestion in suggestions:
            score = await self._calculate_suggestion_score(
                suggestion, user_profile, context, user_patterns
            )
            suggestion.confidence = min(suggestion.confidence * score, 1.0)
            scored_suggestions.append((suggestion, score))

        # Sort by score (descending)
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)

        # Filter low-confidence suggestions if user prefers conservative approach
        settings = await self._get_personalization_settings(user_profile.user_id)
        if settings and settings.suggestion_aggressiveness == "conservative":
            scored_suggestions = [
                (sugg, score)
                for sugg, score in scored_suggestions
                if sugg.confidence >= 0.7
            ]

        return [sugg for sugg, _ in scored_suggestions]

    async def predict_user_preference(
        self, suggestion: Suggestion, user_profile: UserProfile, context: ResumeContext
    ) -> Dict[str, float]:
        """Predict user's likely response to a suggestion"""

        user_patterns = self.user_patterns.get(user_profile.user_id, {})
        feedback_history = self.feedback_history.get(user_profile.user_id, [])

        if not feedback_history:
            return {
                "acceptance_probability": 0.5,
                "rejection_probability": 0.3,
                "modification_probability": 0.2,
                "confidence": 0.1,
            }

        # Analyze similar past suggestions
        similar_feedback = await self._find_similar_feedback(
            suggestion, context, feedback_history
        )

        if not similar_feedback:
            return {
                "acceptance_probability": 0.5,
                "rejection_probability": 0.3,
                "modification_probability": 0.2,
                "confidence": 0.2,
            }

        # Calculate probabilities based on historical data
        actions = [fb.action for fb in similar_feedback]
        action_counts = Counter(actions)
        total = len(actions)

        return {
            "acceptance_probability": action_counts.get("accepted", 0) / total,
            "rejection_probability": action_counts.get("rejected", 0) / total,
            "modification_probability": action_counts.get("modified", 0) / total,
            "confidence": min(
                len(similar_feedback) / 10, 1.0
            ),  # More data = higher confidence
        }

    async def generate_learning_insights(self, user_id: str) -> List[LearningInsight]:
        """Generate insights about user learning patterns"""

        feedback_history = self.feedback_history.get(user_id, [])
        user_patterns = self.user_patterns.get(user_id, {})

        insights = []

        # Analyze acceptance patterns
        if len(feedback_history) >= 5:
            acceptance_insight = await self._analyze_acceptance_patterns(
                feedback_history
            )
            if acceptance_insight:
                insights.append(acceptance_insight)

        # Analyze section preferences
        if len(feedback_history) >= 10:
            section_insight = await self._analyze_section_preferences(feedback_history)
            if section_insight:
                insights.append(section_insight)

        # Analyze suggestion type preferences
        type_insight = await self._analyze_suggestion_type_preferences(feedback_history)
        if type_insight:
            insights.append(type_insight)

        # Analyze improvement areas
        improvement_insight = await self._analyze_improvement_areas(feedback_history)
        if improvement_insight:
            insights.append(improvement_insight)

        return insights

    async def _extract_patterns_from_feedback(
        self, feedback: SuggestionFeedback, user_profile: UserProfile
    ) -> List[PreferencePattern]:
        """Extract learning patterns from feedback"""

        patterns = []

        # Pattern 1: Suggestion type preference
        if feedback.action in ["accepted", "modified"]:
            pattern = PreferencePattern(
                pattern_type=f"suggestion_type_{feedback.suggestion_type}",
                confidence=0.7 if feedback.action == "accepted" else 0.5,
                frequency=1,
                last_seen=datetime.utcnow(),
                context={
                    "section": feedback.section,
                    "action": feedback.action,
                    "rating": feedback.rating,
                },
            )
            patterns.append(pattern)

        # Pattern 2: Section-specific preferences
        if feedback.rating and feedback.rating >= 4:
            pattern = PreferencePattern(
                pattern_type=f"section_preference_{feedback.section}",
                confidence=0.6,
                frequency=1,
                last_seen=datetime.utcnow(),
                context={
                    "suggestion_type": feedback.suggestion_type,
                    "rating": feedback.rating,
                },
            )
            patterns.append(pattern)

        # Pattern 3: Decision speed preference
        if feedback.time_to_decision_seconds:
            speed_category = (
                "fast" if feedback.time_to_decision_seconds < 30 else "slow"
            )
            pattern = PreferencePattern(
                pattern_type=f"decision_speed_{speed_category}",
                confidence=0.4,
                frequency=1,
                last_seen=datetime.utcnow(),
                context={
                    "time_seconds": feedback.time_to_decision_seconds,
                    "action": feedback.action,
                },
            )
            patterns.append(pattern)

        return patterns

    async def _update_user_pattern(self, user_id: str, new_pattern: PreferencePattern):
        """Update or create user pattern"""

        existing_pattern = self.user_patterns[user_id].get(new_pattern.pattern_type)

        if existing_pattern:
            # Update existing pattern
            existing_pattern.frequency += 1
            existing_pattern.last_seen = new_pattern.last_seen
            # Weighted average for confidence
            existing_pattern.confidence = (
                existing_pattern.confidence * 0.7 + new_pattern.confidence * 0.3
            )
            existing_pattern.context.update(new_pattern.context)
        else:
            # Create new pattern
            self.user_patterns[user_id][new_pattern.pattern_type] = new_pattern

    async def _calculate_suggestion_score(
        self,
        suggestion: Suggestion,
        user_profile: UserProfile,
        context: ResumeContext,
        user_patterns: Dict[str, PreferencePattern],
    ) -> float:
        """Calculate personalized score for a suggestion"""

        base_score = 1.0

        # Factor 1: Suggestion type preference
        type_pattern_key = f"suggestion_type_{suggestion.type}"
        if type_pattern_key in user_patterns:
            pattern = user_patterns[type_pattern_key]
            type_score = pattern.confidence * (
                pattern.frequency / 10
            )  # Normalize frequency
            base_score *= 1 + type_score * self.learning_weights["acceptance_rate"]

        # Factor 2: Section preference
        section_pattern_key = f"section_preference_{suggestion.section}"
        if section_pattern_key in user_patterns:
            pattern = user_patterns[section_pattern_key]
            section_score = pattern.confidence
            base_score *= (
                1 + section_score * self.learning_weights["context_similarity"]
            )

        # Factor 3: User profile alignment
        if user_profile.preferred_suggestion_types:
            if suggestion.type in user_profile.preferred_suggestion_types:
                base_score *= 1.2

        # Factor 4: Impact score alignment with user preferences
        if user_profile.optimization_focus:
            if (
                "impact" in user_profile.optimization_focus
                and suggestion.impact_score > 0.7
            ):
                base_score *= 1.15
            elif (
                "conservative" in user_profile.optimization_focus
                and suggestion.impact_score < 0.5
            ):
                base_score *= 1.1

        return min(base_score, 2.0)  # Cap the multiplier

    async def _find_similar_feedback(
        self,
        suggestion: Suggestion,
        context: ResumeContext,
        feedback_history: List[SuggestionFeedback],
    ) -> List[SuggestionFeedback]:
        """Find similar feedback from history"""

        similar_feedback = []

        for feedback in feedback_history:
            similarity_score = 0

            # Same suggestion type
            if feedback.suggestion_type == suggestion.type:
                similarity_score += 0.4

            # Same section
            if feedback.section == suggestion.section:
                similarity_score += 0.3

            # Similar impact (within 0.2 range)
            if (
                hasattr(feedback, "impact_score")
                and abs(feedback.impact_score - suggestion.impact_score) < 0.2
            ):
                similarity_score += 0.2

            # Recent feedback (within last 30 days)
            if (datetime.utcnow() - feedback.created_at).days < 30:
                similarity_score += 0.1

            if similarity_score >= 0.5:  # Threshold for similarity
                similar_feedback.append(feedback)

        return similar_feedback

    async def _generate_insights(
        self, user_id: str, feedback: SuggestionFeedback
    ) -> List[LearningInsight]:
        """Generate learning insights from feedback"""

        insights = []
        feedback_history = self.feedback_history[user_id]

        # Insight: Consistent rejection of certain suggestion types
        if len(feedback_history) >= 5:
            recent_feedback = feedback_history[-5:]
            rejected_types = [
                fb.suggestion_type for fb in recent_feedback if fb.action == "rejected"
            ]

            if len(rejected_types) >= 3:
                most_rejected = Counter(rejected_types).most_common(1)[0]
                if most_rejected[1] >= 2:  # Rejected at least twice
                    insight = LearningInsight(
                        user_id=user_id,
                        insight_type="preference",
                        title=f"Consistent rejection of {most_rejected[0]} suggestions",
                        description=f"User tends to reject {most_rejected[0]} type suggestions",
                        confidence=0.7,
                        evidence=[
                            f"Rejected {most_rejected[1]} out of last 5 suggestions"
                        ],
                        data_points=len(recent_feedback),
                        recommended_actions=[
                            f"Reduce frequency of {most_rejected[0]} suggestions",
                            "Focus on alternative suggestion types",
                        ],
                    )
                    insights.append(insight)

        return insights

    async def _update_user_profile(
        self,
        user_profile: UserProfile,
        feedback: SuggestionFeedback,
        patterns: List[PreferencePattern],
    ) -> Optional[UserProfile]:
        """Update user profile based on feedback and patterns"""

        updated = False

        # Update suggestion acceptance rate
        feedback_history = self.feedback_history[user_profile.user_id]
        if len(feedback_history) >= 5:
            recent_feedback = feedback_history[-10:]  # Last 10 feedback items
            accepted = len([fb for fb in recent_feedback if fb.action == "accepted"])
            user_profile.suggestion_acceptance_rate = accepted / len(recent_feedback)
            updated = True

        # Update preferred suggestion types
        if (
            feedback.action in ["accepted", "modified"]
            and feedback.rating
            and feedback.rating >= 4
        ):
            if feedback.suggestion_type not in user_profile.preferred_suggestion_types:
                user_profile.preferred_suggestion_types.append(feedback.suggestion_type)
                updated = True

        # Update most improved sections
        if (
            feedback.action == "accepted"
            and feedback.section not in user_profile.most_improved_sections
        ):
            user_profile.most_improved_sections.append(feedback.section)
            updated = True

        if updated:
            user_profile.last_updated = datetime.utcnow()
            return user_profile

        return None

    async def _calculate_learning_confidence(self, user_id: str) -> float:
        """Calculate confidence in learning for a user"""

        feedback_history = self.feedback_history.get(user_id, [])
        user_patterns = self.user_patterns.get(user_id, {})

        if not feedback_history:
            return 0.0

        # Base confidence on amount of data
        data_confidence = min(
            len(feedback_history) / 20, 1.0
        )  # Max confidence at 20+ feedback items

        # Pattern consistency confidence
        pattern_confidence = 0.0
        if user_patterns:
            avg_pattern_confidence = sum(
                p.confidence for p in user_patterns.values()
            ) / len(user_patterns)
            pattern_confidence = avg_pattern_confidence

        # Recency confidence (more recent feedback = higher confidence)
        if feedback_history:
            recent_feedback = [
                fb
                for fb in feedback_history
                if (datetime.utcnow() - fb.created_at).days < 7
            ]
            recency_confidence = min(len(recent_feedback) / 5, 1.0)
        else:
            recency_confidence = 0.0

        # Weighted average
        overall_confidence = (
            data_confidence * 0.4 + pattern_confidence * 0.4 + recency_confidence * 0.2
        )

        return overall_confidence

    async def _get_personalization_settings(
        self, user_id: str
    ) -> Optional[PersonalizationSettings]:
        """Get personalization settings for user (placeholder - would integrate with database)"""
        # This would typically fetch from database
        # For now, return default settings
        return PersonalizationSettings(
            user_id=user_id,
            suggestion_aggressiveness="moderate",
            auto_apply_high_confidence=False,
            show_reasoning=True,
        )

    # Analysis methods for insights
    async def _analyze_acceptance_patterns(
        self, feedback_history: List[SuggestionFeedback]
    ) -> Optional[LearningInsight]:
        """Analyze user's acceptance patterns"""

        if len(feedback_history) < 5:
            return None

        acceptance_rate = len(
            [fb for fb in feedback_history if fb.action == "accepted"]
        ) / len(feedback_history)

        if acceptance_rate > 0.8:
            return LearningInsight(
                user_id=feedback_history[0].user_id,
                insight_type="strength",
                title="High suggestion acceptance rate",
                description=f"User accepts {acceptance_rate:.1%} of suggestions",
                confidence=0.8,
                evidence=[
                    f"Accepted {int(acceptance_rate * len(feedback_history))} out of {len(feedback_history)} suggestions"
                ],
                data_points=len(feedback_history),
                recommended_actions=["Continue providing similar suggestion types"],
            )
        elif acceptance_rate < 0.3:
            return LearningInsight(
                user_id=feedback_history[0].user_id,
                insight_type="improvement_area",
                title="Low suggestion acceptance rate",
                description=f"User accepts only {acceptance_rate:.1%} of suggestions",
                confidence=0.7,
                evidence=[
                    f"Accepted only {int(acceptance_rate * len(feedback_history))} out of {len(feedback_history)} suggestions"
                ],
                data_points=len(feedback_history),
                recommended_actions=[
                    "Analyze rejection reasons",
                    "Adjust suggestion types",
                    "Provide more conservative suggestions",
                ],
            )

        return None

    async def _analyze_section_preferences(
        self, feedback_history: List[SuggestionFeedback]
    ) -> Optional[LearningInsight]:
        """Analyze user's section preferences"""

        section_feedback = defaultdict(list)
        for fb in feedback_history:
            section_feedback[fb.section].append(fb)

        # Find section with highest acceptance rate
        best_section = None
        best_rate = 0

        for section, feedback_list in section_feedback.items():
            if len(feedback_list) >= 3:  # Need at least 3 feedback items
                acceptance_rate = len(
                    [fb for fb in feedback_list if fb.action == "accepted"]
                ) / len(feedback_list)
                if acceptance_rate > best_rate:
                    best_rate = acceptance_rate
                    best_section = section

        if best_section and best_rate > 0.7:
            return LearningInsight(
                user_id=feedback_history[0].user_id,
                insight_type="preference",
                title=f"Strong preference for {best_section} improvements",
                description=f"User accepts {best_rate:.1%} of {best_section} suggestions",
                confidence=0.8,
                evidence=[f"High acceptance rate in {best_section} section"],
                data_points=len(section_feedback[best_section]),
                recommended_actions=[f"Prioritize {best_section} suggestions"],
            )

        return None

    async def _analyze_suggestion_type_preferences(
        self, feedback_history: List[SuggestionFeedback]
    ) -> Optional[LearningInsight]:
        """Analyze user's suggestion type preferences"""

        type_feedback = defaultdict(list)
        for fb in feedback_history:
            type_feedback[fb.suggestion_type].append(fb)

        # Find most preferred suggestion type
        best_type = None
        best_rate = 0

        for sugg_type, feedback_list in type_feedback.items():
            if len(feedback_list) >= 2:
                acceptance_rate = len(
                    [
                        fb
                        for fb in feedback_list
                        if fb.action in ["accepted", "modified"]
                    ]
                ) / len(feedback_list)
                if acceptance_rate > best_rate:
                    best_rate = acceptance_rate
                    best_type = sugg_type

        if best_type and best_rate > 0.6:
            return LearningInsight(
                user_id=feedback_history[0].user_id,
                insight_type="preference",
                title=f"Preference for {best_type} suggestions",
                description=f"User responds positively to {best_rate:.1%} of {best_type} suggestions",
                confidence=0.7,
                evidence=[f"High acceptance rate for {best_type} suggestions"],
                data_points=len(type_feedback[best_type]),
                recommended_actions=[f"Increase frequency of {best_type} suggestions"],
            )

        return None

    async def _analyze_improvement_areas(
        self, feedback_history: List[SuggestionFeedback]
    ) -> Optional[LearningInsight]:
        """Analyze areas where user needs improvement"""

        if len(feedback_history) < 10:
            return None

        # Look for patterns in rejected suggestions
        rejected_feedback = [fb for fb in feedback_history if fb.action == "rejected"]

        if len(rejected_feedback) >= 5:
            rejection_reasons = [
                fb.feedback_text for fb in rejected_feedback if fb.feedback_text
            ]

            if rejection_reasons:
                # Simple keyword analysis
                common_words = []
                for reason in rejection_reasons:
                    words = reason.lower().split()
                    common_words.extend(words)

                word_counts = Counter(common_words)
                most_common = word_counts.most_common(3)

                if most_common and most_common[0][1] >= 2:
                    return LearningInsight(
                        user_id=feedback_history[0].user_id,
                        insight_type="improvement_area",
                        title="Common rejection patterns identified",
                        description=f"User frequently mentions '{most_common[0][0]}' in rejection feedback",
                        confidence=0.6,
                        evidence=[
                            f"Word '{most_common[0][0]}' appears {most_common[0][1]} times in rejection feedback"
                        ],
                        data_points=len(rejection_reasons),
                        recommended_actions=[
                            "Adjust suggestions to address common concerns",
                            "Provide more context for suggestions",
                        ],
                    )

        return None


# Global instance
preference_learning_service = PreferenceLearningService()
