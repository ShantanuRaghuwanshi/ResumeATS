"""
WebSocket test client for conversation API
"""

import asyncio
import websockets
import json
from datetime import datetime


async def test_websocket_connection():
    """Test WebSocket connection for real-time conversation"""

    print("🔌 Testing WebSocket Connection...\n")

    # Test session ID (you'll need to create a session first)
    session_id = "test-session-ws"
    uri = f"ws://localhost:8000/api/v1/conversation/{session_id}/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to WebSocket: {uri}")

            # Wait for connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Received: {data}")

            # Send a ping
            await websocket.send(
                json.dumps({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
            )
            print("📤 Sent ping")

            # Wait for pong
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Received pong: {data}")

            # Send a chat message
            await websocket.send(
                json.dumps(
                    {
                        "type": "message",
                        "content": "Hello, I need help with my resume!",
                        "llm_provider": "openai",
                        "llm_config": {},
                    }
                )
            )
            print("📤 Sent chat message")

            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Received response: {data}")

            print("✅ WebSocket test completed successfully!")

    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused. Make sure the FastAPI server is running.")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")


async def test_websocket_with_session():
    """Test WebSocket with a real conversation session"""

    print("🔌 Testing WebSocket with Real Session...\n")

    # First, create a session via HTTP API
    import requests

    try:
        # Create session
        start_response = requests.post(
            "http://localhost:8000/api/v1/conversation/start",
            json={
                "resume_id": "test-resume-ws",
                "user_id": "test-user-ws",
                "section": "work_experience",
                "llm_provider": "openai",
                "llm_config": {},
            },
        )

        if start_response.status_code != 200:
            print(f"❌ Failed to create session: {start_response.status_code}")
            return

        session_data = start_response.json()
        session_id = session_data["session"]["id"]
        print(f"✅ Created session: {session_id}")

        # Connect to WebSocket
        uri = f"ws://localhost:8000/api/v1/conversation/{session_id}/ws"

        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to WebSocket for session {session_id}")

            # Receive connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Connection confirmed: {data['type']}")

            # Send multiple messages
            messages = [
                "I want to improve my work experience section.",
                "Can you help me make it more impactful?",
                "What specific changes would you recommend?",
            ]

            for i, message in enumerate(messages):
                print(f"\n📤 Sending message {i+1}: {message}")

                await websocket.send(
                    json.dumps(
                        {
                            "type": "message",
                            "content": message,
                            "llm_provider": "openai",
                            "llm_config": {},
                        }
                    )
                )

                # Wait for response
                response = await websocket.recv()
                data = json.loads(response)

                if data["type"] == "message_response":
                    print(f"📨 AI Response: {data['response']['message'][:100]}...")
                    print(f"   Suggestions: {len(data['response']['suggestions'])}")
                    print(f"   Confidence: {data['response']['confidence']}")
                else:
                    print(f"📨 Received: {data}")

                # Small delay between messages
                await asyncio.sleep(1)

            print("\n✅ WebSocket conversation test completed!")

        # Clean up - end the session
        end_response = requests.post(
            f"http://localhost:8000/api/v1/conversation/{session_id}/end"
        )
        if end_response.status_code == 200:
            print("✅ Session ended successfully")

    except requests.exceptions.ConnectionError:
        print("❌ HTTP Connection error: Make sure the FastAPI server is running")
    except websockets.exceptions.ConnectionRefused:
        print("❌ WebSocket connection refused")
    except Exception as e:
        print(f"❌ Test failed: {e}")


def run_websocket_tests():
    """Run WebSocket tests"""

    print("🚀 Starting WebSocket Tests\n")
    print("📝 Make sure to start the FastAPI server first:")
    print("   cd backend/app && uvicorn main:app --reload\n")

    input("Press Enter when the server is running...")

    # Run tests
    asyncio.run(test_websocket_with_session())


if __name__ == "__main__":
    run_websocket_tests()
