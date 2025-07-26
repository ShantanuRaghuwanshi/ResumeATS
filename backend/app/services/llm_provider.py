from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
import google.generativeai as genai
import openai
import anthropic
from app.services.ollama_utils import (
    ollama_extract_personal_details,
    ollama_extract_sections,
)
from ollama import chat, AsyncClient
from app.models.resume import PersonalDetails, ResumeSections
from app.models.conversation import ResumeContext, AIResponse, Suggestion, Message
from app.models.user_preferences import UserProfile, SuggestionFeedback

import json
import asyncio
from datetime import datetime
from abc import ABC, abstractmethod
from app.configs.config import get_logger

# Setup logger
logger = get_logger(__name__)


class LLMProviderBase(ABC):
    """Enhanced base class for LLM providers with conversation and context management"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conversation_history: Dict[str, List[Message]] = {}
        self.context_cache: Dict[str, ResumeContext] = {}
        self.optimization_strategies: Dict[str, Dict[str, Any]] = {}
        self._setup_optimization_strategies()

    # Original methods (kept for backward compatibility)
    @abstractmethod
    async def extract_personal_details(self, text: str) -> PersonalDetails:
        raise NotImplementedError

    @abstractmethod
    async def extract_sections(self, text: str) -> ResumeSections:
        raise NotImplementedError

    # Simple test method for configuration validation
    @abstractmethod
    async def generate_simple_response(self, prompt: str) -> str:
        """Generate a simple response for testing configuration"""
        raise NotImplementedError

    # New conversation and context management methods
    @abstractmethod
    async def generate_conversation_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AIResponse:
        """Generate a conversational response with context awareness"""
        raise NotImplementedError

    @abstractmethod
    async def generate_streaming_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time chat"""
        raise NotImplementedError

    @abstractmethod
    async def generate_section_suggestions(
        self,
        section: str,
        content: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Generate suggestions for a specific resume section"""
        raise NotImplementedError

    @abstractmethod
    async def optimize_content_for_job(
        self,
        content: str,
        job_description: str,
        section: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Optimize content for a specific job description"""
        raise NotImplementedError

    @abstractmethod
    async def optimize_resume(
        self,
        resume_data: Dict[str, Any],
        job_description: str,
        optimization_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize entire resume for a specific job description"""
        raise NotImplementedError

    # Context management methods
    def store_conversation_context(self, session_id: str, context: ResumeContext):
        """Store conversation context for session"""
        self.context_cache[session_id] = context

    def get_conversation_context(self, session_id: str) -> Optional[ResumeContext]:
        """Retrieve conversation context for session"""
        return self.context_cache.get(session_id)

    def update_conversation_history(self, session_id: str, message: Message):
        """Update conversation history for session"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        self.conversation_history[session_id].append(message)

    def get_conversation_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """Get conversation history for session"""
        history = self.conversation_history.get(session_id, [])
        if limit:
            return history[-limit:]
        return history

    # Provider-specific optimization strategies
    def _setup_optimization_strategies(self):
        """Setup provider-specific optimization strategies"""
        self.optimization_strategies = {
            "ats_optimization": {
                "focus": "keyword_density",
                "formatting": "simple",
                "sections_priority": ["experience", "skills", "education"],
            },
            "readability": {
                "focus": "clarity",
                "sentence_length": "medium",
                "bullet_points": True,
            },
            "impact_focused": {
                "focus": "achievements",
                "quantification": True,
                "action_verbs": True,
            },
            "industry_specific": {
                "focus": "domain_expertise",
                "technical_terms": True,
                "industry_keywords": True,
            },
        }

    def get_optimization_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """Get optimization strategy configuration"""
        return self.optimization_strategies.get(strategy_name, {})

    def customize_strategy_for_user(
        self, strategy_name: str, user_profile: UserProfile
    ) -> Dict[str, Any]:
        """Customize optimization strategy based on user profile"""
        base_strategy = self.get_optimization_strategy(strategy_name)

        # Customize based on user preferences
        if user_profile.writing_style:
            base_strategy["writing_style"] = user_profile.writing_style

        if user_profile.industry:
            base_strategy["industry_focus"] = user_profile.industry

        if user_profile.experience_level:
            base_strategy["experience_level"] = user_profile.experience_level

        return base_strategy

    # Feedback integration methods
    async def process_user_feedback(
        self, feedback: SuggestionFeedback, user_profile: UserProfile
    ) -> Dict[str, Any]:
        """Process user feedback to improve future suggestions"""
        from services.preference_learning import preference_learning_service

        # Use the preference learning service for advanced feedback processing
        learning_results = await preference_learning_service.process_feedback(
            feedback, user_profile
        )

        # Legacy feedback insights for backward compatibility
        feedback_insights = {
            "suggestion_type_preference": {},
            "content_style_preference": {},
            "rejection_patterns": [],
        }

        # Analyze feedback patterns
        if feedback.action == "accepted":
            feedback_insights["suggestion_type_preference"][
                feedback.suggestion_type
            ] = (
                feedback_insights["suggestion_type_preference"].get(
                    feedback.suggestion_type, 0
                )
                + 1
            )
        elif feedback.action == "rejected" and feedback.feedback_text:
            feedback_insights["rejection_patterns"].append(
                {
                    "reason": feedback.feedback_text,
                    "suggestion_type": feedback.suggestion_type,
                    "section": feedback.section,
                }
            )

        # Combine with learning results
        feedback_insights.update(learning_results)
        return feedback_insights

    async def personalize_suggestions_with_learning(
        self,
        suggestions: List[Suggestion],
        user_profile: UserProfile,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Personalize suggestions using machine learning insights"""
        from services.preference_learning import preference_learning_service

        return await preference_learning_service.personalize_suggestions(
            suggestions, user_profile, context
        )

    async def predict_user_response(
        self, suggestion: Suggestion, user_profile: UserProfile, context: ResumeContext
    ) -> Dict[str, float]:
        """Predict how user will likely respond to a suggestion"""
        from services.preference_learning import preference_learning_service

        return await preference_learning_service.predict_user_preference(
            suggestion, user_profile, context
        )

    # Utility methods for all providers
    def _build_system_prompt(
        self,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
        strategy: Optional[str] = None,
    ) -> str:
        """Build system prompt with context and user preferences"""
        base_prompt = f"""You are an expert resume optimization assistant helping with the {context.current_section} section.

Resume Context:
- User ID: {context.user_id}
- Current Section: {context.current_section}
- Optimization Goals: {', '.join(context.optimization_goals)}
"""

        if context.job_description:
            base_prompt += (
                f"\nJob Description Context:\n{context.job_description[:500]}..."
            )

        if user_profile:
            base_prompt += f"""
User Profile:
- Industry: {user_profile.industry or 'Not specified'}
- Experience Level: {user_profile.experience_level or 'Not specified'}
- Writing Style: {user_profile.writing_style or 'Not specified'}
- Preferred Focus: {', '.join(user_profile.optimization_focus)}
"""

        if strategy:
            strategy_config = self.get_optimization_strategy(strategy)
            if user_profile:
                strategy_config = self.customize_strategy_for_user(
                    strategy, user_profile
                )
            base_prompt += (
                f"\nOptimization Strategy: {json.dumps(strategy_config, indent=2)}"
            )

        base_prompt += """

Guidelines:
1. Provide specific, actionable suggestions
2. Explain the reasoning behind each suggestion
3. Consider ATS compatibility
4. Maintain professional tone
5. Focus on quantifiable achievements
6. Ensure consistency with other resume sections
"""

        return base_prompt

    def _format_conversation_history(
        self, history: List[Message], limit: int = 10
    ) -> str:
        """Format conversation history for context"""
        recent_history = history[-limit:] if len(history) > limit else history
        formatted = []

        for msg in recent_history:
            role = "Human" if msg.role == "user" else "Assistant"
            formatted.append(f"{role}: {msg.content}")

        return "\n".join(formatted)


# Ollama implementation
class OllamaProvider(LLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model", "gemma3n:e4b")
        self.ollama_client = AsyncClient(
            host=config.get("url", "http://localhost:11434")
        )
        self.ollama_extract_personal_details = ollama_extract_personal_details
        self.ollama_extract_sections = ollama_extract_sections

    async def extract_personal_details(self, text: str) -> PersonalDetails:
        return await self.ollama_extract_personal_details(
            text, self.ollama_client, self.model
        )

    async def extract_sections(self, text: str) -> ResumeSections:
        return await self.ollama_extract_sections(text, self.ollama_client, self.model)

    async def generate_simple_response(self, prompt: str) -> str:
        """Generate a simple response for testing configuration"""
        try:
            response = await self.ollama_client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 100, "temperature": 0.3},
            )
            return (
                response["message"]["content"] or "Test response received successfully"
            )
        except Exception as e:
            raise Exception(f"Ollama API test failed: {str(e)}")

    async def generate_conversation_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AIResponse:
        """Generate conversational response using Ollama"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        full_prompt = f"{system_prompt}\n\nConversation History:\n{history_context}\n\nCurrent Message: {message}\n\nResponse:"

        response = await self.ollama_client.chat(
            model=self.model, messages=[{"role": "user", "content": full_prompt}]
        )

        response_text = response["message"]["content"]

        # Generate suggestions if the response indicates improvements
        suggestions = await self._extract_suggestions_from_response(
            response_text, context.current_section, context
        )

        return AIResponse(
            message=response_text,
            suggestions=suggestions,
            confidence=0.7,
            follow_up_questions=self._generate_follow_up_questions(message, context),
        )

    async def generate_streaming_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time chat"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        full_prompt = f"{system_prompt}\n\nConversation History:\n{history_context}\n\nCurrent Message: {message}\n\nResponse:"

        # Ollama streaming implementation
        async for chunk in self.ollama_client.chat(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            stream=True,
        ):
            if chunk.get("message", {}).get("content"):
                yield chunk["message"]["content"]

    async def generate_section_suggestions(
        self,
        section: str,
        content: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Generate suggestions for a specific resume section"""
        prompt = f"""Analyze the {section} section and provide specific improvement suggestions.

Current {section} content:
{content}

Provide 3-5 specific suggestions for improvement. For each suggestion, include:
1. Type (content, structure, keyword, formatting)
2. Brief title
3. Detailed description
4. Impact score (0.0-1.0)
5. Reasoning

Format as a clear list."""

        response = await self.ollama_client.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )

        response_text = response["message"]["content"]
        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def optimize_content_for_job(
        self,
        content: str,
        job_description: str,
        section: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Optimize content for a specific job description"""
        prompt = f"""Optimize the {section} section to better match this job description.

Job Description:
{job_description[:1000]}...

Current {section} content:
{content}

Provide specific optimization suggestions that will improve the match between the resume section and job requirements.
Focus on relevant keywords, skills, and experiences that align with the job posting."""

        response = await self.ollama_client.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )

        response_text = response["message"]["content"]
        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def _extract_suggestions_from_response(
        self, response_text: str, section: str, context: ResumeContext
    ) -> List[Suggestion]:
        """Extract suggestions from AI response text"""
        suggestions = []

        # Simple parsing - in production, this would be more sophisticated
        if "suggest" in response_text.lower() or "improve" in response_text.lower():
            suggestion = Suggestion(
                type="content",
                title="AI Recommendation",
                description=(
                    response_text[:200] + "..."
                    if len(response_text) > 200
                    else response_text
                ),
                impact_score=0.6,
                reasoning="Based on AI analysis of content and context",
                section=section,
                confidence=0.6,
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_follow_up_questions(
        self, message: str, context: ResumeContext
    ) -> List[str]:
        """Generate follow-up questions based on the conversation"""
        questions = []

        if "experience" in message.lower():
            questions.append(
                "Would you like me to help quantify your achievements with specific metrics?"
            )
        if "skills" in message.lower():
            questions.append(
                "Should we prioritize technical skills or soft skills for this role?"
            )
        if "job" in message.lower():
            questions.append(
                "Do you have a specific job posting you'd like to optimize for?"
            )

        return questions[:2]  # Limit to 2 questions

    async def optimize_resume(
        self,
        resume_data: Dict[str, Any],
        job_description: str,
        optimization_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize entire resume for a specific job description using Ollama"""
        optimized_resume = resume_data.copy()

        # Extract key information from job description
        jd_analysis_prompt = f"""Analyze this job description and extract:
1. Required skills (technical and soft skills)
2. Key responsibilities and qualifications
3. Important keywords and phrases
4. Company culture indicators
5. Experience level requirements

Job Description:
{job_description}

Provide a structured analysis."""

        try:
            # Analyze job description
            jd_response = await self.ollama_client.chat(
                model=self.model,
                messages=[{"role": "user", "content": jd_analysis_prompt}],
            )

            jd_analysis = jd_response["message"]["content"]

            # Generate optimization suggestions for each section
            sections_to_optimize = ["skills", "experience", "summary", "education"]
            suggestions_by_section = {}

            for section in sections_to_optimize:
                section_content = resume_data.get(section, "")
                if not section_content:
                    continue

                optimization_prompt = f"""Based on this job description analysis:
{jd_analysis[:500]}...

Optimize this {section} section to better match the job requirements:

Current {section}:
{section_content}

Provide specific suggestions for:
1. New skills to add that are mentioned in the job description
2. How to reframe existing content to better align with job requirements
3. Keywords to incorporate naturally
4. Achievements to highlight or quantify
5. Content that should be emphasized or de-emphasized

Focus on making the candidate appear as a strong match while maintaining truthfulness."""

                try:
                    optimization_response = await self.ollama_client.chat(
                        model=self.model,
                        messages=[{"role": "user", "content": optimization_prompt}],
                    )

                    suggestions_by_section[section] = optimization_response["message"][
                        "content"
                    ]

                except Exception as e:
                    logger.error(f"Error optimizing {section}: {e}")
                    suggestions_by_section[section] = (
                        f"Error generating suggestions for {section}"
                    )

            # Generate improved content for key sections
            if "skills" in resume_data:
                skills_improvement_prompt = f"""Based on the job analysis and current skills, suggest an improved skills section:

Current Skills: {resume_data.get('skills', '')}

Job Requirements Analysis: {jd_analysis[:300]}...

Provide an enhanced skills section that:
1. Includes relevant skills from the job description that the candidate likely has
2. Prioritizes the most important skills for this role
3. Uses similar terminology as the job posting
4. Maintains credibility and truthfulness

Return only the improved skills section content."""

                try:
                    skills_response = await self.ollama_client.chat(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": skills_improvement_prompt}
                        ],
                    )
                    optimized_resume["skills"] = skills_response["message"]["content"]
                except Exception as e:
                    logger.error(f"Error improving skills section: {e}")

            # Generate improved summary/objective
            if "summary" in resume_data or "objective" in resume_data:
                summary_content = resume_data.get("summary") or resume_data.get(
                    "objective", ""
                )
                summary_prompt = f"""Rewrite this professional summary to better align with the job requirements:

Current Summary: {summary_content}

Job Analysis: {jd_analysis[:300]}...

Create a compelling summary that:
1. Highlights relevant experience for this specific role
2. Uses keywords from the job description naturally
3. Emphasizes achievements that matter for this position
4. Shows clear value proposition for the employer

Return only the improved summary."""

                try:
                    summary_response = await self.ollama_client.chat(
                        model=self.model,
                        messages=[{"role": "user", "content": summary_prompt}],
                    )

                    if "summary" in resume_data:
                        optimized_resume["summary"] = summary_response["message"][
                            "content"
                        ]
                    else:
                        optimized_resume["objective"] = summary_response["message"][
                            "content"
                        ]
                except Exception as e:
                    logger.error(f"Error improving summary: {e}")

            # Add optimization metadata
            optimized_resume["optimization_metadata"] = {
                "job_description_analyzed": True,
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "sections_optimized": list(suggestions_by_section.keys()),
                "suggestions_by_section": suggestions_by_section,
                "optimization_goals": optimization_goals
                or ["ats_optimization", "keyword_matching"],
                "model_used": self.model,
            }

            return optimized_resume

        except Exception as e:
            logger.error(f"Error in resume optimization: {e}")
            # Return original resume with error info if optimization fails
            optimized_resume["optimization_metadata"] = {
                "optimization_error": str(e),
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "fallback_applied": True,
            }
            return optimized_resume


# Stubs for other providers
class OpenAIProvider(LLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.openai = openai
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.openai.api_key = self.api_key
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
        )

    async def extract_personal_details(self, text: str) -> Dict:
        """
        Extract personal details using OpenAI API.
        """
        # OpenAI's async API is not available in the latest SDK, so use run_in_executor

        loop = asyncio.get_event_loop()

        response = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ],
            response_format=PersonalDetails,
            temperature=0.2,
        )
        # Assuming the response has choices and message content
        result = response.choices[0].message.parsed
        if result is None:
            raise ValueError("Failed to extract personal details: result is None")
        return result.model_dump()

    async def extract_sections(self, text: str) -> Dict:
        """
        Extract resume sections using OpenAI API.
        """

        loop = asyncio.get_event_loop()

        response = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract resume sections from the text.",
                },
                {"role": "user", "content": text},
            ],
            response_format=ResumeSections,
            temperature=0.2,
        )
        result = response.choices[0].message.parsed
        if result is None:
            raise ValueError("Failed to extract resume sections: result is None")
        return result.model_dump()

    async def generate_simple_response(self, prompt: str) -> str:
        """Generate a simple response for testing configuration"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,
            )
            return (
                response.choices[0].message.content
                or "Test response received successfully"
            )
        except Exception as e:
            raise Exception(f"OpenAI API test failed: {str(e)}")

    async def generate_conversation_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AIResponse:
        """Generate conversational response using OpenAI"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Conversation History:\n{history_context}\n\nCurrent Message: {message}",
            },
        ]

        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.7, max_tokens=1000
        )

        response_text = response.choices[0].message.content

        # Generate suggestions if the response indicates improvements
        suggestions = await self._extract_suggestions_from_response(
            response_text, context.current_section, context
        )

        return AIResponse(
            message=response_text,
            suggestions=suggestions,
            confidence=0.8,
            follow_up_questions=self._generate_follow_up_questions(message, context),
        )

    async def generate_streaming_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time chat"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Conversation History:\n{history_context}\n\nCurrent Message: {message}",
            },
        ]

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_section_suggestions(
        self,
        section: str,
        content: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Generate suggestions for a specific resume section"""
        system_prompt = f"""You are an expert resume optimizer. Analyze the {section} section and provide specific improvement suggestions.

Current {section} content:
{content}

Provide suggestions in JSON format with the following structure:
{{
    "suggestions": [
        {{
            "type": "content|structure|keyword|formatting",
            "title": "Brief title",
            "description": "Detailed description",
            "original_text": "text to replace (if applicable)",
            "suggested_text": "replacement text (if applicable)",
            "impact_score": 0.0-1.0,
            "reasoning": "explanation",
            "confidence": 0.0-1.0
        }}
    ]
}}
"""

        if user_profile:
            system_prompt += f"\nUser Profile: {user_profile.model_dump_json()}"

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Analyze and suggest improvements for this {section} section.",
                },
            ],
            temperature=0.3,
        )

        try:
            suggestions_data = json.loads(response.choices[0].message.content)
            suggestions = []

            for sugg_data in suggestions_data.get("suggestions", []):
                suggestion = Suggestion(
                    type=sugg_data["type"],
                    title=sugg_data["title"],
                    description=sugg_data["description"],
                    original_text=sugg_data.get("original_text"),
                    suggested_text=sugg_data.get("suggested_text"),
                    impact_score=sugg_data["impact_score"],
                    reasoning=sugg_data["reasoning"],
                    section=section,
                    confidence=sugg_data["confidence"],
                )
                suggestions.append(suggestion)

            # Personalize suggestions using machine learning
            if user_profile:
                suggestions = await self.personalize_suggestions_with_learning(
                    suggestions, user_profile, context
                )

            return suggestions
        except json.JSONDecodeError:
            # Fallback: create a general suggestion
            fallback_suggestion = [
                Suggestion(
                    type="content",
                    title="General Improvement",
                    description=response.choices[0].message.content,
                    impact_score=0.5,
                    reasoning="AI-generated improvement suggestion",
                    section=section,
                    confidence=0.6,
                )
            ]

            # Still apply personalization to fallback
            if user_profile:
                fallback_suggestion = await self.personalize_suggestions_with_learning(
                    fallback_suggestion, user_profile, context
                )

            return fallback_suggestion

    async def optimize_content_for_job(
        self,
        content: str,
        job_description: str,
        section: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Optimize content for a specific job description"""
        system_prompt = f"""You are an expert resume optimizer. Optimize the {section} section to better match the job description.

Job Description:
{job_description[:1000]}...

Current {section} content:
{content}

Provide optimization suggestions that will improve the match between the resume section and job requirements.
Focus on relevant keywords, skills, and experiences that align with the job posting.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Provide specific optimization suggestions for better job matching.",
                },
            ],
            temperature=0.3,
        )

        # Parse response and create suggestions
        return await self._extract_suggestions_from_response(
            response.choices[0].message.content, section, context
        )

    async def _extract_suggestions_from_response(
        self, response_text: str, section: str, context: ResumeContext
    ) -> List[Suggestion]:
        """Extract suggestions from AI response text"""
        # Simple implementation - in production, this would be more sophisticated
        suggestions = []

        if "suggest" in response_text.lower() or "improve" in response_text.lower():
            suggestion = Suggestion(
                type="content",
                title="AI Recommendation",
                description=(
                    response_text[:200] + "..."
                    if len(response_text) > 200
                    else response_text
                ),
                impact_score=0.7,
                reasoning="Based on AI analysis of content and context",
                section=section,
                confidence=0.7,
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_follow_up_questions(
        self, message: str, context: ResumeContext
    ) -> List[str]:
        """Generate follow-up questions based on the conversation"""
        questions = []

        if "experience" in message.lower():
            questions.append(
                "Would you like me to help quantify your achievements with specific metrics?"
            )
        if "skills" in message.lower():
            questions.append(
                "Should we prioritize technical skills or soft skills for this role?"
            )
        if "job" in message.lower():
            questions.append(
                "Do you have a specific job posting you'd like to optimize for?"
            )

        return questions[:2]  # Limit to 2 questions

    async def optimize_resume(
        self,
        resume_data: Dict[str, Any],
        job_description: str,
        optimization_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize entire resume for a specific job description using OpenAI"""
        optimized_resume = resume_data.copy()

        try:
            # Analyze job description first
            jd_analysis_response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume optimization assistant. Analyze job descriptions and provide structured insights.",
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this job description and extract:
1. Required technical skills
2. Required soft skills  
3. Key responsibilities
4. Important keywords
5. Experience level needed
6. Company culture indicators

Job Description:
{job_description}

Provide a structured analysis.""",
                    },
                ],
                temperature=0.3,
            )

            jd_analysis = jd_analysis_response.choices[0].message.content

            # Optimize skills section
            if "skills" in resume_data and resume_data["skills"]:
                skills_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a resume optimization expert. Enhance skills sections to match job requirements while maintaining truthfulness.",
                        },
                        {
                            "role": "user",
                            "content": f"""Job Analysis: {jd_analysis[:500]}...

Current Skills: {resume_data['skills']}

Enhance this skills section by:
1. Adding relevant skills from the job description that the candidate likely has
2. Reordering to prioritize job-relevant skills
3. Using similar terminology as the job posting
4. Maintaining credibility

Return only the improved skills section.""",
                        },
                    ],
                    temperature=0.3,
                )
                optimized_resume["skills"] = skills_response.choices[0].message.content

            # Optimize summary/objective
            summary_field = "summary" if "summary" in resume_data else "objective"
            if summary_field in resume_data and resume_data[summary_field]:
                summary_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a resume writing expert. Rewrite professional summaries to align with specific job requirements.",
                        },
                        {
                            "role": "user",
                            "content": f"""Job Analysis: {jd_analysis[:500]}...

Current {summary_field}: {resume_data[summary_field]}

Rewrite this {summary_field} to:
1. Highlight relevant experience for this specific role
2. Use keywords from the job description naturally
3. Show clear value proposition
4. Emphasize achievements that matter for this position

Return only the improved {summary_field}.""",
                        },
                    ],
                    temperature=0.3,
                )
                optimized_resume[summary_field] = summary_response.choices[
                    0
                ].message.content

            # Generate suggestions for experience section
            experience_suggestions = ""
            if "experience" in resume_data and resume_data["experience"]:
                exp_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a career advisor. Provide specific suggestions for improving work experience descriptions.",
                        },
                        {
                            "role": "user",
                            "content": f"""Job Analysis: {jd_analysis[:500]}...

Current Experience: {resume_data['experience'][:1000]}...

Provide specific suggestions for improving this experience section:
1. How to reframe achievements to match job requirements
2. Metrics and quantifications to add
3. Keywords to incorporate
4. Skills to emphasize
5. Projects or responsibilities to highlight

Return actionable suggestions.""",
                        },
                    ],
                    temperature=0.3,
                )
                experience_suggestions = exp_response.choices[0].message.content

            # Add optimization metadata
            optimized_resume["optimization_metadata"] = {
                "job_description_analyzed": True,
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "sections_optimized": ["skills", summary_field]
                + (["experience_suggestions"] if experience_suggestions else []),
                "experience_improvement_suggestions": experience_suggestions,
                "job_analysis": jd_analysis,
                "optimization_goals": optimization_goals
                or ["ats_optimization", "keyword_matching"],
                "model_used": self.model,
            }

            return optimized_resume

        except Exception as e:
            logger.error(f"Error in OpenAI resume optimization: {e}")
            optimized_resume["optimization_metadata"] = {
                "optimization_error": str(e),
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "fallback_applied": True,
            }
            return optimized_resume


