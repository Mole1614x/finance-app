"""Bounded demo API throttling; Redis is required when configured."""
import hashlib
import os
import time
from collections import OrderedDict
from threading import Lock

from redis import Redis
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

WINDOW = 60
LUA = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""

class RateLimiter:
    def __init__(self, redis_url=None, max_keys=4096):
        self.redis = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2) if redis_url else None
        self.entries = OrderedDict()
        self.lock = Lock()
        self.max_keys = max_keys

    def allow(self, identity, limit, timestamp=None):
        bucket = int(time.time() if timestamp is None else timestamp) // WINDOW
        key = "arth:rate:" + hashlib.sha256(identity.encode()).hexdigest() + ":" + str(bucket)
        if self.redis:
            return self.redis.eval(LUA, 1, key, WINDOW*2) <= limit
        with self.lock:
            while self.entries and next(iter(self.entries.values()))[0] < bucket:
                self.entries.popitem(last=False)
            if key not in self.entries and len(self.entries) >= self.max_keys:
                return False
            _, count = self.entries.get(key, (bucket, 0))
            self.entries[key] = (bucket, count+1)
            return count < limit

limiter = RateLimiter(os.getenv("ARTH_RATE_LIMIT_REDIS_URL"))
AUTH_ROUTES = {"/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/otp/request",
               "/api/v1/auth/otp/verify", "/api/v1/auth/refresh"}
MONEY_ROUTES = {"/api/v1/accounts/initialize", "/api/v1/accounts/move",
                "/api/v1/payments/send", "/api/v1/services/purchase"}

async def security_middleware(request, call_next):
    path = request.url.path.rstrip("/")
    response = None
    if request.method == "POST" and path in AUTH_ROUTES | MONEY_ROUTES:
        # Do not trust forwarded IP headers; run Uvicorn with proxy headers disabled.
        peer = request.client.host if request.client else "unknown"
        group = "auth" if path in AUTH_ROUTES else "money"
        limit = int(os.getenv("ARTH_AUTH_RATE_LIMIT", "60")) if group == "auth" else 120
        try:
            allowed = await run_in_threadpool(limiter.allow, peer+":"+group, limit)
            if not allowed:
                response = JSONResponse({"detail": "Too many demo requests."}, status_code=429,
                                        headers={"Retry-After": str(WINDOW)})
        except RedisError:
            response = JSONResponse({"detail": "Demo rate limiter unavailable."}, status_code=503)
    if response is None:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response
