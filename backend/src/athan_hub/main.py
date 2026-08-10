from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core import pin_auth
from .core.config import get_settings
from .core.logging import configure_logging
from .db.migrations import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Athan Hub", version="1.0.0", openapi_url="/api/openapi.json", lifespan=lifespan)
configure_logging()
app.include_router(router)

settings = get_settings()
app.mount("/backgrounds", StaticFiles(directory=settings.background_dir, check_dir=False), name="backgrounds")


@app.middleware("http")
async def pin_protect_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    if pin_auth.is_protected_host(host, settings):
        if request.url.path in {"/api/pin/status", "/api/pin/verify"}:
            return await call_next(request)
        if not pin_auth.is_pin_valid(request, settings):
            return JSONResponse({"detail": "PIN_REQUIRED"}, status_code=401)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response
