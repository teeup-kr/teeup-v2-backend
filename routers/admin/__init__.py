"""
백오피스 API 라우터 패키지
- auth, search, admins: 인증, 검색, 관리자 CRUD
- users, dashboard, upload, profile: 사용자, 대시보드, 업로드, 프로필
- payments, terms, notices, inquiries, notifications, scores: 결제, 약관, 공지, 문의, 알림, 스코어
- clubs, meetings: 클럽, 모임
"""
from fastapi import APIRouter, Depends

from .deps import get_admin_user, require_super_admin, require_roles
from models import AdminRole

from .auth import router as auth_router
from .search import router as search_router
from .admins import router as admins_router
from .users import router as users_router
from .dashboard import router as dashboard_router
from .upload import router as upload_router
from .profile import router as profile_router
from .payments import router as payments_router
from .terms import router as terms_router
from .notices import router as notices_router
from .inquiries import router as inquiries_router
from .notifications import router as notifications_router
from .scores import router as scores_router
from .clubs import router as clubs_router
from .meetings import router as meetings_router
from .faq import router as faq_router

router = APIRouter(prefix="/admin", tags=["admin"])

# 인증/프로필/설정: 모든 역할 접근 가능
router.include_router(auth_router)
router.include_router(profile_router)
router.include_router(search_router)

# 관리자 CRUD: 슈퍼어드민만
router.include_router(admins_router, dependencies=[Depends(require_super_admin)])

# 분야별 라우터: 역할별 접근 제어
router.include_router(users_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.USER_ADMIN))])
router.include_router(clubs_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.CLUB_ADMIN))])
router.include_router(meetings_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.MEETING_ADMIN))])
router.include_router(notices_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN))])
router.include_router(faq_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN))])
router.include_router(terms_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.CONTENT_ADMIN))])
router.include_router(inquiries_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.SUPPORT_ADMIN))])

# 대시보드/업로드/알림: 모든 역할 접근 가능
router.include_router(dashboard_router)
router.include_router(upload_router)
router.include_router(notifications_router)

# 스코어: 모임 관리 권한 필요
router.include_router(scores_router, dependencies=[Depends(require_roles(AdminRole.SUPER_ADMIN, AdminRole.MEETING_ADMIN))])

# 결제: 슈퍼어드민만 (추후 PAYMENT_ADMIN 추가 가능)
router.include_router(payments_router, dependencies=[Depends(require_super_admin)])

__all__ = ["router", "get_admin_user"]
