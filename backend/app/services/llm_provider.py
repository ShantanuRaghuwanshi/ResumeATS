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
from abc import ABC, abstractmethod
from datetime import datetime


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
        from app.services.preference_learning import preference_learning_service

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
        from app.services.preference_learning import preference_learning_service

        return await preference_learning_service.personalize_suggestions(
            suggestions, user_profile, context
        )

    async def predict_user_response(
        self, suggestion: Suggestion, user_profile: UserProfile, context: ResumeContext
    ) -> Dict[str, float]:
        """Predict how user will likely respond to a suggestion"""
        from app.services.preference_learning import preference_learning_service

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


class GeminiProvider(LLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.genai = genai
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gemini-pro")
        self.genai.configure(api_key=self.api_key)
        self.model_client = genai.GenerativeModel(self.model)

    async def extract_personal_details(self, text: str) -> Dict:
        """
        Extract personal details using Gemini API.
        """

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content(
                ["Extract personal details from the resume text.", text]
            )

        response = await loop.run_in_executor(None, sync_call)
        try:
            return json.loads(response.text)
        except Exception:
            return {"result": response.text}

    async def extract_sections(self, text: str) -> Dict:
        """
        Extract resume sections using Gemini API.
        """
        import asyncio
        import json

        loop = asyncio.get_event_loop()

        def sync_call():
            return self.model_client.generate_content(
                ["Extract resume sections from the text.", text]
            )

        response = await loop.run_in_executor(None, sync_call)
        try:
            return json.loads(response.text)
        except Exception:
            return {"result": response.text}

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
