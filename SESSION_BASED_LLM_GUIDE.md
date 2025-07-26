# Session-Based LLM Configuration Guide

## Overview

The Resume ATS application now uses a **session-based LLM configuration system** that acts as middleware similar to authentication. This means:

- ✅ **LLM configuration is required before accessing any resume-related APIs**
- ✅ **Frontend only needs to pass session ID, not LLM config repeatedly**
- ✅ **LLM credentials are stored securely server-side**
- ✅ **Automatic session management and cleanup**

## How It Works

### 1. Prerequisites Flow
```
Frontend → Test LLM Config → Create Session → Store Session ID → Use Other APIs
```

### 2. Middleware Protection
The `SessionMiddleware` automatically:
- Validates session ID in request headers
- Injects LLM configuration into request context
- Blocks access to protected endpoints without valid session
- Provides session information to endpoints

### 3. Protected Endpoints
These endpoints **require** a valid session:
- `/api/v1/resume/*`
- `/api/v1/conversation/*`
- `/api/v1/section-optimization/*`
- `/api/v1/job-analysis/*`
- `/api/v1/feedback/*`
- `/api/v1/version-management/*`
- `/api/v1/export/*`

These endpoints are **always accessible** (no session required):
- `/api/v1/session/*` (session management)
- `/api/v1/monitoring/*`
- `/api/v1/security/*`
- `/docs`, `/redoc`, `/openapi.json`

## API Workflow

### Step 1: Test LLM Configuration

**Endpoint:** `POST /api/v1/session/test-config`

```json
{
  "provider": "openai",
  "model_name": "gpt-3.5-turbo",
  "api_key": "your-api-key",
  "temperature": 0.7,
  "max_tokens": 1000,
  "test_prompt": "Hello, please respond to test the configuration"
}
```

**Response:**
```json
{
  "success": true,
  "response_text": "Configuration test successful!",
  "latency_ms": 250.5,
  "provider_info": {
    "provider": "openai",
    "model": "gpt-3.5-turbo"
  }
}
```

### Step 2: Create Session

**Endpoint:** `POST /api/v1/session/create`

```json
{
  "llm_config": {
    "provider": "openai",
    "model_name": "gpt-3.5-turbo",
    "api_key": "your-api-key",
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "device_id": "optional-device-id",
  "session_duration_hours": 24,
  "metadata": {
    "user_agent": "MyApp/1.0",
    "platform": "web"
  }
}
```

**Response:**
```json
{
  "session_id": "a628397a-5263-4919-a1e0-de0d455059c7",
  "status": "created",
  "expires_at": "2025-07-26T14:54:12.686593Z",
  "message": "Session created successfully"
}
```

### Step 3: Use Session ID in All Requests

Add the session ID to **all subsequent requests** using one of these methods:

#### Option 1: X-Session-ID Header (Recommended)
```
X-Session-ID: a628397a-5263-4919-a1e0-de0d455059c7
```

#### Option 2: Authorization Header
```
Authorization: Bearer a628397a-5263-4919-a1e0-de0d455059c7
```

#### Option 3: Query Parameter (Not recommended for security)
```
?session_id=a628397a-5263-4919-a1e0-de0d455059c7
```

### Step 4: Use Resume APIs Normally

**Example:** Upload Resume (now session-based)

**Endpoint:** `POST /api/v1/upload_resume/`

**Headers:**
```
X-Session-ID: a628397a-5263-4919-a1e0-de0d455059c7
Content-Type: multipart/form-data
```

**Body:** (form-data)
```
file: [resume.pdf]
```

**Response:**
```json
{
  "personal_details": {...},
  "education": [...],
  "work_experience": [...],
  "projects": [...],
  "skills": [...],
  "resume_id": "resume_a628397a_resume",
  "session_id": "a628397a-5263-4919-a1e0-de0d455059c7"
}
```

## Frontend Implementation Guide

### 1. React/JavaScript Example