class ClaudeProvider(LLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.anthropic = anthropic
        self.api_key = config.get("api_key")
        self.model = config.get("model", "claude-3-opus-20240229")
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def extract_personal_details(self, text: str) -> Dict:
        """
        Extract personal details using Claude API.
        """

        loop = asyncio.get_event_loop()

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="Extract personal details from the resume text.",
            messages=[{"role": "user", "content": text}],
        )

        return response.content[0].to_dict()

    async def extract_sections(self, text: str) -> Dict:
        """
        Extract resume sections using Claude API.
        """
        loop = asyncio.get_event_loop()

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="Extract resume sections from the text.",
            messages=[{"role": "user", "content": text}],
        )
        return response.content[0].to_dict()

    async def generate_simple_response(self, prompt: str) -> str:
        """Generate a simple response for testing configuration"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text or "Test response received successfully"
        except Exception as e:
            raise Exception(f"Claude API test failed: {str(e)}")

    async def generate_conversation_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AIResponse:
        """Generate conversational response using Claude"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        user_message = (
            f"Conversation History:\n{history_context}\n\nCurrent Message: {message}"
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        # Generate suggestions if the response indicates improvements
        suggestions = await self._extract_suggestions_from_response(
            response_text, context.current_section, context
        )

        return AIResponse(
            message=response_text,
            suggestions=suggestions,
            confidence=0.8,
            follow_up_questions=self._generate_follow_up_questions(message, context),
        )

    async def generate_streaming_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time chat"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        user_message = (
            f"Conversation History:\n{history_context}\n\nCurrent Message: {message}"
        )

        # Claude streaming implementation
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_section_suggestions(
        self,
        section: str,
        content: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Generate suggestions for a specific resume section"""
        system_prompt = f"""You are an expert resume optimizer. Analyze the {section} section and provide specific improvement suggestions.

Current {section} content:
{content}

Provide 3-5 specific suggestions for improvement. For each suggestion, include:
1. Type (content, structure, keyword, formatting)
2. Brief title
3. Detailed description
4. Impact score (0.0-1.0)
5. Reasoning

Format as a clear list."""

        if user_profile:
            system_prompt += f"\nUser Profile: {user_profile.model_dump_json()}"

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze and suggest improvements for this {section} section.",
                }
            ],
        )

        response_text = response.content[0].text
        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def optimize_content_for_job(
        self,
        content: str,
        job_description: str,
        section: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Optimize content for a specific job description"""
        system_prompt = f"""You are an expert resume optimizer. Optimize the {section} section to better match the job description.

Job Description:
{job_description[:1000]}...

Current {section} content:
{content}

Provide optimization suggestions that will improve the match between the resume section and job requirements.
Focus on relevant keywords, skills, and experiences that align with the job posting."""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": "Provide specific optimization suggestions for better job matching.",
                }
            ],
        )

        response_text = response.content[0].text
        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def _extract_suggestions_from_response(
        self, response_text: str, section: str, context: ResumeContext
    ) -> List[Suggestion]:
        """Extract suggestions from AI response text"""
        suggestions = []

        if "suggest" in response_text.lower() or "improve" in response_text.lower():
            suggestion = Suggestion(
                type="content",
                title="AI Recommendation",
                description=(
                    response_text[:200] + "..."
                    if len(response_text) > 200
                    else response_text
                ),
                impact_score=0.7,
                reasoning="Based on AI analysis of content and context",
                section=section,
                confidence=0.7,
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_follow_up_questions(
        self, message: str, context: ResumeContext
    ) -> List[str]:
        """Generate follow-up questions based on the conversation"""
        questions = []

        if "experience" in message.lower():
            questions.append(
                "Would you like me to help quantify your achievements with specific metrics?"
            )
        if "skills" in message.lower():
            questions.append(
                "Should we prioritize technical skills or soft skills for this role?"
            )
        if "job" in message.lower():
            questions.append(
                "Do you have a specific job posting you'd like to optimize for?"
            )

        return questions[:2]  # Limit to 2 questions

    async def optimize_resume(
        self,
        resume_data: Dict[str, Any],
        job_description: str,
        optimization_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize entire resume for a specific job description using Claude"""
        optimized_resume = resume_data.copy()

        try:
            # Analyze job description
            jd_analysis_response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system="You are an expert resume optimization assistant specializing in job description analysis.",
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze this job description and extract key information:

Job Description:
{job_description}

Please provide:
1. Required technical skills
2. Required soft skills
3. Key responsibilities and qualifications
4. Important keywords and industry terms
5. Experience level requirements
6. Company culture indicators

Structure your analysis clearly.""",
                    }
                ],
            )

            jd_analysis = jd_analysis_response.content[0].text

            # Optimize skills section
            if "skills" in resume_data and resume_data["skills"]:
                skills_response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    system="You are a resume writing expert. Optimize skills sections to match job requirements while maintaining truthfulness.",
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Based on this job analysis:
{jd_analysis[:500]}...

