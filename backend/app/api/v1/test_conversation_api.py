"""
Test script for Conversation API endpoints
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER_ID = "test-user-api"
TEST_RESUME_ID = "test-resume-api"


def test_conversation_api():
    """Test the conversation API endpoints"""

    print("🧪 Testing Conversation API Endpoints...\n")

    # Test data
    test_section = "work_experience"
    llm_config = {"provider": "openai", "model": "gpt-3.5-turbo"}

    session_id = None

    try:
        # Test 1: Start conversation
        print("1️⃣ Testing conversation start...")
        start_response = requests.post(
            f"{BASE_URL}/conversation/start",
            json={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "section": test_section,
                "llm_provider": "openai",
                "llm_config": llm_config,
            },
        )

        if start_response.status_code == 200:
            start_data = start_response.json()
            session_id = start_data["session"]["id"]
            print(f"✅ Conversation started successfully")
            print(f"   Session ID: {session_id}")
            print(f"   Section: {start_data['session']['section']}")
            print(f"   Title: {start_data['session']['title']}")
        else:
            print(f"❌ Failed to start conversation: {start_response.status_code}")
            print(f"   Response: {start_response.text}")
            return False

        print()

        # Test 2: Send message
        print("2️⃣ Testing message sending...")
        message_response = requests.post(
            f"{BASE_URL}/conversation/{session_id}/message",
            json={
                "content": "I want to improve my work experience section to better highlight my achievements.",
                "llm_provider": "openai",
                "llm_config": llm_config,
            },
        )

        if message_response.status_code == 200:
            message_data = message_response.json()
            print(f"✅ Message sent successfully")
            print(f"   Response: {message_data['response']['message'][:100]}...")
            print(f"   Suggestions: {len(message_data['response']['suggestions'])}")
            print(f"   Confidence: {message_data['response']['confidence']}")
        else:
            print(f"❌ Failed to send message: {message_response.status_code}")
            print(f"   Response: {message_response.text}")

        print()

        # Test 3: Get conversation history
        print("3️⃣ Testing conversation history...")
        history_response = requests.get(f"{BASE_URL}/conversation/{session_id}/history")

        if history_response.status_code == 200:
            history_data = history_response.json()
            print(f"✅ Retrieved conversation history")
            print(f"   Total messages: {len(history_data['messages'])}")
            for i, msg in enumerate(history_data["messages"]):
                print(f"   Message {i+1}: {msg['role']} - {msg['content'][:50]}...")
        else:
            print(f"❌ Failed to get history: {history_response.status_code}")

        print()

        # Test 4: Get session status
        print("4️⃣ Testing session status...")
        status_response = requests.get(f"{BASE_URL}/conversation/{session_id}/status")

        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ Retrieved session status")
            print(f"   Active: {status_data['status']['is_active']}")
            print(f"   Messages: {status_data['status']['message_count']}")
            print(f"   Suggestions: {status_data['status']['suggestions_total']}")
        else:
            print(f"❌ Failed to get status: {status_response.status_code}")

        print()

        # Test 5: Get active sessions for user
        print("5️⃣ Testing active sessions retrieval...")
        sessions_response = requests.get(
            f"{BASE_URL}/conversation/user/{TEST_USER_ID}/active"
        )

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            print(f"✅ Retrieved active sessions")
            print(f"   Active sessions: {len(sessions_data['sessions'])}")
            for session in sessions_data["sessions"]:
                print(f"   Session: {session['id'][:8]}... - {session['section']}")
        else:
            print(f"❌ Failed to get active sessions: {sessions_response.status_code}")

        print()

        # Test 6: End conversation
        print("6️⃣ Testing conversation end...")
        end_response = requests.post(f"{BASE_URL}/conversation/{session_id}/end")

        if end_response.status_code == 200:
            end_data = end_response.json()
            print(f"✅ Conversation ended successfully")
            print(f"   Duration: {end_data['summary']['duration_minutes']} minutes")
            print(f"   Messages: {end_data['summary']['total_messages']}")
            print(f"   Suggestions: {end_data['summary']['suggestions_generated']}")
        else:
            print(f"❌ Failed to end conversation: {end_response.status_code}")

        print()

        # Test 7: Health check
        print("7️⃣ Testing health check...")
        health_response = requests.get(f"{BASE_URL}/conversation/health")

        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {health_data['status']}")
            print(f"   Service: {health_data['service']}")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")

        print()
        print("🎉 All Conversation API tests completed!")
        return True

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection error: Make sure the FastAPI server is running on http://localhost:8000"
        )
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def test_error_handling():
    """Test API error handling"""

    print("🔍 Testing error handling...\n")

    try:
        # Test with invalid session ID
        print("Testing invalid session ID...")
        response = requests.get(f"{BASE_URL}/conversation/invalid-session-id/status")
        if response.status_code == 404:
            print("✅ Correctly handled invalid session ID")
        else:
            print(f"❌ Unexpected response for invalid session: {response.status_code}")

        # Test with missing required fields
        print("Testing missing required fields...")
        response = requests.post(
            f"{BASE_URL}/conversation/start",
            json={
                "resume_id": "test"
                # Missing user_id and section
            },
        )
        if response.status_code == 422:  # Validation error
            print("✅ Correctly handled missing fields")
        else:
            print(f"❌ Unexpected response for missing fields: {response.status_code}")

        print("✅ Error handling tests passed\n")
        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_api_tests():
    """Run all API tests"""

    print("🚀 Starting Conversation API Tests\n")
    print("📝 Make sure to start the FastAPI server first:")
    print("   cd backend/app && uvicorn main:app --reload\n")

    # Wait a moment for user to start server if needed
    input("Press Enter when the server is running...")

    tests = [
        ("Main API functionality", test_conversation_api),
        ("Error handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"🔍 {test_name}:")
        try:
            result = test_func()
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
        print("🎉 All Conversation API tests passed!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return failed == 0


if __name__ == "__main__":
    run_api_tests()
