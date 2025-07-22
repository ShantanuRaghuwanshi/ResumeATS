"""
Test script for enhanced LLM provider functionality
"""

import asyncio
from datetime import datetime
from app.models.conversation import ResumeContext, Message, Suggestion
from app.models.user_preferences import UserProfile
from app.services.llm_provider import LLMProviderFactory


async def test_enhanced_llm_provider():
    """Test the enhanced LLM provider functionality"""

    print("Testing Enhanced LLM Provider Functionality...")

    # Test configuration for Ollama (assuming it's available)
    config = {"model": "gemma3n:e4b", "url": "http://localhost:11434"}

    try:
        # Create provider instance
        provider = LLMProviderFactory.create("ollama", config)
        print("✅ Provider created successfully")

        # Test context management
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="experience",
            full_resume_data={"experience": "Software Engineer at Tech Corp"},
            optimization_goals=["ats_optimization", "keyword_enhancement"],
        )

        session_id = "test-session-789"
        provider.store_conversation_context(session_id, context)
        retrieved_context = provider.get_conversation_context(session_id)

        assert retrieved_context is not None
        assert retrieved_context.user_id == "test-user-456"
        print("✅ Context management working")

        # Test conversation history
        test_message = Message(
            session_id=session_id,
            role="user",
            content="Help me improve my experience section",
        )

        provider.update_conversation_history(session_id, test_message)
        history = provider.get_conversation_history(session_id)

        assert len(history) == 1
        assert history[0].content == "Help me improve my experience section"
        print("✅ Conversation history management working")

        # Test optimization strategies
        strategy = provider.get_optimization_strategy("ats_optimization")
        assert "focus" in strategy
        assert strategy["focus"] == "keyword_density"
        print("✅ Optimization strategies working")

        # Test user profile customization
        user_profile = UserProfile(
            user_id="test-user-456",
            industry="technology",
            experience_level="mid",
            writing_style="technical",
        )

        customized_strategy = provider.customize_strategy_for_user(
            "ats_optimization", user_profile
        )
        assert "industry_focus" in customized_strategy
        assert customized_strategy["industry_focus"] == "technology"
        print("✅ User profile customization working")

        # Test system prompt building
        system_prompt = provider._build_system_prompt(
            context, user_profile, "ats_optimization"
        )
        assert "experience section" in system_prompt.lower()
        assert "technology" in system_prompt.lower()
        print("✅ System prompt building working")

        print("\n🎉 All enhanced LLM provider tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


async def test_conversation_response():
    """Test conversation response generation (requires actual LLM)"""

    print("\nTesting Conversation Response Generation...")

    config = {"model": "gemma3n:e4b", "url": "http://localhost:11434"}

    try:
        provider = LLMProviderFactory.create("ollama", config)

        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="experience",
            full_resume_data={
                "experience": "Software Engineer at Tech Corp for 2 years"
            },
            optimization_goals=["keyword_enhancement"],
        )

        user_profile = UserProfile(
            user_id="test-user-456", industry="technology", experience_level="mid"
        )

        # Test conversation response
        response = await provider.generate_conversation_response(
            message="How can I make my experience section more impactful?",
            context=context,
            conversation_history=[],
            user_profile=user_profile,
        )

        assert response.message is not None
        assert len(response.message) > 0
        print("✅ Conversation response generated successfully")
        print(f"Response preview: {response.message[:100]}...")

        # Test section suggestions
        suggestions = await provider.generate_section_suggestions(
            section="experience",
            content="Software Engineer at Tech Corp for 2 years",
            context=context,
            user_profile=user_profile,
        )

        assert isinstance(suggestions, list)
        print(f"✅ Generated {len(suggestions)} suggestions")

        return True

    except Exception as e:
        print(f"❌ Conversation test failed: {str(e)}")
        print("Note: This test requires a running Ollama instance")
        return False


if __name__ == "__main__":

    async def main():
        # Test basic functionality
        basic_test_passed = await test_enhanced_llm_provider()

        # Test conversation functionality (may fail if Ollama not available)
        conversation_test_passed = await test_conversation_response()

        if basic_test_passed:
            print("\n✅ Enhanced LLM Provider implementation is working correctly!")
        else:
            print("\n❌ Enhanced LLM Provider has issues that need to be addressed")

    asyncio.run(main())