Current Skills Section:
{resume_data['skills']}

Please provide an optimized skills section that:
1. Includes relevant skills from the job description
2. Prioritizes the most important skills for this role
3. Uses terminology consistent with the job posting
4. Maintains credibility and truthfulness

Return only the improved skills section content.""",
                        }
                    ],
                )
                optimized_resume["skills"] = skills_response.content[0].text

            # Optimize summary/objective
            summary_field = "summary" if "summary" in resume_data else "objective"
            if summary_field in resume_data and resume_data[summary_field]:
                summary_response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    system="You are a professional resume writer. Craft compelling summaries that align with job requirements.",
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Job Analysis:
{jd_analysis[:400]}...

Current {summary_field}:
{resume_data[summary_field]}

Rewrite this {summary_field} to better align with the job requirements:
1. Highlight relevant experience and achievements
2. Incorporate important keywords naturally
3. Show clear value proposition for this specific role
4. Maintain professional tone and accuracy

Return only the improved {summary_field}.""",
                        }
                    ],
                )
                optimized_resume[summary_field] = summary_response.content[0].text

            # Add optimization metadata
            optimized_resume["optimization_metadata"] = {
                "job_description_analyzed": True,
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "sections_optimized": ["skills", summary_field],
                "job_analysis": jd_analysis,
                "optimization_goals": optimization_goals
                or ["ats_optimization", "keyword_matching"],
                "model_used": self.model,
            }

            return optimized_resume

        except Exception as e:
            logger.error(f"Error in Claude resume optimization: {e}")
            optimized_resume["optimization_metadata"] = {
                "optimization_error": str(e),
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "fallback_applied": True,
            }
            return optimized_resume


