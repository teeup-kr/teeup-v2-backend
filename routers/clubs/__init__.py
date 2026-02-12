# 클럽 관련 라우터 패키지
# 모든 클럽 관련 API를 한 곳에서 관리

# 기본 클럽 관리
from .base import router as base_router

# 클럽 공지사항 관리
from .notices import router as notices_router

# 클럽 규정 관리
from .regulations import router as regulations_router

# 클럽 멤버 관리
from .members import router as members_router

# 클럽 회비 관리
from .fees import router as fees_router

# 클럽 통계
from .stats import router as stats_router

__all__ = [
    "base_router",
    "notices_router",
    "regulations_router",
    "members_router",
    "fees_router",
    "stats_router"
]

