#!/usr/bin/env python3
"""
Test script for the enhanced resume optimization functionality.
Run this to test the optimize_resume endpoint improvements.
"""

import asyncio
import json
from app.services.jd_optimizer import optimize_resume_for_jd

# Sample resume data
sample_resume = {
    "personal_details": {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "555-0123",
        "location": "San Francisco, CA",
    },
    "summary": "Experienced software engineer with expertise in web development and problem solving.",
    "skills": "Python, JavaScript, HTML, CSS, SQL, Git",
    "experience": "Software Engineer at TechCorp (2021-2023): Developed web applications using Python and JavaScript. Built REST APIs and managed databases.",
    "education": "Bachelor of Science in Computer Science, University of California (2017-2021)",
}

# Sample job description
sample_jd = """
Senior Full Stack Developer
Location: San Francisco, CA

We are seeking a Senior Full Stack Developer to join our dynamic team. The ideal candidate will have:

Required Skills:
- 3+ years of experience with Python and JavaScript
- Experience with React.js and Node.js
- Strong knowledge of RESTful APIs and microservices architecture
- Experience with cloud platforms (AWS, Azure, or GCP)
- Database experience with PostgreSQL or MongoDB
- Experience with Docker and containerization
- Knowledge of CI/CD pipelines
- Agile development experience

Responsibilities:
- Design and develop scalable web applications
- Collaborate with cross-functional teams
- Implement best practices for code quality and testing
- Mentor junior developers
- Participate in technical decision making

Preferred Skills:
- Experience with Kubernetes
- Knowledge of machine learning frameworks
- Experience with data visualization tools
- Leadership experience
- Strong communication skills

Company Culture:
We value innovation, collaboration, and continuous learning. Our team works in an agile environment with modern tools and technologies.
"""


async def test_optimization():
    """Test the enhanced resume optimization"""
    print("🚀 Testing Enhanced Resume Optimization")
    print("=" * 50)

    try:
        # Test with Ollama (default)
        print("📋 Testing with Ollama provider...")
        ollama_result = await optimize_resume_for_jd(
            parsed=sample_resume.copy(),
            jd=sample_jd,
            provider_name="ollama",
            provider_config={"model": "gemma3n:e4b", "url": "http://localhost:11434"},
            optimization_goals=[
                "ats_optimization",
                "keyword_matching",
                "skills_enhancement",
            ],
        )

        print("✅ Ollama optimization completed!")
        print(f"📊 Metadata: {ollama_result.get('optimization_metadata', {})}")

        if "skills" in ollama_result:
            print(f"🔧 Enhanced Skills: {ollama_result['skills'][:200]}...")

        print("\n" + "=" * 50)

        # Test fallback optimization
        print("📋 Testing fallback optimization...")
        fallback_result = await optimize_resume_for_jd(
            parsed=sample_resume.copy(),
            jd=sample_jd,
            provider_name="invalid_provider",  # This will trigger fallback
        )

        print("✅ Fallback optimization completed!")
        print(f"📊 Metadata: {fallback_result.get('optimization_metadata', {})}")

        return True

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False


def test_api_format():
    """Test the expected API request format"""
    print("\n🌐 API Request Format Example")
    print("=" * 50)

    api_request = {
        "parsed": sample_resume,
        "jd": sample_jd,
        "provider_name": "ollama",
        "provider_config": {"model": "gemma3n:e4b", "url": "http://localhost:11434"},
        "optimization_goals": [
            "ats_optimization",
            "keyword_matching",
            "skills_enhancement",
            "content_improvement",
        ],
    }

    print("📝 Sample API Request:")
    print(json.dumps(api_request, indent=2)[:500] + "...")

    print("\n📋 Available Providers:")
    providers = ["ollama", "openai", "claude", "gemini"]
    for provider in providers:
        print(f"  • {provider}")

    print("\n🎯 Available Optimization Goals:")
    goals = [
        "ats_optimization",
        "keyword_matching",
        "skills_enhancement",
        "content_improvement",
        "experience_enhancement",
    ]
    for goal in goals:
        print(f"  • {goal}")


if __name__ == "__main__":
    print("🔧 Resume Optimization Test Suite")
    print("=" * 50)

    # Test API format first
    test_api_format()

    # Test optimization
    try:
        success = asyncio.run(test_optimization())
        if success:
            print("\n✅ All tests completed successfully!")
            print("\n💡 Next steps:")
            print("  1. Start your backend server")
            print("  2. Test the /optimize_resume/ endpoint")
            print("  3. Ensure your LLM provider (Ollama) is running")
        else:
            print("\n❌ Some tests failed. Check the logs above.")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        print("\n🔍 Common issues:")
        print("  • Ollama not running (if using ollama provider)")
        print("  • Missing API keys (for OpenAI, Claude, Gemini)")
        print("  • Network connectivity issues")
