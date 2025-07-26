# Session-Based Resume API Updates

## Overview
Updated the resume API endpoints to handle session values from headers and use previously configured LLM configurations from the session instead of requiring LLM config in each request.

## Key Changes Made

### 1. Session Middleware Integration
- The session middleware already extracts `session_id` from headers (`X-Session-ID`, `Authorization: Bearer`, or query params)
- LLM configuration is automatically validated and made available through the middleware
- All protected endpoints now require valid session with LLM configuration

### 2. Updated Resume API Endpoints

#### `/upload_resume/` (POST)
- **Already updated** - Uses session-based approach
- Gets `session_id` and `llm_config` from middleware
- Associates uploaded resume with session
- Stores resume with session-specific ID

#### `/resume_sections/` (GET)
- **Updated** - Now requires session ID from headers
- Retrieves latest resume from current session
- Returns resume data with session metadata

#### `/resume_sections/` (PATCH)
- **Updated** - Now uses session-based approach
- Updates resume sections for the latest resume in session
- Includes audit logging with session information

#### `/optimize_resume/` (POST)
- **Completely updated** - Removed manual LLM config parameters
- Now uses LLM configuration from session
- Gets provider settings from session's LLM config
- Includes comprehensive error handling and logging

#### `/generate_resume/` (POST)
- **Updated** - Enhanced to work with session data
- Can use provided parsed data or automatically get latest resume from session
- Includes session-based audit logging

### 3. New Session-Aware Endpoints

#### `/session/info/` (GET)
- Returns current session information
- Shows LLM configuration details
- Lists resumes and conversations in session
- Provides session status and timing info

#### `/session/resumes/` (GET)
- Lists all resumes in current session
- Shows basic metadata for each resume
- Indicates which sections are available

#### `/session/resume/{resume_id}` (GET)
- Retrieves specific resume by ID from current session
- Validates resume belongs to current session
- Returns full resume data

## Header Requirements

All API endpoints now expect one of these headers:

```
X-Session-ID: <session_id>
```
or
```
Authorization: Bearer <session_id>
```

## Session Configuration Flow

1. **Test LLM Config**: `POST /api/v1/session/test-config`
2. **Create Session**: `POST /api/v1/session/create` with LLM config
3. **Use APIs**: All resume APIs use session ID from headers
4. **Session automatically provides LLM config** to endpoints

## Benefits

1. **Centralized Configuration**: LLM settings configured once per session
2. **Security**: No API keys in request bodies
3. **Session Persistence**: Resume data tied to sessions
4. **Audit Trail**: All actions logged with session context
5. **Multi-Resume Support**: Multiple resumes per session
6. **Simplified API**: No need to provide LLM config in each request

## Backward Compatibility

- Old direct LLM config approach removed from `/optimize_resume/`
- All endpoints now require valid session
- Session middleware handles validation automatically

## Error Handling

- Returns appropriate HTTP status codes
- Detailed error messages for missing sessions
- Comprehensive audit logging for all operations
- Graceful handling of missing session data

## Usage Example

```bash
# 1. Create session with LLM config
curl -X POST "http://localhost:8000/api/v1/session/create" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_config": {
      "provider": "ollama",
      "model_name": "gemma2:2b",
      "base_url": "http://localhost:11434",
      "temperature": 0.7
    }
  }'

# Response: {"session_id": "abc-123", ...}

# 2. Upload resume with session
curl -X POST "http://localhost:8000/api/v1/upload_resume/" \
  -H "X-Session-ID: abc-123" \
  -F "file=@resume.pdf"

# 3. Optimize resume (no LLM config needed)
curl -X POST "http://localhost:8000/api/v1/optimize_resume/" \
  -H "X-Session-ID: abc-123" \
  -H "Content-Type: application/json" \
  -d '{
    "parsed": {...},
    "jd": "Job description text",
    "optimization_goals": ["ats_optimization", "keyword_matching"]
  }'
```

## Files Modified

- `/backend/app/api/v1/resume.py` - Main resume API endpoints
- Session middleware already in place at `/backend/app/middleware/session_middleware.py`
- Session manager already available at `/backend/app/services/session_manager.py`