```javascript
class ResumeATSClient {
  constructor() {
    this.sessionId = localStorage.getItem('resume_ats_session');
    this.baseURL = 'http://localhost:8000/api/v1';
  }

  // Step 1: Test LLM Configuration
  async testLLMConfig(config) {
    const response = await fetch(`${this.baseURL}/session/test-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config)
    });
    return response.json();
  }

  // Step 2: Create Session
  async createSession(llmConfig, options = {}) {
    const response = await fetch(`${this.baseURL}/session/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        llm_config: llmConfig,
        device_id: options.deviceId || this.getDeviceId(),
        session_duration_hours: options.durationHours || 24,
        metadata: options.metadata || {}
      })
    });
    
    const result = await response.json();
    if (result.session_id) {
      this.sessionId = result.session_id;
      localStorage.setItem('resume_ats_session', this.sessionId);
    }
    return result;
  }

  // Helper: Get headers with session ID
  getHeaders(additionalHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...additionalHeaders
    };
    
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }
    
    return headers;
  }

  // Step 3: Upload Resume (session-based)
  async uploadResume(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseURL}/upload_resume/`, {
      method: 'POST',
      headers: {
        'X-Session-ID': this.sessionId // Only session ID needed!
      },
      body: formData
    });
    
    return response.json();
  }

  // All other APIs work the same way - just add session header
  async startConversation(resumeId, userId, section) {
    const response = await fetch(`${this.baseURL}/conversation/start`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        resume_id: resumeId,
        user_id: userId,
        section: section
        // No llm_provider or llm_config needed anymore!
      })
    });
    
    return response.json();
  }

  // Session Management
  async validateSession() {
    if (!this.sessionId) return { valid: false };
    
    const response = await fetch(`${this.baseURL}/session/validate/${this.sessionId}`);
    return response.json();
  }

  async getCurrentSession() {
    const response = await fetch(`${this.baseURL}/session/current`, {
      headers: this.getHeaders()
    });
    return response.json();
  }

  async terminateSession() {
    if (!this.sessionId) return;
    
    await fetch(`${this.baseURL}/session/${this.sessionId}`, {
      method: 'DELETE'
    });
    
    this.sessionId = null;
    localStorage.removeItem('resume_ats_session');
  }

  getDeviceId() {
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId = 'device_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('device_id', deviceId);
    }
    return deviceId;
  }
}

// Usage Example
const client = new ResumeATSClient();

// 1. Configure LLM
const llmConfig = {
  provider: "openai",
  model_name: "gpt-3.5-turbo",
  api_key: "your-api-key",
  temperature: 0.7
};

// Test configuration
const testResult = await client.testLLMConfig(llmConfig);
if (testResult.success) {
  // Create session
  const sessionResult = await client.createSession(llmConfig);
  console.log('Session created:', sessionResult.session_id);
  
  // Now use other APIs normally
  const uploadResult = await client.uploadResume(file);
  console.log('Resume uploaded:', uploadResult.resume_id);
}
```

### 2. Error Handling

The middleware returns specific error responses for missing or invalid sessions:

```javascript
// Handle session errors
async function handleApiCall(apiCall) {
  try {
    const result = await apiCall();
    return result;
  } catch (error) {
    if (error.status === 401) {
      // Session invalid or missing
      if (error.error === 'missing_session') {
        // Redirect to LLM configuration
        showLLMConfigurationScreen();
      } else if (error.error === 'invalid_session') {
        // Session expired, create new one
        await recreateSession();
      }
    }
    throw error;
  }
}
```

## Session Management APIs

### Validate Session
```
GET /api/v1/session/validate/{session_id}
```

### Get Current Session
```
GET /api/v1/session/current
Headers: X-Session-ID: {session_id}
```

### Get Session Data
```
GET /api/v1/session/{session_id}/data
```

### List Sessions
```
GET /api/v1/session/list?device_id={optional}
```

### Terminate Session
```
DELETE /api/v1/session/{session_id}
```

### Cleanup Expired Sessions
```
POST /api/v1/session/cleanup
```

## Benefits

### For Frontend Developers
- ✅ **Simplified API calls** - no need to pass LLM config repeatedly
- ✅ **Better UX** - configure once, use everywhere
- ✅ **Session persistence** - works across browser sessions
- ✅ **Clear error handling** - 401 errors indicate session issues

### For Security
- ✅ **Credentials isolation** - API keys stored server-side only
- ✅ **Session control** - automatic expiration and cleanup
- ✅ **Device tracking** - associate sessions with devices
- ✅ **Audit trail** - track all session-related activities

### For Backend
- ✅ **Clean architecture** - LLM config injected automatically
- ✅ **Consistent provider usage** - no config parsing in each endpoint
- ✅ **Resource management** - automatic cleanup of expired sessions
- ✅ **Scalability** - sessions can be stored in Redis/database later

## Migration from Old System

### Before (Old Way)
```javascript
// Every API call needed LLM config
await uploadResume(file, "openai", {
  api_key: "key",
  model: "gpt-3.5-turbo"
});

await startConversation(resumeId, "openai", {
  api_key: "key", 
  model: "gpt-3.5-turbo"
});
```

### After (New Way)
```javascript
// Configure once
await createSession(llmConfig);

// Use everywhere
await uploadResume(file); // No LLM config needed!
await startConversation(resumeId); // No LLM config needed!
```

## Configuration Options

### Supported LLM Providers
- `openai` - OpenAI GPT models
- `anthropic` - Claude models  
- `gemini` - Google Gemini models
- `ollama` - Local Ollama models

### Session Configuration
- `session_duration_hours` - 1 to 168 hours (1 week max)
- `device_id` - Optional device tracking
- `metadata` - Custom session metadata

### LLM Configuration Options
- `provider` - Required provider type
- `model_name` - Required model name
- `api_key` - API key (not required for Ollama)
- `base_url` - Custom endpoint URL (for Ollama)
- `temperature` - 0.0 to 2.0
- `max_tokens` - Token limit
- `top_p` - Nucleus sampling
- `frequency_penalty` - Frequency penalty
- `presence_penalty` - Presence penalty
- `additional_params` - Provider-specific parameters
