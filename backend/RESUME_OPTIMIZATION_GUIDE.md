# Enhanced Resume Optimization Endpoint

## 🚀 Overview

The `/optimize_resume/` endpoint has been enhanced to use AI/LLM providers for intelligent resume optimization based on job descriptions. It now provides:

- **Smart Skills Enhancement**: Adds relevant skills from job descriptions
- **Content Reframing**: Improves summaries and experience descriptions
- **Keyword Optimization**: Incorporates important terms naturally
- **Multiple LLM Support**: Works with Ollama, OpenAI, Claude, and Gemini
- **Fallback Protection**: Uses keyword matching if LLM fails

## 🔧 API Usage

### Endpoint
```
POST /optimize_resume/
```

### Request Body
```json
{
  "parsed": {
    "personal_details": {...},
    "summary": "Your current summary...",
    "skills": "Python, JavaScript, React...",
    "experience": "Your work experience...",
    "education": "Your education..."
  },
  "jd": "Full job description text here...",
  "provider_name": "ollama",
  "provider_config": {
    "model": "gemma3n:e4b",
    "url": "http://localhost:11434"
  },
  "optimization_goals": [
    "ats_optimization",
    "keyword_matching",
    "skills_enhancement"
  ]
}
```

### Response
```json
{
  "success": true,
  "optimized_resume": {
    "personal_details": {...},
    "summary": "Enhanced summary with job-relevant keywords...",
    "skills": "Enhanced skills including relevant technologies...",
    "experience": "Your work experience...",
    "education": "Your education...",
    "optimization_metadata": {
      "job_description_analyzed": true,
      "optimization_timestamp": "2025-07-25T10:30:00",
      "sections_optimized": ["skills", "summary"],
      "optimization_goals": ["ats_optimization", "keyword_matching"],
      "model_used": "gemma3n:e4b"
    }
  },
  "provider_used": "ollama",
  "optimization_goals": ["ats_optimization", "keyword_matching"]
}
```

## 🎯 Provider Configurations

### Ollama (Default)
```json
{
  "provider_name": "ollama",
  "provider_config": {
    "model": "gemma3n:e4b",
    "url": "http://localhost:11434"
  }
}
```

### OpenAI
```json
{
  "provider_name": "openai",
  "provider_config": {
    "model": "gpt-3.5-turbo",
    "api_key": "your-openai-api-key"
  }
}
```

### Claude
```json
{
  "provider_name": "claude",
  "provider_config": {
    "model": "claude-3-opus-20240229",
    "api_key": "your-claude-api-key"
  }
}
```

### Gemini
```json
{
  "provider_name": "gemini",
  "provider_config": {
    "model": "gemini-pro",
    "api_key": "your-gemini-api-key"
  }
}
```

## 🎨 Optimization Goals

Available optimization goals:
- **`ats_optimization`**: Optimize for Applicant Tracking Systems
- **`keyword_matching`**: Match job description keywords
- **`skills_enhancement`**: Add relevant skills
- **`content_improvement`**: Improve content quality
- **`experience_enhancement`**: Enhance experience descriptions

## 🔍 What Gets Optimized

### 1. Skills Section
- Adds relevant technical skills from job description
- Prioritizes job-relevant skills
- Uses terminology consistent with job posting
- Maintains truthfulness and credibility

### 2. Summary/Objective
- Emphasizes relevant experience
- Incorporates important keywords naturally
- Shows clear value proposition
- Maintains professional tone

### 3. Experience Suggestions
- Provides suggestions for reframing achievements
- Recommends metrics and quantifications
- Suggests keywords to incorporate
- Identifies skills to emphasize

## 🛡️ Fallback Mechanism

If LLM optimization fails, the system automatically falls back to:
- Simple keyword extraction and matching
- Adding relevant technical terms to skills
- Basic enhancement with common industry keywords

## 🧪 Testing

Run the test script to verify functionality:
```bash
cd backend
python test_optimization.py
```

## 📝 Example Usage

### Frontend Integration
```javascript
const optimizeResume = async (resumeData, jobDescription) => {
  const response = await fetch('/api/v1/resume/optimize_resume/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      parsed: resumeData,
      jd: jobDescription,
      provider_name: 'ollama',
      provider_config: {
        model: 'gemma3n:e4b',
        url: 'http://localhost:11434'
      },
      optimization_goals: [
        'ats_optimization',
        'keyword_matching',
        'skills_enhancement'
      ]
    })
  });
  
  const result = await response.json();
  return result.optimized_resume;
};
```

### Python Client
```python
import requests

def optimize_resume(resume_data, job_description):
    response = requests.post(
        'http://localhost:8000/api/v1/resume/optimize_resume/',
        json={
            'parsed': resume_data,
            'jd': job_description,
            'provider_name': 'ollama',
            'provider_config': {
                'model': 'gemma3n:e4b',
                'url': 'http://localhost:11434'
            },
            'optimization_goals': [
                'ats_optimization',
                'keyword_matching'
            ]
        }
    )
    return response.json()
```

## 🚨 Error Handling

The endpoint includes comprehensive error handling:
- Invalid provider names return 400 with valid options
- LLM failures automatically trigger fallback optimization
- Configuration errors are logged and reported
- Network issues are handled gracefully

## 🔧 Requirements

- **Ollama**: Ensure Ollama is running on localhost:11434
- **OpenAI**: Valid API key required
- **Claude**: Valid Anthropic API key required  
- **Gemini**: Valid Google AI API key required

The enhanced optimization system provides intelligent, context-aware resume improvements that significantly increase job match rates while maintaining accuracy and truthfulness.
