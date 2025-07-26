#!/usr/bin/env python3
"""
Debug script to test session middleware behavior
"""

import asyncio
import aiohttp
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


async def test_middleware():
    """Test session middleware on upload_resume endpoint"""

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Test 1: Try upload without session - should fail
        print("=== Test 1: Upload without session ===")
        url = f"{base_url}/api/v1/upload_resume/"
        data = aiohttp.FormData()
        data.add_field(
            "file",
            b"test resume content",
            filename="test.txt",
            content_type="text/plain",
        )

        try:
            async with session.post(url, data=data) as response:
                print(f"Status: {response.status}")
                print(f"Content-Type: {response.content_type}")
                if response.content_type == "application/json":
                    result = await response.json()
                    print(f"Response: {result}")
                else:
                    text = await response.text()
                    print(f"Response text: {text}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n" + "=" * 50 + "\n")

        # Test 2: Create session first
        print("=== Test 2: Create session ===")
        session_url = f"{base_url}/api/v1/session/create"
        session_data = {
            "llm_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "test_key",
                "base_url": None,
                "temperature": 0.7,
                "max_tokens": 2000,
            }
        }

        try:
            async with session.post(session_url, json=session_data) as response:
                print(f"Session creation status: {response.status}")
                if response.content_type == "application/json":
                    session_result = await response.json()
                    print(f"Session response: {session_result}")

                    if response.status == 200 and "session_id" in session_result:
                        session_id = session_result["session_id"]
                        print(f"Created session: {session_id}")

                        # Test 3: Try upload with session
                        print("\n=== Test 3: Upload with session ===")
                        headers = {"X-Session-ID": session_id}

                        async with session.post(
                            url, data=data, headers=headers
                        ) as upload_response:
                            print(f"Upload status: {upload_response.status}")
                            if upload_response.content_type == "application/json":
                                upload_result = await upload_response.json()
                                print(f"Upload response: {upload_result}")
                            else:
                                upload_text = await upload_response.text()
                                print(f"Upload response text: {upload_text}")
                else:
                    text = await response.text()
                    print(f"Session response text: {text}")
        except Exception as e:
            print(f"Session creation error: {e}")


if __name__ == "__main__":
    print("Testing session middleware behavior...")
    print("Make sure the FastAPI server is running on localhost:8000")
    print("")

    asyncio.run(test_middleware())
