# -*- coding: utf-8 -*-
import io
import sys
import locale
from typing import cast
from sqlalchemy import text

sys.stdout = cast(io.TextIOWrapper, sys.stdout)
sys.stderr = cast(io.TextIOWrapper, sys.stderr)
# Set default encoding to UTF-8
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Set Korean locale
try:
    locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Korean_Korea.UTF-8")
    except:
        pass

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_redoc_html,
)

from sqlalchemy.orm import Session
import uvicorn
import logging

from config import settings
from database import get_db, init_database, test_connection
from routers import (
    auth,
    plans,
    payments,
    payment_methods,
    subscriptions,
    users,
    terms,
    notices,
    inquiries,
    upload,
    admin,
    oauth,
    faq,
)
from routers.clubs import (
    base_router as clubs_router,
    notices_router as clubs_notices_router,
    regulations_router as club_regulations_router,
    members_router as clubs_members_router,
    fees_router as clubs_fees_router,
)
from routers.meetings import (
    base_router,
    participants_router,
    workflow_router,
    settlement_router,
    teams_router,
    scores_router,
    meeting_score_router,
    expenses_router,
    rounds_router,
    socials_router,
)
from utils.csrf_protection import CSRFProtectionMiddleware

# from utils.rate_limiter import RateLimiterMiddleware  # 개발 환경에서는 비활성화

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TeeupLink API",
    description="골프 모임 관리 플랫폼 API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    default_response_class=JSONResponse,
    openapi_tags=[
        {"name": "auth", "description": "인증 관련 API"},
        {"name": "users", "description": "사용자 관리 API"},
        {"name": "clubs", "description": "골프 클럽 관리 API"},
        {"name": "meetings", "description": "모임 관리 API"},
        {"name": "scores", "description": "점수 관리 API"},
        {"name": "payments", "description": "결제 관리 API"},
    ],
)
from starlette.middleware.base import BaseHTTPMiddleware


class RawRequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()

        request_dict = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
            "headers": dict(request.headers),
            "body": body.decode("utf-8", errors="ignore"),
        }

        print("==== INCOMING REQUEST ====")
        print(request_dict)
        print("==========================")

        async def receive():
            return {"type": "http.request", "body": body}

        request._receive = receive  # 🔥 핵심

        return await call_next(request)


app.add_middleware(RawRequestLogMiddleware)

# CORS 설정 - 가장 먼저 추가해야 함 (미들웨어는 역순으로 실행됨)
# 개발 환경을 위한 localhost 기본값 (하드코딩된 도메인 제거)
default_dev_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3005",
    "http://localhost:3006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
    "http://127.0.0.1:3005",
    "http://127.0.0.1:3006",
]
# CORS_ORIGINS 환경 변수 필수 (프로덕션 도메인은 환경 변수로 설정)
allowed_origins = (
    settings.cors_origins_list if settings.cors_origins_list else default_dev_origins
)
logger.info(f"CORS origins: {allowed_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# CSRF 보호 미들웨어 추가 (CORS 이후)
app.add_middleware(CSRFProtectionMiddleware)

# # 한국어 로케일 및 인코딩 설정
# @app.middleware("http")
# async def add_korean_locale_header(request: Request, call_next):
#     response = await call_next(request)
#     response.headers["Content-Type"] = "application/json; charset=utf-8"
#     return response

# API 라우터 등록
app.include_router(auth.router, prefix="/api/v1")
app.include_router(oauth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

# 클럽 관련 라우터 - 기능별로 통합됨
app.include_router(clubs_router, prefix="/api/v1")  # /clubs - 기본 CRUD
app.include_router(clubs_notices_router, prefix="/api/v1")  # /clubs - 공지사항
app.include_router(club_regulations_router, prefix="/api/v1")  # /clubs - 규정
app.include_router(clubs_members_router, prefix="/api/v1")  # /clubs - 멤버 관리
app.include_router(clubs_fees_router, prefix="/api/v1")  # /clubs - 회비 관리

# 모임 관련 라우터 - 기능별로 통합됨
app.include_router(base_router, prefix="/api/v1")  # /meetings - 기본 CRUD
app.include_router(participants_router, prefix="/api/v1")  # /meetings - 참가자 관리
app.include_router(workflow_router, prefix="/api/v1")  # /meetings - 워크플로우
app.include_router(settlement_router, prefix="/api/v1")  # /meetings - 정산
app.include_router(teams_router, prefix="/api/v1")  # /teams - 팀 관리
app.include_router(scores_router, prefix="/api/v1")  # /scores - 점수 관리
app.include_router(
    meeting_score_router, prefix="/api/v1"
)  # /meetings - 모임 스코어 관리
app.include_router(expenses_router, prefix="/api/v1")  # /expenses - 비용 관리
app.include_router(rounds_router, prefix="/api/v1")  # /rounds - 라운딩 전용
app.include_router(socials_router, prefix="/api/v1")  # /socials - 소셜 모임 전용
app.include_router(plans.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1/payments")
app.include_router(payment_methods.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(terms.router, prefix="/api/v1")
app.include_router(notices.router, prefix="/api/v1")
app.include_router(inquiries.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(faq.admin_router, prefix="/api/v1")
app.include_router(faq.client_router, prefix="/api/v1")

# 보안 미들웨어 설정
# Rate Limiting (개발 환경에서는 비활성화)
# app.add_middleware(RateLimiterMiddleware, requests_per_minute=120, requests_per_hour=2000)

# CSRF Protection (API 제외) - 임시 비활성화
# app.add_middleware(CSRFProtectionMiddleware, secret_key=settings.jwt_secret_key)


@app.get("/")
async def root():
    return {"message": "TeeupLink API Server"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        # Simple query to test database connection
        db.execute(statement=text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting TeeupLink API Server...")

    # Initialize database
    if init_database():
        logger.info("Database initialization successful")
    else:
        logger.error("Database initialization failed")

    # Test database connection
    if test_connection():
        logger.info("Database connection test successful")
    else:
        logger.error("Database connection test failed")


@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="FastAPI - Swagger UI"
    )


@app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
def redoc_ui():
    return get_redoc_html(openapi_url="/openapi.json", title="FastAPI - ReDoc")


@app.get("/openapi.json", include_in_schema=False)
def openapi():
    return app.openapi()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
