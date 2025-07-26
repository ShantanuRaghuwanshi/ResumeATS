"""
Test script to verify the session-based LLM configuration system
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class SessionBasedAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_llm_config(self, config):
        """Test LLM configuration"""
        url = f"{self.base_url}/api/v1/session/test-config"
        async with self.session.post(url, json=config) as response:
            result = await response.json()
            return response.status, result

    async def create_session(self, llm_config):
        """Create a new session"""
        url = f"{self.base_url}/api/v1/session/create"
        session_request = {
            "llm_config": llm_config,
            "device_id": "test-device-123",
            "session_duration_hours": 24,
            "metadata": {"test": True},
        }
        async with self.session.post(url, json=session_request) as response:
            result = await response.json()
            if response.status == 200:
                self.session_id = result.get("session_id")
            return response.status, result

    async def validate_session(self):
        """Validate current session"""
        if not self.session_id:
            return 400, {"error": "No session ID"}

        url = f"{self.base_url}/api/v1/session/validate/{self.session_id}"
        async with self.session.get(url) as response:
            result = await response.json()
            return response.status, result

    async def upload_resume_with_session(self, file_path):
        """Upload resume using session-based approach"""
        if not self.session_id:
            return 400, {"error": "No session ID"}

        url = f"{self.base_url}/api/v1/upload_resume/"
        headers = {"X-Session-ID": self.session_id}

        # Create a test file if it doesn't exist
        test_content = b"John Doe\njohndoe@email.com\n\nEducation:\nBachelor's Degree\n\nExperience:\nSoftware Engineer at Tech Corp"

        data = aiohttp.FormData()
        data.add_field(
            "file", test_content, filename="test_resume.txt", content_type="text/plain"
        )

        async with self.session.post(url, data=data, headers=headers) as response:
            if response.content_type == "application/json":
                result = await response.json()
            else:
                result = {"text": await response.text()}
            return response.status, result

    async def test_unprotected_endpoint(self):
        """Test that unprotected endpoints work without session"""
        url = f"{self.base_url}/api/v1/session/list"
        async with self.session.get(url) as response:
            result = await response.json()
            return response.status, result

    async def test_protected_endpoint_without_session(self):
        """Test that protected endpoints fail without session"""
        url = f"{self.base_url}/api/v1/upload_resume/"
        data = aiohttp.FormData()
        data.add_field("file", b"test", filename="test.txt", content_type="text/plain")

        async with self.session.post(url, data=data) as response:
            if response.content_type == "application/json":
                result = await response.json()
            else:
                result = {"text": await response.text()}
            return response.status, result


async def run_comprehensive_test():
    """Run comprehensive test of the session-based system"""

    print("🧪 Session-Based LLM Configuration Test Suite")
    print("=" * 60)

    async with SessionBasedAPITester() as tester:

        # Test 1: Test unprotected endpoint (should work)
        print("\n1️⃣ Testing unprotected endpoint (no session required)")
        status, result = await tester.test_unprotected_endpoint()
        print(f"   Status: {status}")
        if status == 200:
            print(f"   ✅ Success: Found {result.get('total', 0)} sessions")
        else:
            print(f"   ❌ Failed: {result}")

        # Test 2: Test protected endpoint without session (should fail)
        print("\n2️⃣ Testing protected endpoint without session (should fail)")
        status, result = await tester.test_protected_endpoint_without_session()
        print(f"   Status: {status}")
        if status == 401:
            print(f"   ✅ Correctly blocked: {result.get('message', 'Access denied')}")
        else:
            print(f"   ❌ Unexpected result: {result}")

        # Test 3: Test LLM configuration (using Ollama as example)
        print("\n3️⃣ Testing LLM configuration")
        llm_test_config = {
            "provider": "ollama",
            "model_name": "llama3:8b",
            "base_url": "http://localhost:11434",
            "temperature": 0.7,
            "max_tokens": 100,
            "test_prompt": "Hello! Please respond to confirm the connection.",
        }

        status, result = await tester.test_llm_config(llm_test_config)
        print(f"   Status: {status}")
        if status == 200 and result.get("success"):
            print(f"   ✅ LLM test successful")
            print(f"   📊 Latency: {result.get('latency_ms', 0):.1f}ms")

            # Test 4: Create session
            print("\n4️⃣ Creating session with LLM configuration")
            llm_config = {
                "provider": "ollama",
                "model_name": "llama3:8b",
                "base_url": "http://localhost:11434",
                "temperature": 0.7,
                "max_tokens": 1000,
            }

            status, result = await tester.create_session(llm_config)
            print(f"   Status: {status}")
            if status == 200:
                session_id = result.get("session_id")
                print(f"   ✅ Session created: {session_id}")
                print(f"   📅 Expires: {result.get('expires_at')}")

                # Test 5: Validate session
                print("\n5️⃣ Validating session")
                status, result = await tester.validate_session()
                print(f"   Status: {status}")
                if status == 200 and result.get("valid"):
                    print(f"   ✅ Session is valid")
                    print(
                        f"   🤖 Provider: {result.get('llm_config', {}).get('provider')}"
                    )

                    # Test 6: Upload resume with session
                    print("\n6️⃣ Testing resume upload with session")
                    status, result = await tester.upload_resume_with_session(
                        "test_resume.txt"
                    )
                    print(f"   Status: {status}")
                    if status == 200:
                        print(f"   ✅ Resume upload successful")
                        if "resume_id" in result:
                            print(f"   📄 Resume ID: {result['resume_id']}")
                        if "session_id" in result:
                            print(
                                f"   🔗 Associated with session: {result['session_id']}"
                            )
                    else:
                        print(f"   ❌ Upload failed: {result}")
                else:
                    print(f"   ❌ Session validation failed: {result}")
            else:
                print(f"   ❌ Session creation failed: {result}")
        else:
            print(f"   ⚠️ LLM test failed (this is expected if Ollama is not running)")
            print(f"   📝 Result: {result}")

            # Test with a different provider or mock
            print("\n4️⃣ Testing session creation with mock LLM config")
            mock_llm_config = {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": "test-key",
                "temperature": 0.7,
                "max_tokens": 1000,
            }

            status, result = await tester.create_session(mock_llm_config)
            print(f"   Status: {status}")
            print(f"   Result: {result}")

    print("\n🎉 Test Suite Complete!")
    print("=" * 60)
    print("\n📋 What to check manually:")
    print("1. Open frontend at http://localhost:3000 or http://localhost:5173")
    print("2. Try to configure LLM (should work)")
    print("3. Try to upload resume without configuring LLM first (should be blocked)")
    print("4. Configure LLM, then upload resume (should work)")
    print("5. Check that subsequent API calls don't require LLM config")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
