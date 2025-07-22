"""
Test script for ConversationManager service
"""

import asyncio
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.conversation_manager import ConversationManager
from database import get_database


async def test_conversation_manager():
    """Test the ConversationManager functionality"""

    print("🧪 Testing ConversationManager Service...\n")

    # Initialize manager
    manager = ConversationManager()

    # Test data
    user_id = "test-user-123"
    resume_id = "test-resume-456"
    section = "work_experience"

    # Mock resume data
    mock_resume_data = {
        "personal_details": {"name": "John Doe", "email": "john@example.com"},
        "work_experience": [
            {
                "title": "Software Developer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "to_date": "2023-12",
                "summary": "Worked on web applications",
            }
        ],
    }

    # Store mock resume data
    db = get_database()
    db.create(
        "resumes",
        resume_id,
        {"id": resume_id, "user_id": user_id, "data": mock_resume_data},
    )

    try:
        # Test 1: Start conversation session
        print("1️⃣ Testing session creation...")
        session = await manager.start_section_conversation(
            resume_id=resume_id,
            user_id=user_id,
            section=section,
            llm_provider="openai",
            llm_config={"model": "gpt-3.5-turbo"},
        )
        print(f"✅ Session created: {session.id}")
        print(f"   Section: {session.section}")
        print(f"   Title: {session.title}")
        print(f"   Messages: {len(session.messages)}")
        print()

        # Test 2: Send user message
        print("2️⃣ Testing message sending...")
        user_message = "I want to improve my work experience section to highlight my achievements better."
        response = await manager.send_message(
            session_id=session.id,
            content=user_message,
            role="user",
            llm_provider="openai",
        )
        print(f"✅ Message sent and response received")
        print(f"   Response: {response.message}")
        print(f"   Suggestions: {len(response.suggestions)}")
        print(f"   Confidence: {response.confidence}")
        print()

        # Test 3: Get conversation history
        print("3️⃣ Testing conversation history...")
        history = await manager.get_conversation_history(session.id)
        print(f"✅ Retrieved conversation history")
        print(f"   Total messages: {len(history)}")
        for i, msg in enumerate(history):
            print(f"   Message {i+1}: {msg.role} - {msg.content[:50]}...")
        print()

        # Test 4: Apply suggestion (if any)
        if response.suggestions:
            print("4️⃣ Testing suggestion application...")
            suggestion = response.suggestions[0]
            result = await manager.apply_suggestion(
                session_id=session.id,
                suggestion_id=suggestion.id,
                user_modifications="Make it more specific to backend development",
            )
            print(f"✅ Suggestion applied")
            print(f"   Success: {result['success']}")
            print(f"   Updated content: {result['updated_content']}")
            print()

        # Test 5: Get active sessions
        print("5️⃣ Testing active sessions retrieval...")
        active_sessions = await manager.get_active_sessions(user_id)
        print(f"✅ Retrieved active sessions")
        print(f"   Active sessions: {len(active_sessions)}")
        for sess in active_sessions:
            print(f"   Session: {sess.id} - {sess.section}")
        print()

        # Test 6: End session
        print("6️⃣ Testing session ending...")
        summary = await manager.end_session(session.id)
        print(f"✅ Session ended")
        print(f"   Duration: {summary.duration_minutes} minutes")
        print(f"   Messages: {summary.total_messages}")
        print(f"   Suggestions generated: {summary.suggestions_generated}")
        print(f"   Suggestions applied: {summary.suggestions_applied}")
        print()

        print("🎉 All ConversationManager tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_multiple_sessions():
    """Test multiple concurrent sessions"""

    print("🔄 Testing multiple concurrent sessions...\n")

    manager = ConversationManager()
    user_id = "test-user-multi"
    resume_id = "test-resume-multi"

    sessions = []
    sections = ["work_experience", "skills", "education"]

    try:
        # Create multiple sessions
        for section in sections:
            session = await manager.start_section_conversation(
                resume_id=resume_id, user_id=user_id, section=section
            )
            sessions.append(session)
            print(f"✅ Created session for {section}: {session.id}")

        # Send messages to each session
        for i, session in enumerate(sessions):
            await manager.send_message(
                session_id=session.id,
                content=f"Help me improve my {session.section} section",
                role="user",
            )
            print(f"✅ Sent message to {session.section} session")

        # Check active sessions
        active = await manager.get_active_sessions(user_id)
        print(f"✅ Active sessions: {len(active)}")

        # End all sessions
        for session in sessions:
            await manager.end_session(session.id)
            print(f"✅ Ended {session.section} session")

        print("🎉 Multiple sessions test passed!")
        return True

    except Exception as e:
        print(f"❌ Multiple sessions test failed: {e}")
        return False


async def run_all_tests():
    """Run all conversation manager tests"""

    print("🚀 Starting ConversationManager Tests\n")

    tests = [
        ("Basic ConversationManager functionality", test_conversation_manager),
        ("Multiple concurrent sessions", test_multiple_sessions),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"🔍 {test_name}:")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED\n")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}\n")

    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All ConversationManager tests passed!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return failed == 0


if __name__ == "__main__":
    asyncio.run(run_all_tests())
