## Breakage Journal (Lab 5)

### Breakage 1: Removed CORS completely
- What I did: Commented out `app.add_middleware(CORSMiddleware, ...)` in `main.py`.
- Console: Access to fetch at 'http://localhost:8000/courses' has been blocked by CORS policy.
- Network: `/courses` request red (CORS error), POST preflight gets 405 Method Not Allowed.
- Cause: FastAPI did not return Access-Control-Allow-Origin headers.
- How I found it: Algorithm step 2 & 4.

### Breakage 2: Trailing slash in allow_origins
- What I did: Set `allow_origins=["http://localhost:3000/"]`.
- Console: Response to preflight request doesn't pass access control check.
- Network: OPTIONS request returned status 400.
- Cause: Origin matching requires exact scheme + host + port without trailing slash.
- How I found it: Algorithm step 3.

### Breakage 3: Removed allow_methods
- What I did: Removed `allow_methods=["*"]`.
- Console: Response to preflight request doesn't pass access control check: It does not have HTTP ok status.
- Network: OPTIONS preflight returned 400 (Disallowed CORS method).
- Cause: Only GET is allowed by default; POST was rejected during preflight.
- How I found it: Algorithm step 4.

### Breakage 4: Origin mismatch (127.0.0.1 vs localhost)
- What I did: Accessed frontend via `http://127.0.0.1:3000/filter`.
- Console: Blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
- Network: Request red (CORS error).
- Cause: Browser treats `127.0.0.1` and `localhost` as distinct origins.
- How I found it: Algorithm step 3.

### Breakage 5: Python KeyError in backend
- What I did: Replaced `p["offset"]` with `p["ofset"]` in `main.py`.
- Console: No 'Access-Control-Allow-Origin' header is present on the requested resource.
- Network: Status 500 Internal Server Error in backend logs.
- Cause: Unhandled Python exceptions result in HTTP 500 without CORS headers attached.
- How I found it: Algorithm step 5 (Checking backend terminal logs).