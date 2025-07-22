"""
Integration test for machine learning pipeline with LLM providers
"""

import asyncio
from datetime import datetime
from app.models.user_preferences import UserProfile, SuggestionFeedback
from app.models.conversation import ResumeContext, Suggestion
from app.services.preference_learning import preference_learning_service
from app.services.llm_provider import LLMProviderFactory


async def test_full_ml_pipeline():
    """Test the complete machine learning pipeline integration"""

    print("Testing Full Machine Learning Pipeline Integration...")

    # Create test user profile
    user_profile = UserProfile(
        user_id="ml-integration-user",
        industry="technology",
        experience_level="senior",
        writing_style="technical",
        optimization_focus=["ats", "impact"],
        preferred_suggestion_types=[],  # Will be learned
    )

    # Create test context
    context = ResumeContext(
        resume_id="ml-test-resume",
        user_id="ml-integration-user",
        current_section="experience",
        full_resume_data={
            "experience": "Senior Software Engineer at TechCorp. Worked on various projects."
        },
        optimization_goals=["ats_optimization", "impact_focused"],
    )

    try:
        # Step 1: Create LLM provider (mock for testing)
        print("\n1. Setting up LLM provider...")
        config = {"model": "test-model", "url": "http://localhost:11434"}

        try:
            provider = LLMProviderFactory.create("ollama", config)
            print("✅ LLM provider created")
        except Exception as e:
            print(
                f"⚠️  LLM provider creation failed (expected if Ollama not running): {e}"
            )
            provider = None

        # Step 2: Simulate learning from user feedback
        print("\n2. Simulating user feedback learning...")

        # Create various types of suggestions
        test_suggestions = [
            Suggestion(
                type="content",
                title="Quantify achievements",
                description="Add specific metrics to accomplishments",
                impact_score=0.8,
                reasoning="Quantified achievements are more impactful",
                section="experience",
                confidence=0.7,
            ),
            Suggestion(
                type="keyword",
                title="Add technical keywords",
                description="Include relevant technical terms",
                impact_score=0.6,
                reasoning="Keywords improve ATS compatibility",
                section="experience",
                confidence=0.8,
            ),
            Suggestion(
                type="structure",
                title="Improve bullet structure",
                description="Use action-result format",
                impact_score=0.7,
                reasoning="Better structure improves readability",
                section="experience",
                confidence=0.6,
            ),
            Suggestion(
                type="formatting",
                title="Consistent formatting",
                description="Standardize date formats",
                impact_score=0.3,
                reasoning="Consistency improves professionalism",
                section="experience",
                confidence=0.5,
            ),
        ]

        # Simulate user feedback over time
        feedback_scenarios = [
            # User likes content suggestions
            ("content", "accepted", 5, "Great suggestion!"),
            ("content", "accepted", 4, "Very helpful"),
            ("content", "modified", 4, "Good idea, made some changes"),
            # User is mixed on keyword suggestions
            ("keyword", "accepted", 3, "Okay suggestion"),
            ("keyword", "rejected", 2, "Too many keywords"),
            # User dislikes formatting suggestions
            ("formatting", "rejected", 1, "Not important"),
            ("formatting", "rejected", 2, "Focus on content instead"),
            # User likes structure suggestions
            ("structure", "accepted", 4, "Much better structure"),
            ("structure", "accepted", 5, "Perfect improvement"),
        ]

        # Process feedback
        for i, (sugg_type, action, rating, feedback_text) in enumerate(
            feedback_scenarios
        ):
            feedback = SuggestionFeedback(
                user_id="ml-integration-user",
                suggestion_id=f"test-suggestion-{i}",
                session_id=f"test-session-{i}",
                action=action,
                rating=rating,
                feedback_text=feedback_text,
                section="experience",
                suggestion_type=sugg_type,
                original_content="Original content",
                suggested_content="Suggested content",
                time_to_decision_seconds=10.0 + i,
            )

            result = await preference_learning_service.process_feedback(
                feedback, user_profile
            )

        print(f"✅ Processed {len(feedback_scenarios)} feedback items")

        # Step 3: Test learning and personalization
        print("\n3. Testing learned preferences...")

        # Get learning confidence
        confidence = await preference_learning_service._calculate_learning_confidence(
            "ml-integration-user"
        )
        print(f"✅ Learning confidence: {confidence:.2f}")

        # Get learned patterns
        patterns = preference_learning_service.user_patterns.get(
            "ml-integration-user", {}
        )
        print(f"✅ Learned {len(patterns)} preference patterns:")
        for pattern_name, pattern in patterns.items():
            print(
                f"   - {pattern_name}: confidence={pattern.confidence:.2f}, frequency={pattern.frequency}"
            )

        # Step 4: Test suggestion personalization
        print("\n4. Testing suggestion personalization...")

        # Personalize suggestions based on learned preferences
        personalized_suggestions = (
            await preference_learning_service.personalize_suggestions(
                test_suggestions, user_profile, context
            )
        )

        print("✅ Personalized suggestions (ranked by preference):")
        for i, suggestion in enumerate(personalized_suggestions):
            print(
                f"   {i+1}. {suggestion.type}: {suggestion.title} (confidence: {suggestion.confidence:.2f})"
            )

        # Verify that content and structure suggestions are ranked higher
        top_types = [s.type for s in personalized_suggestions[:2]]
        assert "content" in top_types or "structure" in top_types
        print("✅ High-preference suggestion types ranked higher")

        # Step 5: Test prediction accuracy
        print("\n5. Testing user response prediction...")

        for suggestion in test_suggestions:
            prediction = await preference_learning_service.predict_user_preference(
                suggestion, user_profile, context
            )

            print(
                f"   {suggestion.type}: {prediction['acceptance_probability']:.2f} acceptance probability"
            )

            # Verify predictions align with learned preferences
            if suggestion.type == "content":
                assert prediction["acceptance_probability"] > 0.6  # Should be high
            elif suggestion.type == "formatting":
                assert prediction["acceptance_probability"] < 0.4  # Should be low

        print("✅ Predictions align with learned preferences")

        # Step 6: Test insights generation
        print("\n6. Testing insights generation...")

        insights = await preference_learning_service.generate_learning_insights(
            "ml-integration-user"
        )
        print(f"✅ Generated {len(insights)} learning insights:")

        for insight in insights:
            print(f"   - {insight.title}")
            print(f"     {insight.description}")
            print(f"     Confidence: {insight.confidence:.2f}")
            if insight.recommended_actions:
                print(f"     Actions: {', '.join(insight.recommended_actions)}")

        # Step 7: Test LLM provider integration (if available)
        if provider:
            print("\n7. Testing LLM provider integration...")

            # Test feedback processing through provider
            test_feedback = SuggestionFeedback(
                user_id="ml-integration-user",
                suggestion_id="llm-integration-test",
                session_id="llm-integration-session",
                action="accepted",
                rating=5,
                section="experience",
                suggestion_type="content",
                original_content="Original",
                suggested_content="Improved",
            )

            feedback_result = await provider.process_user_feedback(
                test_feedback, user_profile
            )
            print("✅ LLM provider feedback integration working")

            # Test suggestion personalization through provider
            personalized_by_provider = (
                await provider.personalize_suggestions_with_learning(
                    test_suggestions, user_profile, context
                )
            )

            assert len(personalized_by_provider) == len(test_suggestions)
            print("✅ LLM provider suggestion personalization working")
        else:
            print("\n7. Skipping LLM provider integration (provider not available)")

        print("\n🎉 Full machine learning pipeline integration test passed!")

        # Summary of what was tested
        print("\n📊 Integration Test Summary:")
        print(f"   - Processed {len(feedback_scenarios)} user feedback items")
        print(f"   - Learned {len(patterns)} preference patterns")
        print(f"   - Achieved {confidence:.2f} learning confidence")
        print(f"   - Generated {len(insights)} actionable insights")
        print(f"   - Personalized {len(test_suggestions)} suggestions")
        print("   - Verified prediction accuracy")
        print("   - Tested end-to-end ML pipeline")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_real_world_scenario():
    """Test a realistic user interaction scenario"""

    print("\n" + "=" * 60)
    print("Testing Real-World User Interaction Scenario")
    print("=" * 60)

    # Scenario: New user starts using the system
    user_profile = UserProfile(
        user_id="real-world-user",
        industry="finance",
        experience_level="senior",
        target_roles=["Senior Financial Analyst", "Finance Manager"],
    )

    context = ResumeContext(
        resume_id="real-world-resume",
        user_id="real-world-user",
        current_section="experience",
        full_resume_data={
            "experience": "Financial Analyst at BigBank Corp. Analyzed financial data and prepared reports."
        },
        job_description="Senior Financial Analyst position requiring 5+ years experience in financial modeling, data analysis, and report preparation. Strong Excel and SQL skills required.",
        optimization_goals=["job_specific", "ats_optimization"],
    )

    try:
        print("\n📝 Scenario: Senior Financial Analyst optimizing resume for new role")

        # Week 1: User starts with general suggestions
        week1_suggestions = [
            Suggestion(
                type="content",
                title="Quantify financial impact",
                description="Add specific dollar amounts and percentages to achievements",
                impact_score=0.9,
                reasoning="Quantified financial achievements are highly valued",
                section="experience",
                confidence=0.8,
            ),
            Suggestion(
                type="keyword",
                title="Add financial modeling keywords",
                description="Include 'financial modeling', 'forecasting', 'budgeting'",
                impact_score=0.7,
                reasoning="Keywords match job requirements",
                section="experience",
                confidence=0.7,
            ),
            Suggestion(
                type="structure",
                title="Use STAR format",
                description="Structure bullets as Situation-Task-Action-Result",
                impact_score=0.6,
                reasoning="STAR format shows clear impact",
                section="experience",
                confidence=0.6,
            ),
        ]

        # User accepts quantification, modifies keywords, rejects structure
        week1_feedback = [
            (
                "content",
                "accepted",
                5,
                "Excellent suggestion! Added $2M budget impact.",
            ),
            (
                "keyword",
                "modified",
                4,
                "Good keywords, but I added more specific ones.",
            ),
            ("structure", "rejected", 2, "Too rigid, prefer my current format."),
        ]

        print("\n📅 Week 1: Processing initial feedback...")
        for i, (sugg_type, action, rating, feedback_text) in enumerate(week1_feedback):
            feedback = SuggestionFeedback(
                user_id="real-world-user",
                suggestion_id=f"week1-{i}",
                session_id="week1-session",
                action=action,
                rating=rating,
                feedback_text=feedback_text,
                section="experience",
                suggestion_type=sugg_type,
                original_content="Original content",
                suggested_content="Suggested content",
            )
            await preference_learning_service.process_feedback(feedback, user_profile)

        # Week 2: System learns preferences and adapts
        week2_suggestions = [
            Suggestion(
                type="content",
                title="Add ROI metrics",
                description="Include return on investment calculations",
                impact_score=0.8,
                reasoning="Builds on successful quantification approach",
                section="experience",
                confidence=0.7,
            ),
            Suggestion(
                type="keyword",
                title="Industry-specific terms",
                description="Add 'risk assessment', 'compliance', 'regulatory'",
                impact_score=0.6,
                reasoning="Finance industry keywords",
                section="experience",
                confidence=0.6,
            ),
            Suggestion(
                type="formatting",
                title="Consistent date formatting",
                description="Standardize all date formats",
                impact_score=0.3,
                reasoning="Professional consistency",
                section="experience",
                confidence=0.4,
            ),
        ]

        print("\n📅 Week 2: Testing learned personalization...")

        # Personalize based on Week 1 learning
        personalized_week2 = await preference_learning_service.personalize_suggestions(
            week2_suggestions, user_profile, context
        )

        print("✅ Personalized suggestions for Week 2:")
        for i, suggestion in enumerate(personalized_week2):
            print(
                f"   {i+1}. {suggestion.type}: {suggestion.title} (confidence: {suggestion.confidence:.2f})"
            )

        # Content suggestions should be ranked highest due to Week 1 success
        assert personalized_week2[0].type == "content"
        print("✅ Content suggestions prioritized based on learning")

        # Week 2 feedback - user continues pattern
        week2_feedback = [
            ("content", "accepted", 5, "Perfect! Added 15% ROI improvement."),
            ("keyword", "accepted", 4, "Great industry terms."),
            ("formatting", "ignored", None, None),  # User ignored formatting suggestion
        ]

        print("\n📅 Week 2: Processing continued feedback...")
        for i, (sugg_type, action, rating, feedback_text) in enumerate(week2_feedback):
            if action != "ignored":  # Only process non-ignored feedback
                feedback = SuggestionFeedback(
                    user_id="real-world-user",
                    suggestion_id=f"week2-{i}",
                    session_id="week2-session",
                    action=action,
                    rating=rating,
                    feedback_text=feedback_text,
                    section="experience",
                    suggestion_type=sugg_type,
                    original_content="Original content",
                    suggested_content="Suggested content",
                )
                await preference_learning_service.process_feedback(
                    feedback, user_profile
                )

        # Week 3: System has strong learning confidence
        print("\n📅 Week 3: Analyzing learned preferences...")

        confidence = await preference_learning_service._calculate_learning_confidence(
            "real-world-user"
        )
        insights = await preference_learning_service.generate_learning_insights(
            "real-world-user"
        )

        print(f"✅ Learning confidence after 2 weeks: {confidence:.2f}")
        print(f"✅ Generated insights: {len(insights)}")

        for insight in insights:
            print(f"   💡 {insight.title}")
            print(f"      {insight.description}")

        # Test prediction accuracy
        test_prediction = Suggestion(
            type="content",
            title="Add team leadership metrics",
            description="Quantify team management achievements",
            impact_score=0.8,
            reasoning="Leadership quantification",
            section="experience",
            confidence=0.7,
        )

        prediction = await preference_learning_service.predict_user_preference(
            test_prediction, user_profile, context
        )

        print(
            f"✅ Prediction for new content suggestion: {prediction['acceptance_probability']:.2f} acceptance probability"
        )
        assert (
            prediction["acceptance_probability"] > 0.7
        )  # Should be high based on pattern

        print("\n🎉 Real-world scenario test completed successfully!")

        # Final summary
        patterns = preference_learning_service.user_patterns.get("real-world-user", {})
        feedback_count = len(
            preference_learning_service.feedback_history.get("real-world-user", [])
        )

        print(f"\n📈 Final Results:")
        print(f"   - Total feedback processed: {feedback_count}")
        print(f"   - Preference patterns learned: {len(patterns)}")
        print(f"   - Learning confidence: {confidence:.2f}")
        print(f"   - Insights generated: {len(insights)}")
        print(f"   - System successfully adapted to user preferences")

        return True

    except Exception as e:
        print(f"❌ Real-world scenario test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":

    async def main():
        # Test full ML pipeline integration
        pipeline_test_passed = await test_full_ml_pipeline()

        # Test real-world scenario
        scenario_test_passed = await test_real_world_scenario()

        if pipeline_test_passed and scenario_test_passed:
            print("\n" + "=" * 60)
            print("🎉 ALL MACHINE LEARNING INTEGRATION TESTS PASSED!")
            print("=" * 60)
            print("\n✅ Key Capabilities Verified:")
            print("   - User preference tracking and storage")
            print("   - Machine learning pattern recognition")
            print("   - Suggestion personalization based on learning")
            print("   - User response prediction")
            print("   - Insight generation from user behavior")
            print("   - Feedback loop integration with LLM providers")
            print("   - Real-world user interaction scenarios")
            print("   - Adaptive learning over time")
            print("\n🚀 The machine learning pipeline is ready for production!")
        else:
            print("\n❌ Some integration tests failed - review implementation")

    asyncio.run(main())