class GeminiProvider(LLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.genai = genai
        self.api_key = config.get("api_key") or config.get(
            "apiKey"
        )  # Support both formats
        self.model = config.get("model", "gemini-pro")

        # Ensure we have an API key
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Please provide 'api_key' or 'apiKey' in config."
            )

        # Configure the genai library with the provided API key
        self.genai.configure(api_key=self.api_key)
        self.model_client = genai.GenerativeModel(self.model)

    def _get_gemini_resume_sections_schema(self):
        """Create Gemini-compatible schema for resume sections extraction"""
        return {
            "type": "object",
            "properties": {
                "education": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "university": {"type": "string"},
                            "degree": {"type": "string"},
                            "location": {"type": "string"},
                            "from_year": {"type": "string"},
                            "to_year": {"type": "string"},
                            "gpa": {"type": "string"},
                        },
                        "required": ["university", "degree"],
                    },
                },
                "work_experience": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "company": {"type": "string"},
                            "location": {"type": "string"},
                            "from_year": {"type": "string"},
                            "to_year": {"type": "string"},
                            "summary": {"type": "string"},
                            "projects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "bullets": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["name"],
                                },
                            },
                        },
                        "required": ["title", "company"],
                    },
                },
                "projects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "bullets"],
                    },
                },
                "skills": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["education", "work_experience", "projects", "skills"],
        }

    def _get_gemini_personal_details_schema(self):
        """Create Gemini-compatible schema for personal details extraction"""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "linkedin": {"type": "string"},
                "github": {"type": "string"},
                "portfolio": {"type": "string"},
                "website": {"type": "string"},
                "address": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["name", "email"],
        }

    async def extract_personal_details(self, text: str) -> PersonalDetails:
        """
        Extract personal details using Gemini API with proper schema.
        """
        loop = asyncio.get_event_loop()

        def sync_call():
            prompt = f"""
            Extract personal details from the following resume text. Return as JSON with keys: name, email, phone, linkedin, github, portfolio, website, address, summary.
            Resume text:
            {text}
            
            Return only the JSON object, no additional text.
            """

            # Get the Gemini-compatible schema
            schema = self._get_gemini_personal_details_schema()

            return self.model_client.generate_content(
                contents=prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )

        try:
            response = await loop.run_in_executor(None, sync_call)
            response_text = response.text.strip()

            # Try to extract JSON from the response
            if response_text.startswith("```json"):
                response_text = (
                    response_text.replace("```json", "").replace("```", "").strip()
                )
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            try:
                parsed_data = json.loads(response_text)
                # Ensure required fields are present
                if "name" not in parsed_data:
                    parsed_data["name"] = "Unknown"
                if "email" not in parsed_data:
                    parsed_data["email"] = ""

                return PersonalDetails(**parsed_data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"JSON parsing failed: {str(e)}, trying fallback")
                # Fallback to basic extraction if JSON parsing fails
                return PersonalDetails(
                    name="Unknown", email="", phone=None, summary=response_text
                )
        except Exception as e:
            logger.error(f"Error in Gemini extract_personal_details: {str(e)}")
            # Return a minimal PersonalDetails object if there's an error
            return PersonalDetails(
                name="Unknown",
                email="",
                phone=None,
                summary=f"Error extracting details: {str(e)}",
            )

    async def extract_sections(self, text: str) -> Dict:
        """
        Extract resume sections using Gemini API with proper schema.
        """
        import asyncio
        import json

        loop = asyncio.get_event_loop()

        prompt = f"""Extract the following sections from the resume text: education, work_experience, projects, skills.
                Return as JSON with these keys.
                For education, provide a list of objects with university, degree, location, from_year, to_year, and gpa.
                For work_experience, provide a list of objects with title, company, location, from_year, to_year, summary, and a list of projects (each with name, summary, and bullets).
                For projects, provide a list of objects with name and bullets.
                For skills, provide a list of strings.
                Resume text:
                {text}
                Return only the JSON object, no additional text."""

        def sync_call():
            # Get the Gemini-compatible schema
            schema = self._get_gemini_resume_sections_schema()

            return self.model_client.generate_content(
                contents=prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )

        try:
            response = await loop.run_in_executor(None, sync_call)
            logger.info(f"Gemini response: {type(response.text)}")
            parsed_data = json.loads(response.text)
            logger.info(f"Gemini response: {parsed_data}")
            return parsed_data

        except Exception as e:
            logger.error(f"Error in Gemini extract_sections: {str(e)}")
            # Fallback: try without schema if schema fails
            try:

                def fallback_sync_call():
                    return self.model_client.generate_content(
                        contents=prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                        ),
                    )

                response = await loop.run_in_executor(None, fallback_sync_call)
                response_text = response.text.strip()

                # Clean up response text
                if response_text.startswith("```json"):
                    response_text = (
                        response_text.replace("```json", "").replace("```", "").strip()
                    )
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()

                return json.loads(response_text)

            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                # Return a basic structure if everything fails
                return {
                    "education": [],
                    "work_experience": [],
                    "projects": [],
                    "skills": [],
                    "error": f"Failed to parse resume: {str(fallback_error)}",
                }

    async def generate_simple_response(self, prompt: str) -> str:
        """Generate a simple response for testing configuration"""
        import asyncio

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content(
                contents=prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=100,
                    temperature=0.3,
                ),
            )

        try:
            response = await loop.run_in_executor(None, sync_call)
            return response.text or "Test response received successfully"
        except Exception as e:
            raise Exception(f"Gemini API test failed: {str(e)}")

    async def generate_conversation_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AIResponse:
        """Generate conversational response using Gemini"""
        system_prompt = self._build_system_prompt(context, user_profile)
        history_context = self._format_conversation_history(conversation_history)

        full_prompt = f"{system_prompt}\n\nConversation History:\n{history_context}\n\nCurrent Message: {message}\n\nResponse:"

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content([full_prompt])

        response = await loop.run_in_executor(None, sync_call)
        response_text = response.text

        # Generate suggestions if the response indicates improvements
        suggestions = await self._extract_suggestions_from_response(
            response_text, context.current_section, context
        )

        return AIResponse(
            message=response_text,
            suggestions=suggestions,
            confidence=0.7,
            follow_up_questions=self._generate_follow_up_questions(message, context),
        )

    async def generate_streaming_response(
        self,
        message: str,
        context: ResumeContext,
        conversation_history: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response for real-time chat"""
        # Gemini doesn't support streaming in the same way, so we'll simulate it
        response = await self.generate_conversation_response(
            message, context, conversation_history, user_profile
        )

        # Simulate streaming by yielding chunks
        words = response.message.split()
        for i in range(0, len(words), 3):  # Yield 3 words at a time
            chunk = " ".join(words[i : i + 3])
            if i + 3 < len(words):
                chunk += " "
            yield chunk
            await asyncio.sleep(0.1)  # Small delay to simulate streaming

    async def generate_section_suggestions(
        self,
        section: str,
        content: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Generate suggestions for a specific resume section"""
        prompt = f"""Analyze the {section} section and provide specific improvement suggestions.

Current {section} content:
{content}

Provide 3-5 specific suggestions for improvement. For each suggestion, include:
1. Type (content, structure, keyword, formatting)
2. Brief title
3. Detailed description
4. Impact score (0.0-1.0)
5. Reasoning

Format as a clear list."""

        if user_profile:
            prompt += f"\nUser Profile: {user_profile.model_dump_json()}"

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content([prompt])

        response = await loop.run_in_executor(None, sync_call)
        response_text = response.text

        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def optimize_content_for_job(
        self,
        content: str,
        job_description: str,
        section: str,
        context: ResumeContext,
        user_profile: Optional[UserProfile] = None,
    ) -> List[Suggestion]:
        """Optimize content for a specific job description"""
        prompt = f"""Optimize the {section} section to better match this job description.

Job Description:
{job_description[:1000]}...

Current {section} content:
{content}

Provide specific optimization suggestions that will improve the match between the resume section and job requirements.
Focus on relevant keywords, skills, and experiences that align with the job posting."""

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content([prompt])

        response = await loop.run_in_executor(None, sync_call)
        response_text = response.text

        return await self._extract_suggestions_from_response(
            response_text, section, context
        )

    async def _extract_suggestions_from_response(
        self, response_text: str, section: str, context: ResumeContext
    ) -> List[Suggestion]:
        """Extract suggestions from AI response text"""
        suggestions = []

        if "suggest" in response_text.lower() or "improve" in response_text.lower():
            suggestion = Suggestion(
                type="content",
                title="AI Recommendation",
                description=(
                    response_text[:200] + "..."
                    if len(response_text) > 200
                    else response_text
                ),
                impact_score=0.6,
                reasoning="Based on AI analysis of content and context",
                section=section,
                confidence=0.6,
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_follow_up_questions(
        self, message: str, context: ResumeContext
    ) -> List[str]:
        """Generate follow-up questions based on the conversation"""
        questions = []

        if "experience" in message.lower():
            questions.append(
                "Would you like me to help quantify your achievements with specific metrics?"
            )
        if "skills" in message.lower():
            questions.append(
                "Should we prioritize technical skills or soft skills for this role?"
            )
        if "job" in message.lower():
            questions.append(
                "Do you have a specific job posting you'd like to optimize for?"
            )

        return questions[:2]  # Limit to 2 questions

    async def optimize_resume(
        self,
        resume_data: Dict[str, Any],
        job_description: str,
        optimization_goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize entire resume for a specific job description using Gemini"""
        optimized_resume = resume_data.copy()

        try:
            # Analyze job description
            jd_prompt = f"""Analyze this job description and extract key information:

Job Description:
{job_description}

Please provide a structured analysis including:
1. Required technical skills
2. Required soft skills
3. Key responsibilities and qualifications
4. Important keywords and industry terms
5. Experience level requirements
6. Company culture and values

Provide a clear, organized analysis."""

            jd_response = await self.model.generate_content_async(jd_prompt)
            jd_analysis = jd_response.text

            # Optimize skills section
            if "skills" in resume_data and resume_data["skills"]:
                skills_prompt = f"""Based on this job analysis:
{jd_analysis[:500]}...

Current Skills Section:
{resume_data['skills']}

Please optimize this skills section to better match the job requirements:
1. Add relevant skills mentioned in the job description
2. Prioritize skills that are most important for this role
3. Use terminology consistent with the job posting
4. Maintain truthfulness and credibility

Return only the improved skills section."""

                skills_response = await self.model.generate_content_async(skills_prompt)
                optimized_resume["skills"] = skills_response.text

            # Optimize summary/objective
            summary_field = "summary" if "summary" in resume_data else "objective"
            if summary_field in resume_data and resume_data[summary_field]:
                summary_prompt = f"""Job Analysis Summary:
{jd_analysis[:400]}...

Current {summary_field}:
{resume_data[summary_field]}

Please rewrite this {summary_field} to better align with the job requirements:
1. Emphasize relevant experience and achievements
2. Incorporate important keywords naturally
3. Show clear value proposition for this specific role
4. Maintain professional tone and accuracy

Return only the improved {summary_field}."""

                summary_response = await self.model.generate_content_async(
                    summary_prompt
                )
                optimized_resume[summary_field] = summary_response.text

            # Add optimization metadata
            optimized_resume["optimization_metadata"] = {
                "job_description_analyzed": True,
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "sections_optimized": ["skills", summary_field],
                "job_analysis": jd_analysis,
                "optimization_goals": optimization_goals
                or ["ats_optimization", "keyword_matching"],
                "model_used": self.model_name,
            }

            return optimized_resume

        except Exception as e:
            logger.error(f"Error in Gemini resume optimization: {e}")
            optimized_resume["optimization_metadata"] = {
                "optimization_error": str(e),
                "optimization_timestamp": datetime.utcnow().isoformat(),
                "fallback_applied": True,
            }
            return optimized_resume


# Factory pattern for LLM providers
class LLMProviderFactory:
    _providers = {}

    @classmethod
    def register(cls, name: str, provider_cls):
        cls._providers[name.lower()] = provider_cls

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> LLMProviderBase:
        provider_cls = cls._providers.get(provider_name.lower())
        if not provider_cls:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
        return provider_cls(config)


# Register providers
LLMProviderFactory.register("ollama", OllamaProvider)
LLMProviderFactory.register("openai", OpenAIProvider)
LLMProviderFactory.register("claude", ClaudeProvider)
LLMProviderFactory.register("gemini", GeminiProvider)


# Add get_llm_provider function for import
def get_llm_provider(provider_name: str, config: dict):
    return LLMProviderFactory.create(provider_name, config)
