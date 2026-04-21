# API Content-Type

## Problem

API endpoints return HTML challenge pages instead of JSON error responses when a request is blocked.

## Root Cause

The challenge system doesn't inspect the `Accept` header. It serves the same HTML challenge page regardless of whether the client expects JSON or HTML.

## Solution

1. **Configure your WAF/CDN to return JSON for API paths.** Most platforms support custom block responses per path:
   - Match: path starts with `/api/`
   - Block response: `{"error": "challenge_required", "status": 403}`
   - Content-Type: `application/json`

2. **Use the `Accept` header in your challenge rules.** If the request has `Accept: application/json`, return a JSON response instead of HTML.

3. **At the application level**, add middleware that catches challenge responses and converts them:
   ```python
   @app.middleware("http")
   async def challenge_middleware(request, call_next):
       response = await call_next(request)
       if response.status_code == 403 and "application/json" in request.headers.get("accept", ""):
           return JSONResponse({"error": "challenge_required"}, status_code=403)
       return response
   ```

## Verification

Run: `challenge-validator test <api-url> --suite cors`

The `api_content_type` test should now pass.
