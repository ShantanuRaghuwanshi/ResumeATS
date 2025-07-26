# Session Headers Implementation Guide

This guide explains how session headers are automatically handled in the frontend application.

## Overview

The frontend now automatically includes session headers (`X-Session-ID`) in all API requests except for session management endpoints. This ensures proper session tracking while avoiding circular dependencies during session creation.

## Automatic Header Inclusion

### Standard API Calls

For most API calls, session headers are automatically included when using:

1. **`apiRequest()` function** (from `@/lib/queryClient`)
   ```typescript
   import { apiRequest } from "@/lib/queryClient";
   
   // Session headers automatically included
   const response = await apiRequest("POST", "/resume/analyze", { data });
   ```

2. **`apiUpload()` function** (from `@/lib/queryClient`)
   ```typescript
   import { apiUpload } from "@/lib/queryClient";
   
   // Session headers automatically included
   const response = await apiUpload("/upload_resume/", formData);
   ```

3. **React Query with default queryFn**
   ```typescript
   const { data } = useQuery({
     queryKey: ["resumes", userId],
     // Default queryFn automatically includes session headers
   });
   ```

### Custom Query Functions

For custom `queryFn` implementations, use the `fetchWithSession` utility:

```typescript
import { fetchWithSession } from "@/lib/utils";

const { data } = useQuery({
  queryKey: ["custom-endpoint"],
  queryFn: async () => {
    // Session headers automatically included (except for session APIs)
    const response = await fetchWithSession("/api/v1/custom-endpoint");
    if (!response.ok) throw new Error("Request failed");
    return response.json();
  }
});
```

## Session API Exclusions

Session headers are **NOT** included for these endpoints to prevent circular dependencies:

- `/api/v1/session`
- `/api/v1/session/`
- `/api/v1/session/test-config`
- `/api/v1/session/create`
- `/api/v1/session/list`

## Implementation Details

### Session Header Detection

```typescript
// Session data stored in localStorage
const sessionData = localStorage.getItem('resume-ats-session');

// Header format when session is valid
{ 'X-Session-ID': sessionId }
```

### URL Pattern Matching

The system automatically detects session API URLs and excludes them:

```typescript
const sessionApiPaths = [
  '/api/v1/session',
  '/api/v1/session/',
  '/api/v1/session/test-config',
  '/api/v1/session/create',
  '/api/v1/session/list'
];

// Checks if URL matches any session API pattern
const isSessionApi = sessionApiPaths.some(path => 
  urlPath === path || urlPath.startsWith(path + '/')
);
```

## Best Practices

1. **Use provided utilities**: Always use `apiRequest`, `apiUpload`, or `fetchWithSession` instead of raw `fetch` calls
2. **No manual headers**: Don't manually add session headers - they're handled automatically
3. **Error handling**: The system gracefully handles invalid or expired sessions
4. **Development**: Session logic is consistent across all environments

## Migration from Manual Headers

If you have existing code with manual session headers:

```typescript
// OLD: Manual session headers
const sessionId = getSessionId();
const response = await fetch("/api/endpoint", {
  headers: {
    'X-Session-ID': sessionId,
    'Content-Type': 'application/json'
  }
});

// NEW: Automatic session headers
const response = await fetchWithSession("/api/endpoint", {
  headers: {
    'Content-Type': 'application/json'
  }
});
```

## Troubleshooting

### Session Not Being Sent

1. Check if the endpoint is a session API (excluded by design)
2. Verify session data exists in localStorage: `resume-ats-session`
3. Ensure session hasn't expired
4. Confirm you're using the provided utilities (`apiRequest`, `fetchWithSession`, etc.)

### Circular Dependencies

If you see session-related circular dependencies:
1. Ensure session creation endpoints don't include session headers
2. Check that you're not manually adding headers to session APIs
3. Verify the session API path exclusion list is up to date
