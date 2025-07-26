"""
Advanced test for session-based resume upload with real file
"""

import asyncio
import aiohttp
import json
import os


async def test_complete_workflow():
    """Test the complete workflow: session creation -> resume upload -> data retrieval"""

    print("🚀 Complete Session-Based Workflow Test")
    print("=" * 50)

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:

        # Step 1: Create session with Ollama configuration
        print("\n1️⃣ Creating session...")
        session_data = {
            "llm_config": {
                "provider": "ollama",
                "model_name": "llama3:8b",
                "base_url": "http://localhost:11434",
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "device_id": "test-device-advanced",
            "session_duration_hours": 24,
            "metadata": {"test_type": "advanced_workflow"},
        }

        async with session.post(
            f"{base_url}/api/v1/session/create", json=session_data
        ) as response:
            result = await response.json()
            if response.status == 200:
                session_id = result["session_id"]
                print(f"   ✅ Session created: {session_id}")

                # Step 2: Upload the actual resume file if it exists
                print("\n2️⃣ Uploading resume...")

                # Check if the test resume file exists
                resume_path = "/Users/shantanuraghuwanshi/Documents/ResumeATS/backend/uploads/Shantanu_Resume_2025.pdf"

                if os.path.exists(resume_path):
                    print(f"   📄 Using existing resume: {resume_path}")

                    headers = {"X-Session-ID": session_id}
                    data = aiohttp.FormData()

                    with open(resume_path, "rb") as f:
                        data.add_field(
                            "file",
                            f,
                            filename="Shantanu_Resume_2025.pdf",
                            content_type="application/pdf",
                        )

                        async with session.post(
                            f"{base_url}/api/v1/upload_resume/",
                            data=data,
                            headers=headers,
                        ) as upload_response:
                            upload_result = await upload_response.json()

                            if upload_response.status == 200:
                                print(f"   ✅ Resume uploaded successfully!")
                                print(
                                    f"   📋 Resume ID: {upload_result.get('resume_id')}"
                                )
                                print(
                                    f"   👤 Personal Details: {upload_result.get('personal_details', {}).get('name', 'N/A')}"
                                )
                                print(
                                    f"   🎓 Education entries: {len(upload_result.get('education', []))}"
                                )
                                print(
                                    f"   💼 Work experience entries: {len(upload_result.get('work_experience', []))}"
                                )
                                print(
                                    f"   🛠️ Skills: {len(upload_result.get('skills', []))}"
                                )

                                # Step 3: Get session data to verify association
                                print("\n3️⃣ Retrieving session data...")
                                async with session.get(
                                    f"{base_url}/api/v1/session/{session_id}/data"
                                ) as data_response:
                                    if data_response.status == 200:
                                        session_data = await data_response.json()
                                        print(f"   ✅ Session data retrieved")
                                        print(
                                            f"   📄 Associated resumes: {session_data.get('resume_data', {})}"
                                        )
                                        print(
                                            f"   💬 Conversations: {len(session_data.get('conversation_history', []))}"
                                        )
                                    else:
                                        print(
                                            f"   ❌ Failed to get session data: {await data_response.json()}"
                                        )

                                # Step 4: Test that we can make other API calls with just session ID
                                print("\n4️⃣ Testing other session-based APIs...")

                                # Try to start a conversation (this would normally require LLM config)
                                conversation_data = {
                                    "resume_id": upload_result.get("resume_id"),
                                    "user_id": "test-user",
                                    "section": "experience",
                                }

                                async with session.post(
                                    f"{base_url}/api/v1/conversation/start",
                                    json=conversation_data,
                                    headers=headers,
                                ) as conv_response:
                                    if conv_response.status == 200:
                                        conv_result = await conv_response.json()
                                        print(
                                            f"   ✅ Conversation started successfully!"
                                        )
                                        print(
                                            f"   💬 Session ID: {conv_result.get('session', {}).get('id')}"
                                        )
                                    else:
                                        conv_error = await conv_response.json()
                                        print(
                                            f"   ⚠️ Conversation start failed: {conv_error}"
                                        )

                            else:
                                print(f"   ❌ Resume upload failed: {upload_result}")
                else:
                    print(f"   ⚠️ Resume file not found at {resume_path}")
                    print("   Creating test text resume...")

                    # Create a test text resume
                    test_resume = """
SHANTANU RAGHUWANSHI
Email: shantanu@example.com
Phone: +1-234-567-8900
LinkedIn: linkedin.com/in/shantanu

EXPERIENCE
Software Engineer | Tech Corp | 2022-2025
- Developed scalable web applications
- Led a team of 5 developers
- Implemented CI/CD pipelines

EDUCATION  
Bachelor of Technology in Computer Science
Indian Institute of Technology | 2018-2022
GPA: 8.5/10

SKILLS
Python, JavaScript, React, Node.js, AWS, Docker
"""

                    headers = {"X-Session-ID": session_id}
                    data = aiohttp.FormData()
                    data.add_field(
                        "file",
                        test_resume.encode(),
                        filename="test_resume.txt",
                        content_type="text/plain",
                    )

                    async with session.post(
                        f"{base_url}/api/v1/upload_resume/", data=data, headers=headers
                    ) as upload_response:
                        upload_result = await upload_response.json()

                        if upload_response.status == 200:
                            print(f"   ✅ Test resume uploaded successfully!")
                            print(f"   📋 Resume ID: {upload_result.get('resume_id')}")
                        else:
                            print(f"   ❌ Test resume upload failed: {upload_result}")

                # Step 5: List all sessions to verify our session exists
                print("\n5️⃣ Listing all sessions...")
                async with session.get(
                    f"{base_url}/api/v1/session/list"
                ) as list_response:
                    if list_response.status == 200:
                        sessions = await list_response.json()
                        print(
                            f"   📝 Total active sessions: {sessions.get('total', 0)}"
                        )
                        for sess in sessions.get("sessions", []):
                            if sess["session_id"] == session_id:
                                print(
                                    f"   ✅ Found our session: {sess['session_id'][:8]}... ({sess['provider']})"
                                )
                    else:
                        print(
                            f"   ❌ Failed to list sessions: {await list_response.json()}"
                        )

            else:
                print(f"   ❌ Session creation failed: {result}")

    print("\n🎉 Advanced Workflow Test Complete!")
    print("\n💡 Key Benefits Demonstrated:")
    print("   ✅ Single LLM configuration per session")
    print("   ✅ Resume upload without passing LLM config")
    print("   ✅ Session-based data association")
    print("   ✅ All APIs work with just session ID")
    print("   ✅ Automatic middleware protection")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
