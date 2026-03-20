import os
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FRONTEND_BASE_URL: str = ""
    API_VERSION: str = ""
    # Database Configuration
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 80
    DB_POOL_TIMEOUT: int = 60
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # JWT Configuration
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120
    JWT_WEB_REFRESH_EXPIRE_DAYS: int = 7
    JWT_APP_REFRESH_EXPIRE_DAYS: int = 365

    # Environment
    ENVIRONMENT: str = "development"

    # Server Configuration
    BACKEND_PORT: str = ""  # 백엔드 서버 포트 (환경 변수 필수)

    # Database Auto Creation
    AUTO_CREATE_TABLES: Optional[bool] = (
        None  # None이면 개발 환경에서만 자동 생성, True/False로 명시적 제어 가능
    )

    # CORS
    CORS_ORIGINS: str = ""

    # Auth Cookies
    AUTH_ACCESS_COOKIE_NAME: str = "teeup_access_token"
    AUTH_REFRESH_COOKIE_NAME: str = "teeup_refresh_token"
    AUTH_COOKIE_DOMAIN: str = ""
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_SECURE: Optional[bool] = None

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list"""
        if not self.CORS_ORIGINS:
            return []
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # Loadtest Internal OAuth Mock
    ENABLE_LOADTEST_AUTH_MOCK: bool = False
    LOADTEST_AUTH_MOCK_ALLOWED_IPS: str = "127.0.0.1,::1"

    @property
    def auth_cookie_secure(self) -> bool:
        if self.AUTH_COOKIE_SECURE is not None:
            return self.AUTH_COOKIE_SECURE
        return self.ENVIRONMENT.lower() != "development"

    @property
    def loadtest_auth_mock_allowed_ips_list(self) -> List[str]:
        """Convert loadtest oauth mock allowed IPs to list"""
        if not self.LOADTEST_AUTH_MOCK_ALLOWED_IPS:
            return []
        return [
            ip.strip() for ip in self.LOADTEST_AUTH_MOCK_ALLOWED_IPS.split(",")
            if ip.strip()
        ]

    # File Upload
    upload_dir: str = "../../uploads"  # 프로젝트 루트의 uploads 폴더
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # Toss Payments Configuration
    TOSS_PAYMENTS_CLIENT_KEY: str = ""
    TOSS_PAYMENTS_SECRET_KEY: str = ""
    TOSS_PAYMENTS_BASE_URL: str = "https://api.tosspayments.com/v1"

    # Google OAuth Configuration
    GOOGLE_WEB_CLIENT_ID: str = ""
    GOOGLE_WEB_REDIRECT_URI: str = ""  # OAuth 리다이렉트 URI (환경 변수 필수)

    GOOGLE_ANDROID_CLIENT_ID: str = ""
    GOOGLE_ANDROID_REDIRECT_URI: str = ""  # OAuth 리다이렉트 URI (환경 변수 필수)

    GOOGLE_IOS_CLIENT_ID: str = ""
    GOOGLE_IOS_REDIRECT_URI: str = ""  # OAuth 리다이렉트 URI (환경 변수 필수)
    GOOGLE_IOS_REDIRECT_URI: str = ""  # OAuth 리다이렉트 URI (환경 변수 필수)

    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_DRIVE_CLIENT_ID: str = ""
    GOOGLE_DRIVE_REDIRECT_URI: str = (
        ""  # 드라이브 전용 토큰 발급 콜백(프런트) (환경 변수 필수)
    )
    GOOGLE_DRIVE_CLUB_FOLDER_ID: str = (
        ""  # 클럽 등록 파일 업로드 대상 구글 드라이브 폴더 ID
    )
    GOOGLE_DRIVE_NOTICE_FOLDER_ID: str = (
        ""  # 공지사항 첨부파일 업로드 대상 구글 드라이브 폴더 ID
    )
    # OAuth 토큰 저장 경로(절대경로): 백엔드 폴더의 token.json
    GOOGLE_TOKEN_FILE: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "token.json"))

    # Email Configuration (SMTP)
    MAIL_USERNAME: str = ""  # Gmail 주소
    MAIL_PASSWORD: str = ""  # Gmail App Password (OAuth2 대신 사용)
    MAIL_FROM: str = ""  # 발신자 이메일 (기본값: MAIL_USERNAME)
    MAIL_SERVER: str = "smtp.gmail.com"  # SMTP 서버 주소
    MAIL_PORT: int = 587  # SMTP 포트 (587: STARTTLS, 465: SSL/TLS)
    MAIL_STARTTLS: bool = True  # STARTTLS 사용 여부
    MAIL_SSL_TLS: bool = False  # SSL/TLS 사용 여부 (MAIL_PORT가 465일 때 True)
    FRONTEND_BASE_URL: str = ""  # 프론트엔드 기본 URL (환경 변수 필수)

    # 공공 API
    ADMIN_REGION_API_URL: str = ""
    DATA_GO_KR_API_KEY: str = ""

    # Firebase Push
    FIREBASE_SERVICE_ACCOUNT_FILE: str = ""

    @property
    def database_url(self) -> str:
        """SQLAlchemy database URL"""
        return self.DATABASE_URL

    @property
    def frontend_base_url(self) -> str:
        """프론트엔드 기본 URL (환경 변수 필수, 하드코딩된 도메인 제거)"""
        if not self.FRONTEND_BASE_URL:
            raise ValueError("FRONTEND_BASE_URL 환경 변수가 설정되지 않았습니다.")
        return self.FRONTEND_BASE_URL

    @property
    def backend_port(self) -> int:
        """백엔드 서버 포트 (환경 변수 필수)"""
        if not self.BACKEND_PORT:
            raise ValueError("BACKEND_PORT 환경 변수가 설정되지 않았습니다.")
        try:
            port = int(self.BACKEND_PORT)
            if port <= 0:
                raise ValueError(
                    f"BACKEND_PORT가 유효하지 않습니다: {self.BACKEND_PORT}")
            return port
        except ValueError as e:
            if "유효하지 않습니다" in str(e):
                raise
            raise ValueError(f"BACKEND_PORT가 유효하지 않습니다: {self.BACKEND_PORT}")

    class Config:
        # 프로젝트 루트의 .env 파일을 절대경로로 지정 (실행 위치 무관)
        env_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".env"))
        case_sensitive = False
        extra = "ignore"  # 추가 필드 허용


# Global settings instance
settings = Settings()
