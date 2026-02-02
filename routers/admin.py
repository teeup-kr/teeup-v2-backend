"""
백오피스 전용 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import secrets
from datetime import datetime, timedelta, timezone
from utils.datetime_utils import get_kst_now
from pydantic import BaseModel
import threading

from database import get_db
from models import Admin, User, Meeting, ClubMembership, Club, Terms, UserStatus, ClubStatus, ClubRole, ClubRegion, Sido, Gungu, Provider
from schemas import MembershipStatus, TermsType
from schemas import UserResponse, MessageResponse, PaginatedResponse, AdminResponse, AdminCreate, AdminUpdate, AdminPasswordUpdate
import schemas
from utils.jwt_auth import jwt_auth
from utils import generate_id
from utils.display_id_generator import generate_club_display_id
from utils.region import validate_gungu_codes

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# 일회용 토큰 추적을 위한 메모리 캐시 (스레드 안전)
_used_tokens = set()
_token_lock = threading.Lock()


def mark_token_as_used(token_jti: str):
    """토큰을 사용됨으로 표시"""
    with _token_lock:
        _used_tokens.add(token_jti)


def is_token_used(token_jti: str) -> bool:
    """토큰이 이미 사용되었는지 확인"""
    with _token_lock:
        return token_jti in _used_tokens


# JWT 인증을 위한 보안 스키마
security = HTTPBearer()


# 어드민 로그인 요청/응답 모델
class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def verify_admin_credentials(email: str, password: str, db: Session) -> Admin:
    """관리자 인증 확인"""
    try:
        admin = db.query(Admin).filter(Admin.email == email, Admin.deleted_at.is_(None)).first()

        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 올바르지 않습니다")

        # 비밀번호 확인 (SHA256 해시 비교)
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if admin.password != password_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 올바르지 않습니다")

        # 관리자 상태 확인
        if admin.status == UserStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="삭제된 관리자 계정입니다")

        if admin.status == UserStatus.DEACTIVATED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 관리자 계정입니다")

        return admin

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 인증 중 오류: {str(e)}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"인증 처리 중 오류가 발생했습니다: {str(e)}")


def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                   db: Session = Depends(get_db)) -> dict:
    """JWT 토큰으로 어드민 사용자 조회"""
    try:
        # JWT 토큰 검증
        token = credentials.credentials
        logger.info(f"Admin auth - Token received: {token[:20]}...")

        payload = jwt_auth.verify_token(token, "access")
        logger.info(f"Admin auth - Token payload: {payload}")

        user_id = payload.get("id")
        logger.info(f"Admin auth - User ID from token: {user_id}")

        if not user_id:
            logger.error("Admin auth - No user_id in token payload")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 사용자 정보가 없습니다")

        # 관리자 조회
        admin = db.query(Admin).filter(Admin.id == user_id, Admin.deleted_at.is_(None)).first()

        logger.info(f"Admin auth - Admin found: {admin is not None}")

        if not admin:
            logger.error(f"Admin auth - Admin not found for id: {user_id}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="관리자를 찾을 수 없습니다")

        # 관리자 상태 확인
        if admin.status == UserStatus.DELETED:
            logger.error(f"Admin auth - Admin status is DELETED")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="삭제된 관리자 계정입니다")

        if admin.status == UserStatus.DEACTIVATED:
            logger.error(f"Admin auth - Admin status is DEACTIVATED")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 관리자 계정입니다")

        # 관리자 정보를 딕셔너리로 변환 (type 포함 - PermissionChecker.check_admin_permission용)
        user_data = {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "status": admin.status.value if admin.status else None,
            "type": "admin",
        }

        logger.info(f"Admin auth - Returning user data: {user_data}")
        return user_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"어드민 사용자 인증 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 검증 중 오류가 발생했습니다")


# 기존 Basic Auth 기반 get_admin_session 함수는 제거됨
# 이제 JWT 기반 get_admin_user 함수를 사용


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLoginRequest, db: Session = Depends(get_db)):
    """백오피스 로그인 - JWT 기반"""
    logger.info(f"Admin login attempt: {login_data.email}")
    try:
        # 관리자 인증
        admin = verify_admin_credentials(login_data.email, login_data.password, db)

        # JWT 토큰 생성 (type은 access로 유지 - verify_token에서 필요)
        token_payload = {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
        }
        access_token = jwt_auth.create_access_token(token_payload)
        refresh_token = jwt_auth.create_refresh_token(token_payload)

        return AdminLoginResponse(access_token=access_token,
                                  refresh_token=refresh_token,
                                  token_type="bearer",
                                  user={
                                      "id": admin.id,
                                      "email": admin.email,
                                      "name": admin.name,
                                      "type": "admin"
                                  })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"백오피스 로그인 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="로그인 처리 중 오류가 발생했습니다")


@router.post("/generate-client-token")
async def generate_client_token(current_user: dict = Depends(get_admin_user), db: Session = Depends(get_db)):
    """클라이언트 페이지 접근을 위한 일회용 임시 토큰 생성"""
    try:
        # 고유 토큰 ID 생성 (일회용 추적용)
        import string
        token_jti = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

        # 어드민 사용자 정보로 임시 토큰 생성 (5분 유효)
        user_data = {
            "id": current_user["id"],
            "email": current_user["email"],
            "nickname": current_user.get("name"),  # Admin은 name 사용
            "role": "ADMIN",
            "admin_view": True,  # 어드민 뷰 플래그
            "type": "admin_temp",  # 임시 어드민 토큰 타입
            "jti": token_jti  # 일회용 추적용 고유 ID
        }

        # 5분 유효기간의 임시 토큰 생성
        temp_token = jwt_auth.create_access_token(user_data, expires_delta=timedelta(minutes=5))

        logger.info(f"임시 클라이언트 토큰 생성 완료 - user_id: {current_user['id']}, jti: {token_jti}")

        return {
            "temp_token": temp_token,
            "expires_in": 300  # 5분 (초 단위)
        }

    except Exception as e:
        logger.error(f"임시 클라이언트 토큰 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="임시 토큰 생성 중 오류가 발생했습니다")


@router.post("/logout")
async def admin_logout(current_user: dict = Depends(get_admin_user), db: Session = Depends(get_db)):
    """백오피스 로그아웃 - JWT 토큰 무효화"""
    try:
        # JWT 토큰 무효화는 클라이언트에서 처리
        # 서버에서는 로그아웃 로그만 기록
        logger.info(f"Admin logout: {current_user['email']}")
        return {"message": "로그아웃되었습니다"}

    except Exception as e:
        logger.error(f"어드민 로그아웃 중 오류: {str(e)}")
        return {"message": "로그아웃되었습니다"}


@router.get("/me")
async def get_current_admin(current_user: dict = Depends(get_admin_user)):
    """현재 관리자 정보 조회"""
    try:
        logger.info(f"관리자 정보 조회 요청 - user_id: {current_user.get('id')}")
        result = {
            "id": current_user["id"],
            "email": current_user["email"],
            "name": current_user.get("name", ""),
            "nickname": current_user.get("name", ""),  # 하위 호환: nickname = name
            "role": "ADMIN",
            "status": current_user.get("status", "ACTIVE")
        }
        logger.info(f"관리자 정보 조회 성공: {result}")
        return result
    except Exception as e:
        logger.error(f"관리자 정보 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="관리자 정보 조회 중 오류가 발생했습니다")


@router.get("/settings")
async def get_admin_settings(current_user: dict = Depends(get_admin_user)):
    """관리자 설정 조회"""
    try:
        logger.info(f"관리자 설정 조회 요청 - user_id: {current_user.get('id')}")

        # 기본 설정 반환 (실제로는 DB에서 조회해야 함)
        settings = {
            "theme": "light",
            "language": "ko",
            "notifications": {
                "email": True,
                "push": True
            },
            "dashboard": {
                "refresh_interval": 30,
                "default_view": "grid"
            }
        }

        logger.info(f"관리자 설정 조회 성공: {settings}")
        return settings
    except Exception as e:
        logger.error(f"관리자 설정 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="관리자 설정 조회 중 오류가 발생했습니다")


# ==========================
# 헤더 전역 검색 API
# ==========================


@router.get("/search")
async def global_search(
        q: str = Query(..., min_length=1, max_length=100, description="검색어"),
        limit: int = Query(5, ge=1, le=20, description="카테고리별 최대 결과 수"),
        types: Optional[str] = Query("users,clubs,meetings,admins",
                                     description="검색 대상 (쉼표 구분: users,clubs,meetings,admins)"),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """
    백오피스 헤더 전역 검색
    - 사용자, 클럽, 모임, 관리자를 한 번에 검색
    - 각 카테고리별 limit개씩 반환
    """
    if not q or not q.strip():
        return {"users": [], "clubs": [], "meetings": [], "admins": []}

    q = q.strip()
    pattern = f"%{q}%"
    result = {"users": [], "clubs": [], "meetings": [], "admins": []}
    target_types = [t.strip().lower() for t in types.split(",") if t.strip()]

    try:
        # 사용자 검색 (email, nickname, realname)
        if "users" in target_types:
            users = (db.query(User).filter(
                User.deleted_at.is_(None),
                ~User.nickname.like("guest_%"),
                ~User.email.like("%@guest.local"),
            ).filter((User.email.ilike(pattern))
                     | (User.nickname.ilike(pattern))
                     | (User.realname.ilike(pattern))).order_by(User.created_at.desc()).limit(limit).all())
            result["users"] = [{
                "id": u.id,
                "type": "user",
                "email": u.email,
                "nickname": u.nickname,
                "realname": getattr(u, "realname", None),
                "link": f"/users/{u.id}",
            } for u in users]

        # 클럽 검색 (name, description)
        if "clubs" in target_types:
            clubs = (db.query(Club).filter(
                Club.deleted_at.is_(None)).filter((Club.name.ilike(pattern))
                                                  | ((Club.description.isnot(None))
                                                     & (Club.description.ilike(pattern)))).order_by(
                                                         Club.created_at.desc()).limit(limit).all())
            result["clubs"] = [{
                "id": c.id,
                "display_id": c.display_id,
                "type": "club",
                "name": c.name,
                "status": c.status.value if c.status else None,
                "link": f"/clubs/{c.display_id or c.id}",
            } for c in clubs]

        # 모임 검색 (name)
        if "meetings" in target_types:
            meetings = (db.query(Meeting).filter(Meeting.club_id.isnot(None)).filter(
                Meeting.name.ilike(pattern)).order_by(Meeting.created_at.desc()).limit(limit).all())
            result["meetings"] = [{
                "id": m.id,
                "type": "meeting",
                "name": m.name,
                "club_id": m.club_id,
                "meeting_time": m.meeting_time.isoformat() if m.meeting_time else None,
                "status": m.status,
                "link": f"/meetings/{m.id}",
            } for m in meetings]

        # 관리자 검색 (email, name)
        if "admins" in target_types:
            admins = (db.query(Admin).filter(
                Admin.deleted_at.is_(None)).filter((Admin.email.ilike(pattern)) | (Admin.name.ilike(pattern))).order_by(
                    Admin.created_at.desc()).limit(limit).all())
            result["admins"] = [{
                "id": a.id,
                "type": "admin",
                "email": a.email,
                "name": a.name,
                "link": f"/admins/{a.id}",
            } for a in admins]

        return result

    except Exception as e:
        logger.error(f"전역 검색 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="검색 중 오류가 발생했습니다",
        )


# ==========================
# 관리자(Admin) 관리 API
# ==========================


@router.get("/admins", response_model=PaginatedResponse)
async def get_admin_list(
        page: int = Query(1, ge=1, description="페이지"),
        limit: int = Query(10, ge=1, le=100, description="페이지당 개수"),
        search: Optional[str] = Query(None, description="이메일/이름 검색"),
        status_filter: Optional[str] = Query(None, description="상태 필터 (ACTIVE, DEACTIVATED, DELETED)"),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자 목록 조회 (페이지네이션)"""
    try:
        query = db.query(Admin).filter(Admin.deleted_at.is_(None))

        if search:
            search_pattern = f"%{search}%"
            query = query.filter((Admin.email.ilike(search_pattern)) | (Admin.name.ilike(search_pattern)))

        if status_filter:
            try:
                status_enum = UserStatus[status_filter]
                query = query.filter(Admin.status == status_enum)
            except KeyError:
                pass

        total = query.count()
        admins = query.order_by(Admin.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        data = [
            AdminResponse(
                id=a.id,
                email=a.email,
                name=a.name,
                profile_image=a.profile_image,
                phone_number=a.phone_number,
                provider=a.provider.value if a.provider else None,
                status=a.status.value if a.status else None,
                created_at=a.created_at,
                updated_at=a.updated_at,
            ) for a in admins
        ]

        return {
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"관리자 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="관리자 목록 조회 중 오류가 발생했습니다")


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(
        admin_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자 상세 조회"""
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
    return AdminResponse(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        profile_image=admin.profile_image,
        phone_number=admin.phone_number,
        provider=admin.provider.value if admin.provider else None,
        status=admin.status.value if admin.status else None,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
    )


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
        data: AdminCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """새 관리자 생성"""
    import hashlib
    existing = db.query(Admin).filter(Admin.email == data.email, Admin.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 존재하는 이메일입니다")
    password_hash = hashlib.sha256(data.password.encode()).hexdigest()
    admin = Admin(
        email=data.email,
        password=password_hash,
        name=data.name,
        phone_number=data.phone_number,
        profile_image=data.profile_image,
        provider=Provider.LOCAL,
        status=UserStatus.ACTIVE,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return AdminResponse(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        profile_image=admin.profile_image,
        phone_number=admin.phone_number,
        provider=admin.provider.value if admin.provider else None,
        status=admin.status.value if admin.status else None,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
    )


@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
        admin_id: int,
        data: AdminUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자 정보 수정"""
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
    if data.name is not None:
        admin.name = data.name
    if data.phone_number is not None:
        admin.phone_number = data.phone_number
    if data.profile_image is not None:
        admin.profile_image = data.profile_image
    if data.status is not None:
        try:
            admin.status = UserStatus[data.status]
        except KeyError:
            pass
    admin.updated_at = get_kst_now()
    db.commit()
    db.refresh(admin)
    return AdminResponse(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        profile_image=admin.profile_image,
        phone_number=admin.phone_number,
        provider=admin.provider.value if admin.provider else None,
        status=admin.status.value if admin.status else None,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
    )


@router.put("/admins/{admin_id}/password")
async def update_admin_password_by_admin(
        admin_id: int,
        data: AdminPasswordUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """다른 관리자의 비밀번호 변경 (관리자 전용)"""
    import hashlib
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
    admin.password = hashlib.sha256(data.new_password.encode()).hexdigest()
    admin.updated_at = get_kst_now()
    db.commit()
    return {"message": "비밀번호가 변경되었습니다", "success": True}


@router.delete("/admins/{admin_id}")
async def delete_admin(
        admin_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자 삭제 (soft delete)"""
    if admin_id == current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자기 자신은 삭제할 수 없습니다")
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
    admin.deleted_at = get_kst_now()
    admin.status = UserStatus.DELETED
    db.commit()
    return {"message": "관리자가 삭제되었습니다", "success": True}


# ==========================
# 클럽 관리 API
# ==========================

# ==========================
# 클럽 관리 API
# ==========================


@router.get("/clubs")
def admin_list_clubs(page: int = 1,
                     limit: int = 10,
                     status_filter: str | None = None,
                     search: str | None = None,
                     current_user: dict = Depends(get_admin_user),
                     db: Session = Depends(get_db)):
    """관리자용 클럽 목록 조회"""
    try:
        # 관리자 페이지에서는 삭제된 클럽도 조회 (deleted_at 필드로 구분)
        query = db.query(Club)
        if status_filter:
            try:
                status_enum = ClubStatus[status_filter]
                query = query.filter(Club.status == status_enum)
            except Exception:
                pass
        if search:
            like = f"%{search}%"
            query = query.filter((Club.name.ilike(like)) | (Club.description.ilike(like)))
        total = query.count()
        items = (query.order_by(Club.created_at.desc()).offset((page - 1) * limit).limit(limit).all())
        data = []
        for c in items:
            # 대표자/리더명 계산: LEADER 멤버십의 사용자명 (realname > nickname > email 우선순위)
            leader_name = None
            try:
                leader_membership = (db.query(ClubMembership,
                                              User).join(User, ClubMembership.user_id == User.id).filter(
                                                  ClubMembership.club_id == c.id,
                                                  ClubMembership.role == ClubRole.LEADER).first())
                if leader_membership:
                    _, leader_user = leader_membership
                    leader_name = getattr(leader_user, 'realname', None) or leader_user.nickname or leader_user.email
            except Exception:
                pass

            # 실제 멤버 수 계산 (승인된 멤버만)
            # ACTIVE 또는 APPROVED 상태의 멤버를 카운트 (일부는 APPROVED로 저장될 수 있음)
            from sqlalchemy import or_

            # 모든 멤버십 상태 확인 (디버깅용)
            all_memberships = db.query(ClubMembership).filter(ClubMembership.club_id == c.id).all()

            actual_member_count = db.query(ClubMembership).filter(
                ClubMembership.club_id == c.id,
                or_(
                    ClubMembership.status == MembershipStatus.ACTIVE,
                    ClubMembership.status == "APPROVED"  # 이전에 APPROVED로 저장된 멤버도 포함
                )).count()

            # 디버깅: 예상 멤버수와 실제 멤버 수 비교
            expected_count = getattr(c, 'member_count', None)
            logger.info(f"Club {c.id} ({c.name}): expected={expected_count}, actual={actual_member_count}")
            if all_memberships:
                status_counts = {}
                for m in all_memberships:
                    status_counts[m.status] = status_counts.get(m.status, 0) + 1
                logger.info(f"Club {c.id} membership statuses: {status_counts}")

            data.append({
                "id":
                c.id,
                "display_id":
                getattr(c, 'display_id', None),
                "name":
                c.name,
                "description":
                c.description,
                "type":
                c.type.value if hasattr(c.type, 'value') else str(c.type),
                "member_count":
                actual_member_count,  # 실제 멤버 수 사용
                "location":
                getattr(c, 'location', None),
                "sido_code":
                c.sido_code,
                "gungu_codes":
                [region.gungu_code for region in db.query(ClubRegion).filter(ClubRegion.club_id == c.id).all()],
                "representative_name":
                getattr(c, 'representative_name', None),
                "leader_name":
                leader_name,
                "status":
                c.status.value if hasattr(c.status, 'value') else str(c.status),
                "deleted_at":
                c.deleted_at.isoformat() if c.deleted_at else None,
                "created_at":
                c.created_at,
                "updated_at":
                c.updated_at,
            })
        return {
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        logger.error(f"admin list clubs error: {e}")
        raise HTTPException(status_code=500, detail="클럽 목록 조회 중 오류가 발생했습니다")


@router.get("/users", response_model=PaginatedResponse)
async def get_admin_users(page: int = 1,
                          limit: int = 10,
                          search: Optional[str] = None,
                          role_filter: Optional[str] = None,
                          status_filter: Optional[str] = None,
                          sort_order: Optional[str] = "oldest",
                          db: Session = Depends(get_db),
                          current_user: dict = Depends(get_admin_user)):
    """관리자용 사용자 목록 조회"""
    try:
        offset = (page - 1) * limit

        # 검색 쿼리 구성 (모든 사용자 조회, 게스트 제외)
        # 게스트는 일회성이므로 관리자 페이지에서 제외
        query = db.query(User).filter(
            User.deleted_at.is_(None),
            ~User.email.like('%@guest.local'),  # 게스트 이메일 제외
            ~User.nickname.like('guest_%')  # 게스트 닉네임 제외
        )

        if search:
            # 이메일, 닉네임, 실명, 전화번호로 검색
            search_filter = f"%{search}%"
            query = query.filter((User.email.ilike(search_filter))
                                 | (User.nickname.ilike(search_filter))
                                 | (User.realname.ilike(search_filter))
                                 | (User.phone_number.ilike(search_filter)))

        # role_filter 제거 - User 모델에 role 없음 (Admin 분리됨)
        if status_filter:
            query = query.filter(User.status == status_filter)

        # 총 개수 계산 (검색 조건 포함)
        total_count = query.count()

        # 정렬 처리
        logger.info(f"정렬 옵션: {sort_order}")
        if sort_order == "oldest":
            query = query.order_by(User.created_at.asc())
            logger.info("오래된 가입순으로 정렬")
        else:  # "recent" 또는 기본값 - 최근 가입순이 기본
            query = query.order_by(User.created_at.desc())
            logger.info("최근 가입순으로 정렬 (기본값)")

        # 페이지네이션 적용
        users = query.offset(offset).limit(limit).all()

        # 디버깅: 사용자 상태별 개수 로그
        deleted_users = db.query(User).filter(User.deleted_at.isnot(None)).count()
        logger.info(f"총 사용자 수: {total_count}, 삭제된 사용자 수: {deleted_users}")

        user_responses = []
        for user in users:
            # 사용자의 활성 클럽 멤버십 수 계산
            from models import ClubMembership
            from schemas import MembershipStatus
            club_count = db.query(ClubMembership).filter(ClubMembership.user_id == user.id,
                                                         ClubMembership.status == MembershipStatus.ACTIVE).count()

            user_responses.append(
                UserResponse(id=user.id,
                             email=user.email,
                             realname=getattr(user, 'realname', None),
                             nickname=user.nickname,
                             phone_number=getattr(user, 'phone_number', None),
                             birthdate=getattr(user, 'birthdate', None),
                             gender=getattr(user, 'gender', None),
                             handicap=user.handicap,
                             average_score=user.average_score,
                             provider=getattr(user, 'provider', None),
                             email_verified=getattr(user, 'email_verified', None),
                             status=user.status.value if user.status else None,
                             deactivated_at=getattr(user, 'deactivated_at', None),
                             needs_terms_agreement=getattr(user, 'needs_terms_agreement', None),
                             terms_agreement=getattr(user, 'terms_agreement', None),
                             privacy_policy=getattr(user, 'privacy_policy', None),
                             privacy_collection=getattr(user, 'privacy_collection', None),
                             marketing_consent=getattr(user, 'marketing_consent', None),
                             club_count=club_count,
                             created_at=user.created_at,
                             updated_at=user.updated_at))

        return {
            "data": user_responses,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }

    except Exception as e:
        logger.error(f"관리자 사용자 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 목록 조회 중 오류가 발생했습니다")


@router.get("/users/search")
async def search_users_for_club(q: Optional[str] = None,
                                limit: int = 20,
                                db: Session = Depends(get_db),
                                current_user: dict = Depends(get_admin_user)):
    """클럽 대표자 선택을 위한 사용자 검색"""
    logger.info(f"User search API called - q: {q}, limit: {limit}, current_user: {current_user}")
    try:
        # 검색 쿼리 구성
        query = db.query(User).filter(
            User.deleted_at.is_(None),
            User.status == UserStatus.ACTIVE  # 활성 사용자만
        )

        if q:
            # 이메일, 닉네임, 실명으로 검색
            search_filter = f"%{q}%"
            query = query.filter((User.email.ilike(search_filter))
                                 | (User.nickname.ilike(search_filter))
                                 | (User.realname.ilike(search_filter)))

        # 결과 제한
        users = query.limit(limit).all()

        # 간단한 사용자 정보 반환
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "realname": getattr(user, 'realname', None),
                "phone_number": getattr(user, 'phone_number', None),
                "status": user.status.value if user.status else None
            })

        return {"success": True, "users": user_list, "total": len(user_list)}

    except Exception as e:
        logger.error(f"사용자 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 검색 중 오류가 발생했습니다")


@router.get("/users/create")
async def get_user_create_form_data(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """사용자 생성 페이지에 필요한 데이터 조회"""
    try:
        # 사용자 생성 페이지에 필요한 기본 데이터 반환
        return {
            "success": True,
            "data": {
                "roles": ["USER", "ADMIN"],
                "statuses": ["ACTIVE", "INACTIVE", "SUSPENDED"],
                "providers": ["LOCAL", "GOOGLE", "KAKAO", "NAVER"]
            }
        }
    except Exception as e:
        logger.error(f"사용자 생성 페이지 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터 조회 중 오류가 발생했습니다")


@router.get("/users/create/clubs")
async def get_user_create_clubs_data(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """사용자 생성 시 클럽 목록 조회 (대표자 선택용)"""
    try:
        # 활성 클럽 목록 조회
        clubs = db.query(Club).filter(Club.deleted_at.is_(None),
                                      Club.status == ClubStatus.ACTIVE).order_by(Club.created_at.desc()).all()

        club_list = []
        for club in clubs:
            club_list.append({
                "id": club.id,
                "display_id": club.display_id,
                "name": club.name,
                "status": club.status.value if hasattr(club.status, 'value') else str(club.status)
            })

        return {"success": True, "clubs": club_list, "total": len(club_list)}
    except Exception as e:
        logger.error(f"클럽 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="클럽 목록 조회 중 오류가 발생했습니다")


@router.get("/users/{user_id}")
async def get_admin_user_detail(user_id: int,
                                db: Session = Depends(get_db),
                                current_user: dict = Depends(get_admin_user)):
    """관리자용 사용자 상세 조회"""
    try:
        logger.info(f"관리자 사용자 상세 조회 요청 - user_id: {user_id}, current_user: {current_user.get('id')}")

        # 사용자 조회
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        logger.info(f"사용자 조회 결과: {user is not None}")

        if not user:
            logger.error(f"사용자를 찾을 수 없음 - user_id: {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 사용자 정보 구성
        gender_value = None
        if hasattr(user, 'gender') and user.gender:
            if hasattr(user.gender, 'value'):
                gender_value = user.gender.value
            else:
                gender_value = str(user.gender)

        user_response = UserResponse(id=user.id,
                                     email=user.email,
                                     realname=getattr(user, 'realname', None),
                                     nickname=user.nickname,
                                     phone_number=getattr(user, 'phone_number', None),
                                     birthdate=getattr(user, 'birthdate', None),
                                     gender=gender_value,
                                     handicap=float(user.handicap) if user.handicap else None,
                                     average_score=user.average_score,
                                     provider=user.provider.value if user.provider else None,
                                     email_verified=getattr(user, 'email_verified', None),
                                     status=user.status.value if user.status else None,
                                     deactivated_at=getattr(user, 'deactivated_at', None),
                                     needs_terms_agreement=getattr(user, 'needs_terms_agreement', None),
                                     created_at=user.created_at,
                                     updated_at=user.updated_at)

        return user_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 사용자 상세 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 상세 조회 중 오류가 발생했습니다")


@router.get("/users/{user_id}/clubs")
async def get_user_clubs(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """사용자별 소속 클럽 목록 조회"""
    try:
        from models import Club, ClubMembership, ClubRole
        from schemas import MembershipStatus
        from sqlalchemy import or_

        # 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 사용자의 클럽 멤버십 조회 (ACTIVE와 APPROVED 상태 모두 포함, 삭제되지 않은 클럽만)
        memberships = db.query(ClubMembership, Club).join(Club, ClubMembership.club_id == Club.id).filter(
            ClubMembership.user_id == user_id, Club.deleted_at.is_(None),
            or_(ClubMembership.status == MembershipStatus.ACTIVE, ClubMembership.status == "APPROVED")).all()

        club_data = []
        for membership, club in memberships:
            club_data.append({
                "id":
                club.id,
                "name":
                club.name,
                "type":
                club.type.value if hasattr(club.type, 'value') else str(club.type),
                "description":
                club.description,
                "location":
                club.location,
                "status":
                club.status.value if hasattr(club.status, 'value') else str(club.status),
                "member_role":
                membership.role.value if hasattr(membership.role, 'value') else str(membership.role),
                "joined_at":
                membership.created_at.isoformat() if membership.created_at else None,
                "club_created_at":
                club.created_at.isoformat() if club.created_at else None
            })

        return {"user_id": user_id, "user_name": user.nickname, "total_clubs": len(club_data), "clubs": club_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 클럽 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 클럽 목록 조회 중 오류가 발생했습니다")


@router.get("/users/{user_id}/meetings", response_model=schemas.UserMeetingsResponse)
async def get_user_meetings(user_id: int,
                            page: int = Query(1, ge=1),
                            limit: int = Query(10, ge=1, le=100),
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """사용자별 라운딩/소셜 참가 목록 조회"""
    try:
        from models import Meeting, MeetingParticipant, Club, UserScoreHistory
        from schemas import MeetingType

        # 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 페이지네이션 계산
        offset = (page - 1) * limit

        # 라운딩 모임 조회
        rounding_query = db.query(MeetingParticipant, Meeting,
                                  Club).join(Meeting, MeetingParticipant.meeting_id == Meeting.id).join(
                                      Club,
                                      Meeting.club_id == Club.id).filter(MeetingParticipant.user_id == user_id,
                                                                         Meeting.meeting_type == MeetingType.ROUND,
                                                                         Club.deleted_at.is_(None))

        total_rounding = rounding_query.count()
        from sqlalchemy import func, desc
        rounding_results = rounding_query.order_by(desc(func.coalesce(
            Meeting.meeting_time, Meeting.created_at))).offset(offset).limit(limit).all()

        # 소셜 모임 조회
        social_query = db.query(MeetingParticipant, Meeting,
                                Club).join(Meeting, MeetingParticipant.meeting_id == Meeting.id).join(
                                    Club, Meeting.club_id == Club.id).filter(MeetingParticipant.user_id == user_id,
                                                                             Meeting.meeting_type == MeetingType.SOCIAL,
                                                                             Club.deleted_at.is_(None))

        total_social = social_query.count()
        social_results = social_query.order_by(desc(func.coalesce(
            Meeting.meeting_time, Meeting.created_at))).offset(offset).limit(limit).all()

        # 스코어 정보 조회 (라운딩만)
        rounding_meeting_ids = [meeting.id for _, meeting, _ in rounding_results]
        score_histories = {}
        if rounding_meeting_ids:
            scores = db.query(UserScoreHistory).filter(UserScoreHistory.user_id == user_id,
                                                       UserScoreHistory.meeting_id.in_(rounding_meeting_ids)).all()
            for score in scores:
                score_histories[score.meeting_id] = score

        # 라운딩 모임 데이터 구성
        rounding_meetings = []
        for participant, meeting, club in rounding_results:
            score_history = score_histories.get(meeting.id)
            rounding_meetings.append(
                schemas.UserMeetingItem(
                    meeting_id=meeting.id,
                    meeting_name=meeting.name,
                    club_name=club.name,
                    meeting_time=meeting.meeting_time,
                    status=meeting.status,
                    participant_status=participant.status,
                    participant_role=participant.role,
                    joined_at=participant.created_at,
                    rounding_completed_at=meeting.rounding_completed_at,
                    has_score=score_history is not None,
                    gross_score=score_history.gross_score if score_history else None,
                    net_score=float(score_history.net_score) if score_history and score_history.net_score else None))

        # 소셜 모임 데이터 구성
        social_meetings = []
        for participant, meeting, club in social_results:
            social_meetings.append(
                schemas.UserMeetingItem(meeting_id=meeting.id,
                                        meeting_name=meeting.name,
                                        club_name=club.name,
                                        meeting_time=meeting.meeting_time,
                                        status=meeting.status,
                                        participant_status=participant.status,
                                        participant_role=participant.role,
                                        joined_at=participant.created_at,
                                        rounding_completed_at=None,
                                        has_score=False,
                                        gross_score=None,
                                        net_score=None))

        return schemas.UserMeetingsResponse(rounding_meetings=rounding_meetings,
                                            social_meetings=social_meetings,
                                            total_rounding=total_rounding,
                                            total_social=total_social)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 모임 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 모임 목록 조회 중 오류가 발생했습니다")


@router.get("/users/{user_id}/handicap-history", response_model=schemas.UserHandicapHistoryResponse)
async def get_user_handicap_history(user_id: int,
                                    page: int = Query(1, ge=1),
                                    limit: int = Query(10, ge=1, le=100),
                                    db: Session = Depends(get_db),
                                    current_user: dict = Depends(get_admin_user)):
    """사용자별 핸디캡 업데이트 이력 조회"""
    try:
        from models import UserScoreHistory, Meeting, Club

        # 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 현재 핸디캡 정보 구성
        handicap_info = schemas.HandicapInfo(
            initial_handicap=float(user.handicap_init) if user.handicap_init else None,
            calculated_handicap=float(user.handicap) if user.handicap else None,
            handicap_update_method=user.handicap_update_method.value if user.handicap_update_method else None,
            handicap_calculation_count=user.handicap_calculation_count,
            last_updated_at=user.updated_at)

        # 페이지네이션 계산
        offset = (page - 1) * limit

        # 스코어 히스토리 조회
        score_history_query = db.query(UserScoreHistory, Meeting,
                                       Club).join(Meeting, UserScoreHistory.meeting_id == Meeting.id).join(
                                           Club, Meeting.club_id == Club.id).filter(UserScoreHistory.user_id == user_id,
                                                                                    Club.deleted_at.is_(None))

        total = score_history_query.count()
        from sqlalchemy import desc
        results = score_history_query.order_by(desc(UserScoreHistory.played_at)).offset(offset).limit(limit).all()

        # 스코어 히스토리 데이터 구성
        score_history = []
        for score_history_item, meeting, club in results:
            score_history.append(
                schemas.HandicapHistoryItem(
                    id=score_history_item.id,
                    meeting_id=score_history_item.meeting_id,
                    meeting_name=meeting.name if meeting else None,
                    club_name=club.name if club else None,
                    gross_score=score_history_item.gross_score,
                    net_score=float(score_history_item.net_score) if score_history_item.net_score else None,
                    handicap_used=float(score_history_item.handicap_used),
                    played_at=score_history_item.played_at,
                    created_at=score_history_item.created_at))

        # 총 페이지 수 계산
        total_pages = (total + limit - 1) // limit if total > 0 else 0

        return schemas.UserHandicapHistoryResponse(handicap_info=handicap_info,
                                                   score_history=score_history,
                                                   total=total,
                                                   page=page,
                                                   limit=limit,
                                                   total_pages=total_pages)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 핸디캡 이력 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 핸디캡 이력 조회 중 오류가 발생했습니다")


@router.post("/users", response_model=UserResponse)
async def create_admin_user(user_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 사용자 생성"""
    from routers.users import create_user
    from schemas import UserCreate

    # dict를 UserCreate 스키마로 변환
    user_create = UserCreate(**user_data)
    # current_user는 이미 JWT에서 가져온 정보
    return await create_user(user_create, db=db, current_user=current_user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_admin_user(user_id: int,
                            user_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 사용자 수정"""
    from routers.users import update_user
    from schemas import UserUpdate

    # dict를 UserUpdate 스키마로 변환
    user_update = UserUpdate(**user_data)
    # current_user는 이미 JWT에서 가져온 정보
    return await update_user(user_id, user_update, db=db, current_user=current_user)


@router.delete("/users/{user_id}")
async def delete_admin_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 사용자 삭제"""
    try:
        logger.info(f"관리자 사용자 삭제 시작 - user_id: {user_id}")

        # 사용자 조회
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 닉네임 락 설정 (사용자 탈퇴와 동일, 7일 제한)
        # 닉네임은 유니크 제약이 있으므로 중복을 피하기 위해 유니크 접미사를 부여한다
        user.original_nickname = user.nickname  # 원본 닉네임 저장
        base_nickname = "탈퇴회원"
        # 타임스탬프 기반 접미사로 충돌 방지 (예: 탈퇴회원_1730208732)
        unique_suffix = f"_{int(get_kst_now().timestamp())}"
        user.nickname = f"{base_nickname}{unique_suffix}"
        user.nickname_locked_until = datetime.now() + timedelta(days=7)

        # 소프트 삭제 (deleted_at 설정)
        user.deleted_at = datetime.now()
        user.status = UserStatus.DELETED

        db.commit()

        logger.info(f"관리자 사용자 삭제 완료 - user_id: {user_id}")
        return {"message": "사용자가 삭제되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 사용자 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 오류: {str(e)}")


@router.get("/dashboard")
async def get_admin_dashboard(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자 대시보드 데이터"""
    try:
        from models import Club, Meeting, Payment, Notice, User, UserStatus
        from schemas import MeetingType

        # 기본 통계
        total_users = db.query(User).filter(User.deleted_at.is_(None), ~User.nickname.like('guest_%')).count()
        active_users = db.query(User).filter(User.deleted_at.is_(None), User.status == UserStatus.ACTIVE,
                                             ~User.nickname.like('guest_%')).count()

        # 클럽 통계 (삭제되지 않은 클럽만)
        total_clubs = db.query(Club).filter(Club.deleted_at.is_(None)).count()

        # 모임 통계
        total_meetings = db.query(Meeting).count()

        # 소셜 모임 통계 (이전 이벤트)
        total_socials = db.query(Meeting).filter(Meeting.meeting_type == MeetingType.SOCIAL).count()

        # 결제 통계
        total_payments = db.query(Payment).count()

        # 공지사항 통계
        total_notices = db.query(Notice).count()

        # 결제 현황 상세 정보
        from models import PaymentStatus
        payment_stats = {"total_amount": 0, "successful_count": 0, "failed_count": 0, "pending_count": 0}

        payments = db.query(Payment).all()
        for payment in payments:
            payment_stats["total_amount"] += payment.amount or 0
            if payment.status == PaymentStatus.SUCCEEDED:
                payment_stats["successful_count"] += 1
            elif payment.status == PaymentStatus.FAILED:
                payment_stats["failed_count"] += 1
            elif payment.status == PaymentStatus.PENDING:
                payment_stats["pending_count"] += 1

        # 클럽 현황 상세 정보
        from models import ClubStatus
        club_stats = {"approved_count": 0, "pending_count": 0, "rejected_count": 0, "total_members": 0}

        clubs = db.query(Club).filter(Club.deleted_at.is_(None)).all()
        for club in clubs:
            if club.status == ClubStatus.ACTIVE:
                club_stats["approved_count"] += 1
            elif club.status == ClubStatus.PENDING:
                club_stats["pending_count"] += 1
            elif club.status == ClubStatus.REJECTED:
                club_stats["rejected_count"] += 1

            # 클럽 멤버 수 계산
            club_stats["total_members"] += db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                                           ClubMembership.status == "ACTIVE").count()

        # 최근 활동 데이터
        recent_activities = []

        # 최근 가입자 (최근 5명, 게스트 제외)
        recent_users = db.query(User).filter(User.deleted_at.is_(None), ~User.nickname.like('guest_%')).order_by(
            User.created_at.desc()).limit(5).all()

        for user in recent_users:
            recent_activities.append({
                "id": f"user_{user.id}",
                "type": "user",
                "title": "새 사용자 가입",
                "message": f"{user.nickname}님이 새로 가입했습니다.",
                "timestamp": user.created_at.isoformat() if user.created_at else None,
                "user_name": user.nickname
            })

        # 최근 모임 생성 (최근 5개)
        recent_meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).limit(5).all()

        for meeting in recent_meetings:
            recent_activities.append({
                "id": f"meeting_{meeting.id}",
                "type": "meeting",
                "title": "새 모임 생성",
                "message": f"{meeting.name} 모임이 생성되었습니다.",
                "timestamp": meeting.created_at.isoformat() if meeting.created_at else None,
                "meeting_title": meeting.name
            })

        # 최근 소셜 모임 생성 (최근 5개)
        recent_socials = db.query(Meeting).filter(Meeting.meeting_type == MeetingType.SOCIAL).order_by(
            Meeting.created_at.desc()).limit(5).all()

        for social in recent_socials:
            recent_activities.append({
                "id": f"social_{social.id}",
                "type": "social",
                "title": "새 소셜 모임 생성",
                "message": f"{social.name} 소셜 모임이 생성되었습니다.",
                "timestamp": social.created_at.isoformat() if social.created_at else None,
                "social_name": social.name
            })

        # 시간순으로 정렬하고 최근 10개만 선택
        recent_activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        recent_activities = recent_activities[:10]

        return {
            "stats": {
                "total_users": total_users,
                "active_users": active_users,
                "total_clubs": total_clubs,
                "total_meetings": total_meetings,
                "total_socials": total_socials,
                "total_payments": total_payments,
                "total_notices": total_notices,
                "admin_users": current_user.get("role")
            },
            "payment_stats": payment_stats,
            "club_stats": club_stats,
            "recent_activities": recent_activities,
            "user": {
                "id": current_user.get("id"),
                "email": current_user.get("email"),
                "role": current_user.get("role")
            }
        }
    except Exception as e:
        logger.error(f"관리자 대시보드 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="대시보드 데이터 조회 중 오류가 발생했습니다")


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """대시보드 통계 조회"""
    try:
        from models import Club, Meeting, Payment, Notice, User, UserStatus
        from schemas import MeetingType

        # 기본 통계
        total_users = db.query(User).filter(User.deleted_at.is_(None), ~User.nickname.like('guest_%')).count()
        total_clubs = db.query(Club).filter(Club.deleted_at.is_(None)).count()
        total_meetings = db.query(Meeting).count()

        # 이번 주 라운딩 수 계산 (이번 주 월요일부터)
        today = get_kst_now()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_rounds = db.query(Meeting).filter(Meeting.meeting_type == MeetingType.ROUND, Meeting.created_at
                                                 >= start_of_week).count()

        return {
            "total_users": total_users,
            "total_clubs": total_clubs,
            "total_meetings": total_meetings,
            "weekly_rounds": weekly_rounds
        }
    except Exception as e:
        logger.error(f"대시보드 통계 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="통계 데이터 조회 중 오류가 발생했습니다")


@router.get("/dashboard/activities")
async def get_dashboard_activities(db: Session = Depends(get_db),
                                   limit: int = Query(default=10, ge=1, le=50),
                                   current_user: dict = Depends(get_admin_user)):
    """최근 활동 조회"""
    try:
        from schemas import MeetingType

        recent_activities = []

        # 최근 가입자 (최근 5명, 게스트 제외)
        recent_users = db.query(User).filter(User.deleted_at.is_(None), ~User.nickname.like('guest_%')).order_by(
            User.created_at.desc()).limit(5).all()

        for user in recent_users:
            recent_activities.append({
                "id": f"user_{user.id}",
                "type": "user_joined",
                "title": f"{user.nickname}님이 새로 가입했습니다.",
                "timestamp": user.created_at.isoformat() if user.created_at else None
            })

        # 최근 모임 생성 (최근 5개)
        recent_meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).limit(5).all()

        for meeting in recent_meetings:
            activity_type = "meeting_created"
            if meeting.meeting_type == MeetingType.SOCIAL:
                activity_type = "post_created"

            recent_activities.append({
                "id": f"meeting_{meeting.id}",
                "type": activity_type,
                "title": f"{meeting.name} 모임이 생성되었습니다.",
                "timestamp": meeting.created_at.isoformat() if meeting.created_at else None
            })

        # 시간순으로 정렬하고 최근 N개만 선택
        recent_activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        recent_activities = recent_activities[:limit]

        return {"data": recent_activities}
    except Exception as e:
        logger.error(f"최근 활동 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="최근 활동 조회 중 오류가 발생했습니다")


@router.get("/debug/sessions")
async def get_session_debug_info(current_user: dict = Depends(get_admin_user)):
    """세션 디버깅 정보 조회 - 세션 관리 없음"""
    return {"message": "세션 관리 없음", "debug_info": {"session_count": 0, "session_ids": []}, "current_user": current_user}


@router.get("/clubs/{club_id}")
async def get_admin_club(club_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 상세 조회 (display_id 또는 id로 조회)"""
    try:
        from models import Club, ClubMembership, ClubRole

        # display_id로 먼저 조회 시도, 없으면 id로 조회
        club = db.query(Club).filter(Club.display_id == club_id).first()

        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 현재 리더 정보 조회
        current_leader = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                         ClubMembership.role == ClubRole.LEADER,
                                                         ClubMembership.status.in_(["ACTIVE", "APPROVED"])).first()

        # 실제 멤버 수 계산 (승인된 멤버만)
        from sqlalchemy import or_
        from schemas import MembershipStatus
        current_member_count = db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            or_(
                ClubMembership.status == MembershipStatus.ACTIVE,
                ClubMembership.status == "APPROVED"  # 이전에 APPROVED로 저장된 멤버도 포함
            )).count()

        return {
            "id":
            club.id,
            "display_id":
            club.display_id,
            "name":
            club.name,
            "sido_code":
            club.sido_code,
            "gungu_codes":
            [region.gungu_code for region in db.query(ClubRegion).filter(ClubRegion.club_id == club.id).all()],
            "type":
            club.type.value if hasattr(club.type, 'value') else str(club.type),
            "description":
            club.description,
            "status":
            club.status.value if hasattr(club.status, 'value') else str(club.status),
            "representative_name":
            club.representative_name,
            "representative_id":
            current_leader.user_id if current_leader else None,
            "location":
            club.location,
            "contact_info":
            club.contact_info,
            "additional_info":
            club.additional_info,
            "profile_image":
            club.profile_image,
            "member_count":
            club.member_count,  # 예상 멤버 수 (레거시)
            "current_member_count":
            current_member_count,  # 실제 멤버 수
            "created_at":
            club.created_at.isoformat() if club.created_at else None,
            "updated_at":
            club.updated_at.isoformat() if club.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 상세 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="클럽 상세 조회 중 오류가 발생했습니다")


def _resolve_club(db: Session, club_id: str) -> Club:
    """club_id(display_id 또는 id)로 Club 조회"""
    club = db.query(Club).filter(Club.display_id == club_id, Club.deleted_at.is_(None)).first()
    if not club:
        try:
            club = db.query(Club).filter(Club.id == int(club_id), Club.deleted_at.is_(None)).first()
        except ValueError:
            club = None
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")
    return club


@router.get("/clubs/{club_id}/notices")
async def get_admin_club_notices(
        club_id: str,
        page: int = 1,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 공지사항 조회"""
    from models import ClubNotice, User
    club = _resolve_club(db, club_id)
    offset = (page - 1) * limit
    notices_query = db.query(ClubNotice).filter(ClubNotice.club_id == club.id)
    total = notices_query.count()
    notices = notices_query.order_by(ClubNotice.is_important.desc(),
                                     ClubNotice.created_at.desc()).offset(offset).limit(limit).all()
    notice_list = []
    for n in notices:
        author = db.query(User).filter(User.id == n.author_id).first()
        notice_list.append({
            "id": n.id,
            "club_id": n.club_id,
            "title": n.title,
            "content": n.content,
            "is_important": n.is_important,
            "is_private": n.is_private,
            "author_id": n.author_id,
            "author_name": author.realname or author.nickname if author else "Unknown",
            "view_count": n.view_count or 0,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        })
    return {
        "data": notice_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 0,
    }


@router.get("/clubs/{club_id}/regulations")
async def get_admin_club_regulations(
        club_id: str,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 조회"""
    from models import RegulationCategory, Regulation
    club = _resolve_club(db, club_id)
    categories = db.query(RegulationCategory).filter(RegulationCategory.club_id == club.id).order_by(
        RegulationCategory.order).all()
    result_categories = []
    for cat in categories:
        regulations = db.query(Regulation).filter(Regulation.category_id == cat.id).order_by(
            Regulation.created_at).all()
        regulations_list = [{
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in regulations]
        result_categories.append({
            "id": cat.id,
            "name": cat.name,
            "order": cat.order,
            "regulations": regulations_list,
        })
    return {"categories": result_categories, "total_categories": len(result_categories)}


@router.get("/clubs/{club_id}/fees")
async def get_admin_club_fees(
        club_id: str,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 회비 항목 조회"""
    from models import ClubFee
    club = _resolve_club(db, club_id)
    fees = db.query(ClubFee).filter(ClubFee.club_id == club.id).order_by(ClubFee.created_at.desc()).all()
    fee_list = []
    for f in fees:
        cycle_val = f.cycle.value if hasattr(f.cycle, "value") else str(f.cycle) if f.cycle else None
        fee_list.append({
            "id": f.id,
            "club_id": f.club_id,
            "name": f.name,
            "amount": float(f.amount) if f.amount else 0,
            "cycle": cycle_val,
            "description": f.description,
            "is_active": f.is_active if f.is_active is not None else True,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return fee_list


def _get_club_posting_user_id(db: Session, club_id: int) -> int:
    """관리자 대신 게시할 때 사용할 User ID (클럽 리더 우선)"""
    leader = db.query(ClubMembership).filter(
        ClubMembership.club_id == club_id,
        ClubMembership.role == ClubRole.LEADER,
        ClubMembership.status.in_(["ACTIVE", "APPROVED"]),
    ).first()
    if leader:
        return leader.user_id
    member = db.query(ClubMembership).filter(
        ClubMembership.club_id == club_id,
        ClubMembership.status.in_(["ACTIVE", "APPROVED"]),
    ).first()
    if member:
        return member.user_id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="클럽에 등록된 멤버가 없어 공지/회비를 등록할 수 없습니다. 먼저 멤버를 추가해주세요.",
    )


@router.post("/clubs/{club_id}/notices")
async def create_admin_club_notice(
        club_id: str,
        notice_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 공지사항 생성"""
    from models import ClubNotice, User
    from schemas import ClubNoticeCreate
    club = _resolve_club(db, club_id)
    author_id = _get_club_posting_user_id(db, club.id)
    data = ClubNoticeCreate(**notice_data)
    notice = ClubNotice(
        club_id=club.id,
        title=data.title,
        content=data.content,
        is_important=data.is_important,
        is_private=data.is_private,
        author_id=author_id,
        view_count=0,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    author = db.query(User).filter(User.id == notice.author_id).first()
    return {
        "id": notice.id,
        "club_id": notice.club_id,
        "title": notice.title,
        "content": notice.content,
        "is_important": notice.is_important,
        "is_private": notice.is_private,
        "author_id": notice.author_id,
        "author_name": author.realname or author.nickname if author else "Unknown",
        "view_count": notice.view_count or 0,
        "created_at": notice.created_at.isoformat() if notice.created_at else None,
        "updated_at": notice.updated_at.isoformat() if notice.updated_at else None,
    }


@router.get("/clubs/{club_id}/notices/{notice_id}")
async def get_admin_club_notice_detail(
        club_id: str,
        notice_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 공지사항 상세 조회"""
    from models import ClubNotice, User
    club = _resolve_club(db, club_id)
    notice = db.query(ClubNotice).filter(
        ClubNotice.id == notice_id,
        ClubNotice.club_id == club.id,
    ).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")
    author = db.query(User).filter(User.id == notice.author_id).first()
    return {
        "id": notice.id,
        "club_id": notice.club_id,
        "title": notice.title,
        "content": notice.content,
        "is_important": notice.is_important,
        "is_private": notice.is_private,
        "author_id": notice.author_id,
        "author_name": author.realname or author.nickname if author else "Unknown",
        "view_count": notice.view_count or 0,
        "created_at": notice.created_at.isoformat() if notice.created_at else None,
        "updated_at": notice.updated_at.isoformat() if notice.updated_at else None,
    }


@router.put("/clubs/{club_id}/notices/{notice_id}")
async def update_admin_club_notice(
        club_id: str,
        notice_id: int,
        notice_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 공지사항 수정"""
    from models import ClubNotice, User
    from schemas import ClubNoticeUpdate
    club = _resolve_club(db, club_id)
    notice = db.query(ClubNotice).filter(
        ClubNotice.id == notice_id,
        ClubNotice.club_id == club.id,
    ).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")
    data = ClubNoticeUpdate(**{
        k: v
        for k, v in notice_data.items() if k in ("title", "content", "is_important", "is_private")
    })
    if data.title is not None:
        notice.title = data.title
    if data.content is not None:
        notice.content = data.content
    if data.is_important is not None:
        notice.is_important = data.is_important
    if data.is_private is not None:
        notice.is_private = data.is_private
    notice.updated_at = get_kst_now()
    db.commit()
    db.refresh(notice)
    author = db.query(User).filter(User.id == notice.author_id).first()
    return {
        "id": notice.id,
        "club_id": notice.club_id,
        "title": notice.title,
        "content": notice.content,
        "is_important": notice.is_important,
        "is_private": notice.is_private,
        "author_id": notice.author_id,
        "author_name": author.realname or author.nickname if author else "Unknown",
        "view_count": notice.view_count or 0,
        "created_at": notice.created_at.isoformat() if notice.created_at else None,
        "updated_at": notice.updated_at.isoformat() if notice.updated_at else None,
    }


@router.delete("/clubs/{club_id}/notices/{notice_id}")
async def delete_admin_club_notice(
        club_id: str,
        notice_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 공지사항 삭제"""
    from models import ClubNotice
    club = _resolve_club(db, club_id)
    notice = db.query(ClubNotice).filter(
        ClubNotice.id == notice_id,
        ClubNotice.club_id == club.id,
    ).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")
    db.delete(notice)
    db.commit()
    return {"message": "공지사항이 삭제되었습니다", "success": True}


@router.post("/clubs/{club_id}/fees")
async def create_admin_club_fee(
        club_id: str,
        fee_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 회비 항목 생성"""
    from models import ClubFee
    from schemas import ClubFeeCreate, BillingCycle
    club = _resolve_club(db, club_id)
    created_by = _get_club_posting_user_id(db, club.id)
    data = ClubFeeCreate(**fee_data)
    cycle_val = None
    if data.cycle:
        cycle_val = BillingCycle[data.cycle] if isinstance(data.cycle, str) else data.cycle
    fee = ClubFee(
        club_id=club.id,
        name=data.name,
        amount=data.amount,
        cycle=cycle_val,
        description=data.description,
        is_active=data.is_active,
        created_by=created_by,
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return {
        "id": fee.id,
        "club_id": fee.club_id,
        "name": fee.name,
        "amount": float(fee.amount),
        "cycle": fee.cycle.value if fee.cycle else None,
        "description": fee.description,
        "is_active": fee.is_active,
        "created_by": fee.created_by,
        "created_at": fee.created_at.isoformat() if fee.created_at else None,
        "updated_at": fee.updated_at.isoformat() if fee.updated_at else None,
    }


@router.put("/clubs/{club_id}/fees/{fee_id}")
async def update_admin_club_fee(
        club_id: str,
        fee_id: int,
        fee_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 회비 항목 수정"""
    from models import ClubFee
    from schemas import ClubFeeUpdate, BillingCycle
    club = _resolve_club(db, club_id)
    fee = db.query(ClubFee).filter(
        ClubFee.id == fee_id,
        ClubFee.club_id == club.id,
    ).first()
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회비 항목을 찾을 수 없습니다")
    data = ClubFeeUpdate(**{
        k: v
        for k, v in fee_data.items() if k in ("name", "amount", "cycle", "description", "is_active")
    })
    if data.name is not None:
        fee.name = data.name
    if data.amount is not None:
        fee.amount = data.amount
    if data.cycle is not None:
        fee.cycle = BillingCycle[data.cycle] if isinstance(data.cycle, str) else data.cycle
    if data.description is not None:
        fee.description = data.description
    if data.is_active is not None:
        fee.is_active = data.is_active
    fee.updated_at = get_kst_now()
    db.commit()
    db.refresh(fee)
    return {
        "id": fee.id,
        "club_id": fee.club_id,
        "name": fee.name,
        "amount": float(fee.amount),
        "cycle": fee.cycle.value if fee.cycle else None,
        "description": fee.description,
        "is_active": fee.is_active,
        "created_by": fee.created_by,
        "created_at": fee.created_at.isoformat() if fee.created_at else None,
        "updated_at": fee.updated_at.isoformat() if fee.updated_at else None,
    }


@router.delete("/clubs/{club_id}/fees/{fee_id}")
async def delete_admin_club_fee(
        club_id: str,
        fee_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 회비 항목 삭제"""
    from models import ClubFee
    club = _resolve_club(db, club_id)
    fee = db.query(ClubFee).filter(
        ClubFee.id == fee_id,
        ClubFee.club_id == club.id,
    ).first()
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회비 항목을 찾을 수 없습니다")
    db.delete(fee)
    db.commit()
    return {"message": "회비 항목이 삭제되었습니다", "success": True}


# 규정: Regulation의 created_by는 User FK가 아니므로 관리자 이름 사용 가능
@router.get("/clubs/{club_id}/regulations/categories")
async def get_admin_club_regulation_categories(
        club_id: str,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 카테고리 목록 조회"""
    from models import RegulationCategory
    club = _resolve_club(db, club_id)
    categories = db.query(RegulationCategory).filter(RegulationCategory.club_id == club.id).order_by(
        RegulationCategory.order).all()
    return [{"id": c.id, "name": c.name, "order": c.order} for c in categories]


@router.post("/clubs/{club_id}/regulations/categories")
async def create_admin_club_regulation_category(
        club_id: str,
        category_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 규정 카테고리 생성"""
    from models import RegulationCategory
    club = _resolve_club(db, club_id)
    name = category_data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카테고리 이름을 입력해주세요")
    max_order = db.query(RegulationCategory).filter(RegulationCategory.club_id == club.id).count()
    cat = RegulationCategory(club_id=club.id, name=name, order=max_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "order": cat.order}


@router.put("/clubs/{club_id}/regulations/categories/{category_id}")
async def update_admin_club_regulation_category(
        club_id: str,
        category_id: int,
        category_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 규정 카테고리 수정"""
    from models import RegulationCategory
    club = _resolve_club(db, club_id)
    cat = db.query(RegulationCategory).filter(
        RegulationCategory.id == category_id,
        RegulationCategory.club_id == club.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카테고리를 찾을 수 없습니다")
    if "name" in category_data and category_data["name"]:
        cat.name = category_data["name"].strip()
    if "order" in category_data:
        cat.order = int(category_data["order"])
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "order": cat.order}


@router.delete("/clubs/{club_id}/regulations/categories/{category_id}")
async def delete_admin_club_regulation_category(
        club_id: str,
        category_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 규정 카테고리 삭제"""
    from models import RegulationCategory
    club = _resolve_club(db, club_id)
    cat = db.query(RegulationCategory).filter(
        RegulationCategory.id == category_id,
        RegulationCategory.club_id == club.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카테고리를 찾을 수 없습니다")
    db.delete(cat)
    db.commit()
    return {"message": "카테고리가 삭제되었습니다", "success": True}


@router.post("/clubs/{club_id}/regulations")
async def create_admin_club_regulation(
        club_id: str,
        regulation_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 생성"""
    from models import Regulation, RegulationCategory
    from schemas import ClubRegulationCreate
    club = _resolve_club(db, club_id)
    data = ClubRegulationCreate(**regulation_data)
    category = db.query(RegulationCategory).filter(
        RegulationCategory.id == data.category_id,
        RegulationCategory.club_id == club.id,
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="규정 카테고리를 찾을 수 없습니다")
    admin_name = current_user.get("name", "관리자")
    reg = Regulation(
        club_id=club.id,
        category_id=data.category_id,
        title=data.title,
        content=data.content,
        status=data.status or "ACTIVE",
        created_by=0,
        created_by_name=f"{admin_name} (관리자)",
        published_at=datetime.now() if (data.status or "ACTIVE") == "ACTIVE" else None,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return {
        "id": reg.id,
        "club_id": reg.club_id,
        "category_id": reg.category_id,
        "title": reg.title,
        "content": reg.content,
        "status": reg.status,
        "created_by": reg.created_by,
        "created_by_name": reg.created_by_name,
        "published_at": reg.published_at.isoformat() if reg.published_at else None,
        "created_at": reg.created_at.isoformat() if reg.created_at else None,
        "updated_at": reg.updated_at.isoformat() if reg.updated_at else None,
        "category_name": category.name,
    }


@router.get("/clubs/{club_id}/regulations/{regulation_id}")
async def get_admin_club_regulation_detail(
        club_id: str,
        regulation_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 상세 조회"""
    from models import Regulation, RegulationCategory
    club = _resolve_club(db, club_id)
    reg = db.query(Regulation).filter(
        Regulation.id == regulation_id,
        Regulation.club_id == club.id,
    ).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="규정을 찾을 수 없습니다")
    cat = db.query(RegulationCategory).filter(RegulationCategory.id == reg.category_id).first()
    return {
        "id": reg.id,
        "club_id": reg.club_id,
        "category_id": reg.category_id,
        "title": reg.title,
        "content": reg.content,
        "status": reg.status,
        "created_by": reg.created_by,
        "created_by_name": reg.created_by_name,
        "published_at": reg.published_at.isoformat() if reg.published_at else None,
        "created_at": reg.created_at.isoformat() if reg.created_at else None,
        "updated_at": reg.updated_at.isoformat() if reg.updated_at else None,
        "category_name": cat.name if cat else None,
    }


@router.put("/clubs/{club_id}/regulations/{regulation_id}")
async def update_admin_club_regulation(
        club_id: str,
        regulation_id: int,
        regulation_data: dict,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 수정"""
    from models import Regulation, RegulationCategory
    from schemas import ClubRegulationUpdate
    club = _resolve_club(db, club_id)
    reg = db.query(Regulation).filter(
        Regulation.id == regulation_id,
        Regulation.club_id == club.id,
    ).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="규정을 찾을 수 없습니다")
    data = ClubRegulationUpdate(**{
        k: v
        for k, v in regulation_data.items() if k in ("category_id", "title", "content", "status")
    })
    if data.category_id is not None:
        cat = db.query(RegulationCategory).filter(
            RegulationCategory.id == data.category_id,
            RegulationCategory.club_id == club.id,
        ).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="규정 카테고리를 찾을 수 없습니다")
        reg.category_id = data.category_id
    if data.title is not None:
        reg.title = data.title
    if data.content is not None:
        reg.content = data.content
    if data.status is not None:
        reg.status = data.status
    reg.updated_at = get_kst_now()
    db.commit()
    db.refresh(reg)
    cat = db.query(RegulationCategory).filter(RegulationCategory.id == reg.category_id).first()
    return {
        "id": reg.id,
        "club_id": reg.club_id,
        "category_id": reg.category_id,
        "title": reg.title,
        "content": reg.content,
        "status": reg.status,
        "created_by": reg.created_by,
        "created_by_name": reg.created_by_name,
        "published_at": reg.published_at.isoformat() if reg.published_at else None,
        "created_at": reg.created_at.isoformat() if reg.created_at else None,
        "updated_at": reg.updated_at.isoformat() if reg.updated_at else None,
        "category_name": cat.name if cat else None,
    }


@router.delete("/clubs/{club_id}/regulations/{regulation_id}")
async def delete_admin_club_regulation(
        club_id: str,
        regulation_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """관리자용 클럽 규정 삭제"""
    from models import Regulation
    club = _resolve_club(db, club_id)
    reg = db.query(Regulation).filter(
        Regulation.id == regulation_id,
        Regulation.club_id == club.id,
    ).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="규정을 찾을 수 없습니다")
    db.delete(reg)
    db.commit()
    return {"message": "규정이 삭제되었습니다", "success": True}


@router.post("/clubs")
async def create_admin_club(club_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 생성"""
    from models import User, Club, ClubMembership, ClubRole, ClubStatus, ClubRegion
    from schemas import MembershipStatus
    from utils.display_id_generator import generate_club_display_id

    try:
        # 대표자 사용자 조회
        representative_id = club_data.get('representative_id')
        if not representative_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="대표자 사용자 ID가 필요합니다.")

        representative_user = db.query(User).filter(User.id == representative_id, User.deleted_at.is_(None)).first()

        if not representative_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_F, detail="대표자 사용자를 찾을 수 없습니다.")

        # display_id 생성
        display_id = generate_club_display_id(db)

        # 정기 회비 정보 처리 (ClubFee로 생성)
        regular_fee = club_data.get('regular_fee')
        has_regular_fee = False
        regular_fee_amount = None
        regular_fee_cycle = None
        regular_fee_description = None

        if regular_fee:
            has_regular_fee = True
            regular_fee_amount = regular_fee.get('amount')
            regular_fee_cycle = regular_fee.get('cycle')
            regular_fee_description = regular_fee.get('description', '')
        else:
            # 직접 전달된 경우도 처리
            has_regular_fee = club_data.get('has_regular_fee', False)
            regular_fee_amount = club_data.get('regular_fee_amount')
            regular_fee_cycle = club_data.get('regular_fee_cycle')
            regular_fee_description = club_data.get('regular_fee_description', '')

        # 대표자명 결정: realname > nickname > email 우선순위
        representative_name = (getattr(representative_user, 'realname', None) or representative_user.nickname
                               or representative_user.email)

        if not club_data.get("sido_code"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="시도를 선택하셔야 합니다.")

        gungu_codes = club_data.get("gungu_codes") or []
        unique_gungu_codes = validate_gungu_codes(db, club_data.get("sido_code"), gungu_codes)

        # 클럽 생성 (관리자가 생성하므로 바로 승인)
        club = Club(
            display_id=display_id,
            name=club_data['name'],
            sido_code=club_data["sido_code"],
            type=club_data['type'],
            description=club_data.get('description', ''),
            location=club_data.get('location', ''),
            contact_info=club_data.get('contact_info', ''),
            representative_name=representative_name,
            additional_info=club_data.get('additional_info', ''),
            member_count=club_data.get('member_count', 1),  # 대표자 포함 또는 지정된 값
            status=ClubStatus.ACTIVE  # 관리자가 생성하므로 바로 활성화
        )

        db.add(club)
        db.commit()
        db.refresh(club)

        for gungu_code in unique_gungu_codes:
            db.add(ClubRegion(club_id=club.id, gungu_code=gungu_code))

        # 지정된 사용자를 리더로 추가
        membership = ClubMembership(club_id=club.id,
                                    user_id=representative_id,
                                    role=ClubRole.LEADER,
                                    status=MembershipStatus.ACTIVE)

        db.add(membership)

        # 정기 회비가 있는 경우 ClubFee로 생성
        if has_regular_fee and regular_fee_amount and regular_fee_cycle:
            from models import ClubFee
            regular_fee_obj = ClubFee(club_id=club.id,
                                      name="정기 회비",
                                      amount=float(regular_fee_amount),
                                      cycle=regular_fee_cycle,
                                      description=regular_fee_description or '',
                                      is_active=True,
                                      created_by=representative_id)
            db.add(regular_fee_obj)

        db.commit()

        # 응답용 정기 회비 정보 조회
        from models import ClubFee as ClubFeeModel
        from models.enums import BillingCycle
        regular_fee_response = db.query(ClubFeeModel).filter(
            ClubFeeModel.club_id == club.id, ClubFeeModel.is_active == True,
            ClubFeeModel.cycle.in_([BillingCycle.MONTHLY, BillingCycle.QUARTERLY, BillingCycle.YEARLY])).first()

        return {
            "id":
            club.id,
            "display_id":
            club.display_id,
            "name":
            club.name,
            "sido_code":
            club.sido_code,
            "gungu_codes":
            [region.gungu_code for region in db.query(ClubRegion).filter(ClubRegion.club_id == club.id).all()],
            "type":
            club.type.value,
            "description":
            club.description,
            "status":
            club.status.value,
            "representative_name":
            club.representative_name,
            "representative_id":
            representative_id,
            "location":
            club.location,
            "contact_info":
            club.contact_info,
            "additional_info":
            club.additional_info,
            "member_count":
            club.member_count,
            "has_regular_fee":
            regular_fee_response is not None,
            "regular_fee_amount":
            float(regular_fee_response.amount) if regular_fee_response and regular_fee_response.amount else None,
            "regular_fee_cycle":
            regular_fee_response.cycle.value if regular_fee_response and regular_fee_response.cycle else None,
            "regular_fee_description":
            regular_fee_response.description if regular_fee_response else None,
            "created_at":
            club.created_at.isoformat(),
            "updated_at":
            club.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 클럽 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"클럽 생성 중 오류가 발생했습니다: {str(e)}")


@router.post("/upload")
async def admin_upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_admin_user)):
    """관리자용 파일 업로드"""
    from routers.upload import validate_file, generate_filename
    import os

    try:
        # 파일 유효성 검사
        if not validate_file(file):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF만 업로드 가능합니다.")

        # 파일 크기 확인 (10MB 제한)
        file_content = await file.read()
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다.")

        # 업로드 디렉토리 설정
        UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # 파일명 생성
        new_filename = generate_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, new_filename)

        # 중복 파일명 처리
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(new_filename)
            new_filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_DIR, new_filename)
            counter += 1

        # 파일 저장
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        logger.info(f"관리자 파일 업로드 성공: {file.filename} -> {new_filename}")

        return {
            "success": True,
            "message": "파일이 성공적으로 업로드되었습니다.",
            "filename": new_filename,
            "original_filename": file.filename,
            "file_size": len(file_content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 파일 업로드 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")


@router.get("/clubs/{club_id}/pending-members")
async def get_admin_club_pending_members(club_id: str,
                                         db: Session = Depends(get_db),
                                         current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 가입 신청 대기자 목록 조회"""
    try:
        from models import Club, ClubMembership, User
        from schemas import MembershipStatus

        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # PENDING 상태의 멤버들 조회
        pending_memberships = db.query(ClubMembership).join(User).filter(
            ClubMembership.club_id == club.id, ClubMembership.status == MembershipStatus.PENDING,
            User.deleted_at.is_(None)).all()

        members = []
        for membership in pending_memberships:
            user = membership.user
            members.append({
                "membership_id": membership.id,
                "user_id": user.id,
                "user_nickname": user.nickname,
                "user_email": user.email,
                "user_realname": user.realname,
                "role": membership.role.value if membership.role else "MEMBER",
                "status": membership.status.value,
                "applied_at": membership.created_at.isoformat() if membership.created_at else None
            })

        return {"club_id": club.id, "club_name": club.name, "pending_members": members, "total_pending": len(members)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 가입 대기자 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="가입 대기자 조회 중 오류가 발생했습니다")


@router.get("/clubs/{club_id}/members")
async def get_admin_club_members(club_id: str,
                                 db: Session = Depends(get_db),
                                 current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 멤버 목록 조회"""
    try:
        from models import Club, ClubMembership, ClubRole, User

        # display_id로 먼저 조회 시도, 없으면 id로 조회
        club = db.query(Club).filter(Club.display_id == club_id).first()

        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 멤버십과 사용자 정보를 JOIN으로 한번에 조회
        query = db.query(ClubMembership, User).join(User, ClubMembership.user_id == User.id).filter(
            ClubMembership.club_id == club.id,
            User.deleted_at.is_(None),
            ~User.email.like('%@guest.local'),  # 게스트 이메일 제외
            ~User.nickname.like('guest_%')  # 게스트 닉네임 제외
        )

        results = query.all()

        # 멤버 데이터 구성
        members = []
        for membership, user in results:
            # Enum인지 문자열인지 확인하여 적절히 처리
            role_value = membership.role.value if hasattr(membership.role, 'value') else str(membership.role)
            status_value = membership.status.value if hasattr(membership.status, 'value') else str(membership.status)

            # 리더는 항상 APPROVED 상태로 강제 설정
            leader_role = ClubRole.LEADER.value if hasattr(ClubRole.LEADER, 'value') else "LEADER"
            final_status = "APPROVED" if role_value == leader_role else status_value

            member = {
                "id": membership.id,
                "club_id": membership.club_id,
                "user_id": membership.user_id,
                "role": role_value,
                "status": final_status,
                "created_at": membership.created_at.isoformat(),
                "updated_at": membership.updated_at.isoformat(),
                "user_nickname": user.nickname,
                "user_email": user.email,
                "user_realname": user.realname,  # 관리자용이므로 마스킹하지 않음
                "user_phone_number": user.phone_number,
                "user_birthdate": user.birthdate.isoformat() if user.birthdate else None,
                "user_gender": user.gender,
                "user_handicap": user.handicap,
                "user_average_score": user.average_score
            }
            members.append(member)

        return {"members": members, "total_members": len(members)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 멤버 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"클럽 멤버 조회 중 오류가 발생했습니다: {str(e)}")


@router.put("/clubs/{club_id}/members/{user_id}/approve")
async def approve_admin_club_membership(club_id: str,
                                        user_id: int,
                                        db: Session = Depends(get_db),
                                        current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 가입 승인"""
    try:
        from models import Club, ClubMembership, User
        from schemas import MembershipStatus

        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 가입 신청 조회
        membership = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                     ClubMembership.user_id == user_id,
                                                     ClubMembership.status == MembershipStatus.PENDING).first()

        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가입 신청을 찾을 수 없습니다")

        # 가입 승인
        membership.status = MembershipStatus.ACTIVE
        membership.updated_at = get_kst_now()

        # 클럽 멤버 수 증가
        club.member_count = (club.member_count or 0) + 1
        club.updated_at = get_kst_now()

        db.commit()

        # status 값 추출 (Enum인지 문자열인지 확인)
        status_value = membership.status.value if hasattr(membership.status, 'value') else str(membership.status)

        return {"message": "클럽 가입이 승인되었습니다", "membership_id": membership.id, "user_id": user_id, "status": status_value}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 가입 승인 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"가입 승인 중 오류가 발생했습니다: {str(e)}")


@router.put("/clubs/{club_id}/members/{user_id}/reject")
async def reject_admin_club_membership(club_id: str,
                                       user_id: int,
                                       db: Session = Depends(get_db),
                                       current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 가입 거절"""
    try:
        from models import Club, ClubMembership, User
        from schemas import MembershipStatus

        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 가입 신청 조회
        membership = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                     ClubMembership.user_id == user_id,
                                                     ClubMembership.status == MembershipStatus.PENDING).first()

        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가입 신청을 찾을 수 없습니다")

        # 가입 거절 (멤버십 삭제)
        db.delete(membership)
        db.commit()

        return {"message": "클럽 가입이 거절되었습니다", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 가입 거절 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"가입 거절 중 오류가 발생했습니다: {str(e)}")


@router.post("/clubs/{club_id}/members")
async def add_admin_club_member(club_id: str,
                                user_id: int,
                                role: str = "MEMBER",
                                db: Session = Depends(get_db),
                                current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 멤버 추가"""
    try:
        from models import Club, ClubMembership, ClubRole, User
        from schemas import MembershipStatus
        from datetime import datetime

        # 클럽 조회
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다")

        # 이미 멤버인지 확인
        existing_membership = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                              ClubMembership.user_id == user_id).first()

        if existing_membership:
            if existing_membership.status == MembershipStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 해당 클럽의 멤버입니다")
            else:
                # 승인되지 않은 상태라면 승인 상태로 변경
                existing_membership.status = MembershipStatus.ACTIVE
                existing_membership.role = ClubRole[role] if role in ['LEADER', 'MANAGER', 'MEMBER'
                                                                      ] else ClubRole.MEMBER
                existing_membership.updated_at = get_kst_now()
                db.commit()

                return {
                    "message": "기존 멤버십이 승인되었습니다",
                    "membership_id": existing_membership.id,
                    "user_id": user_id,
                    "role": existing_membership.role.value,
                    "status": existing_membership.status.value
                }

        # 새 멤버십 생성
        membership = ClubMembership(
            club_id=club.id,
            user_id=user_id,
            role=ClubRole[role] if role in ['LEADER', 'MANAGER', 'MEMBER'] else ClubRole.MEMBER,
            status=MembershipStatus.ACTIVE,  # 관리자가 추가하므로 바로 승인
            created_at=get_kst_now(),
            updated_at=get_kst_now())

        db.add(membership)
        db.commit()

        return {
            "message": "멤버가 성공적으로 추가되었습니다",
            "membership_id": membership.id,
            "user_id": user_id,
            "role": membership.role.value,
            "status": membership.status.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 클럽 멤버 추가 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"멤버 추가 중 오류가 발생했습니다: {str(e)}")


@router.put("/clubs/{club_id}/members/{user_id}/role")
async def update_admin_club_member_role(club_id: str,
                                        user_id: int,
                                        role_data: dict,
                                        db: Session = Depends(get_db),
                                        current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 멤버 역할 변경"""
    try:
        from models import Club, ClubMembership, ClubRole, User
        from datetime import datetime, timezone

        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 대상 멤버 조회
        target_membership = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                            ClubMembership.user_id == user_id).first()

        if not target_membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 사용자가 클럽 멤버가 아닙니다")

        # 역할 변경
        new_role = role_data.get("new_role") or role_data.get("role")
        if not new_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="역할을 지정해주세요")

        # 유효한 역할인지 확인
        if new_role not in ['MEMBER', 'MANAGER', 'LEADER']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 역할입니다")

        target_membership.role = ClubRole[new_role]
        target_membership.updated_at = get_kst_now()
        db.commit()

        return {"message": f"멤버 역할이 {new_role}로 변경되었습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 멤버 역할 변경 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"멤버 역할 변경 중 오류가 발생했습니다: {str(e)}")


@router.delete("/clubs/{club_id}/members/{user_id}")
async def remove_admin_club_member(club_id: str,
                                   user_id: int,
                                   db: Session = Depends(get_db),
                                   current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 멤버 내보내기"""
    try:
        from models import Club, ClubMembership, User

        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 대상 멤버 조회
        target_membership = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                            ClubMembership.user_id == user_id).first()

        if not target_membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 사용자가 클럽 멤버가 아닙니다")

        # 멤버십 삭제
        db.delete(target_membership)

        # 클럽 멤버 수 감소
        club.member_count = max(0, club.member_count - 1)
        db.commit()

        return {"message": "멤버가 성공적으로 내보내졌습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 멤버 내보내기 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"멤버 내보내기 중 오류가 발생했습니다: {str(e)}")


@router.put("/clubs/{club_id}")
async def update_admin_club(club_id: str,
                            club_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 수정 (display_id 또는 id로 조회)"""
    try:
        from models import Club, ClubStatus, ClubRegion
        from schemas import ClubResponse

        # display_id로 먼저 조회 시도, 없으면 id로 조회
        club = db.query(Club).filter(Club.display_id == club_id, Club.deleted_at.is_(None)).first()

        if not club:
            # display_id로 찾지 못했으면 id로 조회
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int, Club.deleted_at.is_(None)).first()
            except ValueError:
                # 숫자로 변환 불가능한 경우
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다")

        # 클럽 정보 수정
        if club_data.get("name") is not None:
            club.name = club_data["name"]
        if club_data.get("type") is not None:
            club.type = club_data["type"]
        if club_data.get("description") is not None:
            club.description = club_data["description"]
        if club_data.get("sido_code") is not None and not club_data.get("sido_code"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="시도를 선택하셔야 합니다.")
        if club_data.get("sido_code") is not None and "gungu_codes" not in club_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sido_code 변경 시 gungu_codes는 필수입니다.")
        if club_data.get("sido_code") is not None:
            club.sido_code = club_data["sido_code"]
        if club_data.get("member_count") is not None:
            club.member_count = club_data["member_count"]
        if club_data.get("location") is not None:
            club.location = club_data["location"]
        if club_data.get("contact_info") is not None:
            club.contact_info = club_data["contact_info"]
        if club_data.get("additional_info") is not None:
            club.additional_info = club_data["additional_info"]
        if club_data.get("application_deadline") is not None:
            club.application_deadline = club_data["application_deadline"]
        if club_data.get("status") is not None:
            club.status = ClubStatus(club_data["status"])

        if "gungu_codes" in club_data:
            target_sido_code = club_data.get("sido_code") or club.sido_code
            if not target_sido_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="시도를 선택하셔야 합니다.")
            gungu_codes = club_data.get("gungu_codes") or []
            unique_gungu_codes = validate_gungu_codes(db, target_sido_code, gungu_codes)
            db.query(ClubRegion).filter(ClubRegion.club_id == club.id).delete(synchronize_session=False)
            for gungu_code in unique_gungu_codes:
                db.add(ClubRegion(club_id=club.id, gungu_code=gungu_code))

        club.updated_at = get_kst_now()
        db.commit()
        db.refresh(club)

        club.gungu_codes = [
            region.gungu_code for region in db.query(ClubRegion).filter(ClubRegion.club_id == club.id).all()
        ]
        return club

    except HTTPException:
        raise
    except ValueError as e:
        db.rollback()
        logger.error(f"클럽 수정 중 값 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"잘못된 값입니다: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"클럽 수정 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 내부 오류가 발생했습니다: {str(e)}")


@router.delete("/clubs/{club_id}")
async def delete_admin_club(club_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 클럽 삭제"""
    try:
        # 클럽 조회 (display_id 또는 id로)
        club = db.query(Club).filter(Club.display_id == club_id).first()
        if not club:
            try:
                club_id_int = int(club_id)
                club = db.query(Club).filter(Club.id == club_id_int).first()
            except ValueError:
                club = None

        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다.")

        # 클럽에 승인된 멤버가 있는지 확인
        approved_members = db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                           ClubMembership.status == MembershipStatus.ACTIVE).count()

        if approved_members > 1:  # 대표자 제외하고 다른 멤버가 있으면
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"승인된 멤버가 {approved_members-1}명 있습니다. 모든 멤버를 제거한 후 클럽을 삭제해주세요.")

        # 클럽 삭제 (소프트 삭제)
        club.deleted_at = get_kst_now()
        club.updated_at = get_kst_now()

        # 관련 멤버십도 삭제
        memberships = db.query(ClubMembership).filter(ClubMembership.club_id == club.id).all()

        for membership in memberships:
            membership.deleted_at = get_kst_now()
            membership.updated_at = get_kst_now()

        db.commit()

        logger.info(f"관리자가 클럽 삭제: {club.display_id} ({club.name})")

        return {"success": True, "message": f"클럽 '{club.name}'이 성공적으로 삭제되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"클럽 삭제 중 오류 발생: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"클럽 삭제 중 오류가 발생했습니다: {str(e)}")


@router.get("/meetings/rounding")
async def admin_get_rounding_meetings(page: int = Query(1, ge=1, description="페이지 번호"),
                                      limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
                                      status: Optional[str] = Query(None, description="모임 상태 필터"),
                                      search: Optional[str] = Query(None, description="검색어"),
                                      club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
                                      current_user: dict = Depends(get_admin_user),
                                      db: Session = Depends(get_db)):
    """관리자용 라운딩 모임 목록 조회 (모든 클럽 조회 가능)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from sqlalchemy import desc, and_, or_

        query = db.query(Meeting).join(Club).filter(Meeting.meeting_type == MeetingType.ROUND)

        # 클럽 필터
        if club_id:
            query = query.filter(Meeting.club_id == club_id)

        # 상태 필터
        if status:
            query = query.filter(Meeting.status == status)

        # 검색 필터
        if search:
            search_filter = or_(Meeting.name.contains(search), Meeting.course_name.contains(search),
                                Meeting.location.contains(search))
            query = query.filter(search_filter)

        # 총 개수 조회
        total = query.count()

        # 페이지네이션
        meetings = query.offset((page - 1) * limit).limit(limit).all()

        # 응답 데이터 구성
        meeting_data = []
        for meeting in meetings:
            # 참가자 수 조회
            participant_count = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

            # 개설자(ORGANIZER) 조회
            organizer_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.role == MeetingParticipantRole.ORGANIZER)).first()

            creator_info = None
            if organizer_participant and organizer_participant.user:
                creator_info = {
                    "id": organizer_participant.user.id,
                    "realname": organizer_participant.user.realname,
                    "nickname": organizer_participant.user.nickname,
                    "email": organizer_participant.user.email
                }

            # meeting_type과 status는 데이터베이스에서 문자열로 저장되므로 .value 접근 불필요
            meeting_type_str = meeting.meeting_type
            if hasattr(meeting_type_str, 'value'):
                meeting_type_str = meeting_type_str.value

            meeting_subtype_str = meeting.meeting_subtype
            if meeting_subtype_str and hasattr(meeting_subtype_str, 'value'):
                meeting_subtype_str = meeting_subtype_str.value

            status_str = meeting.status
            if hasattr(status_str, 'value'):
                status_str = status_str.value

            meeting_data.append({
                "id":
                str(meeting.id),
                "name":
                str(meeting.name) if meeting.name else "",
                "description":
                str(meeting.description) if meeting.description else "",
                "meeting_type":
                str(meeting_type_str) if meeting_type_str else "",
                "meeting_subtype":
                str(meeting_subtype_str) if meeting_subtype_str else "",
                "location":
                str(meeting.location) if meeting.location else "",
                "course_name":
                str(meeting.course_name) if meeting.course_name else "",
                "tee_time":
                meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
                "meeting_time":
                meeting.meeting_time.isoformat() if meeting.meeting_time else None,
                "max_participants":
                int(meeting.max_participants) if meeting.max_participants else 0,
                "status":
                str(status_str) if status_str else "",
                "club_id":
                str(meeting.club_id),
                "club_name":
                str(meeting.club.name) if meeting.club and meeting.club.name else "",
                "participant_count":
                int(participant_count),
                "creator":
                creator_info,
                "created_at":
                meeting.created_at.isoformat() if meeting.created_at else None,
                "updated_at":
                meeting.updated_at.isoformat() if meeting.updated_at else None
            })

        total_pages = (total + limit - 1) // limit

        return {"data": meeting_data, "total": total, "page": page, "limit": limit, "total_pages": total_pages}

    except Exception as e:
        logger.error(f"관리자 라운딩 모임 목록 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라운딩 모임 목록 조회 중 오류가 발생했습니다")


@router.get("/meetings/event")
async def admin_get_event_meetings(page: int = Query(1, ge=1, description="페이지 번호"),
                                   limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
                                   status: Optional[str] = Query(None, description="모임 상태 필터"),
                                   search: Optional[str] = Query(None, description="검색어"),
                                   club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
                                   current_user: dict = Depends(get_admin_user),
                                   db: Session = Depends(get_db)):
    """관리자용 이벤트 모임 목록 조회 (모든 클럽 조회 가능)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from sqlalchemy import desc, and_, or_

        query = db.query(Meeting).join(Club).filter(Meeting.meeting_type == MeetingType.SOCIAL)

        # 클럽 필터
        if club_id:
            query = query.filter(Meeting.club_id == club_id)

        # 상태 필터
        if status:
            query = query.filter(Meeting.status == status)

        # 검색 필터
        if search:
            search_filter = or_(Meeting.name.contains(search), Meeting.venue_name.contains(search),
                                Meeting.location.contains(search))
            query = query.filter(search_filter)

        # 총 개수 조회
        total = query.count()

        # 페이지네이션
        meetings = query.offset((page - 1) * limit).limit(limit).all()

        # 응답 데이터 구성
        meeting_data = []
        for meeting in meetings:
            # 참가자 수 조회
            participant_count = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

            # 개설자(ORGANIZER) 조회
            organizer_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.role == MeetingParticipantRole.ORGANIZER)).first()

            creator_info = None
            if organizer_participant and organizer_participant.user:
                creator_info = {
                    "id": organizer_participant.user.id,
                    "realname": organizer_participant.user.realname,
                    "nickname": organizer_participant.user.nickname,
                    "email": organizer_participant.user.email
                }

            meeting_data.append({
                "id":
                meeting.id,
                "name":
                meeting.name,
                "description":
                meeting.description,
                "meeting_type":
                meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
                "meeting_subtype":
                meeting.meeting_subtype.value
                if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
                "location":
                meeting.location,
                "venue_name":
                meeting.venue_name,
                "meeting_time":
                meeting.meeting_time.isoformat() if meeting.meeting_time else None,
                "max_participants":
                meeting.max_participants,
                "status":
                meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
                "club_id":
                meeting.club_id,
                "club_name":
                meeting.club.name,
                "participant_count":
                participant_count,
                "creator":
                creator_info,
                "created_at":
                meeting.created_at.isoformat() if meeting.created_at else None,
                "updated_at":
                meeting.updated_at.isoformat() if meeting.updated_at else None
            })

        total_pages = (total + limit - 1) // limit

        return {"data": meeting_data, "total": total, "page": page, "limit": limit, "total_pages": total_pages}

    except Exception as e:
        logger.error(f"관리자 이벤트 모임 목록 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이벤트 모임 목록 조회 중 오류가 발생했습니다")


@router.get("/meetings/{meeting_id}")
async def get_admin_meeting(meeting_id: int,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 상세 조회"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingParticipantStatus
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).join(Club).filter(Meeting.id == meeting_id).first()

        if not meeting:
            from fastapi import status as http_status
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            and_(MeetingParticipant.meeting_id == meeting.id,
                 MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "venue_name":
            meeting.venue_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            meeting.club.name,
            "participant_count":
            participant_count,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 상세 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 상세 조회 중 오류가 발생했습니다")


@router.post("/meetings/rounding")
async def create_admin_rounding_meeting(meeting_data: dict,
                                        db: Session = Depends(get_db),
                                        current_user: dict = Depends(get_admin_user)):
    """관리자용 라운딩 모임 생성"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole
        from utils import generate_id
        from datetime import datetime

        # 클럽 존재 확인
        club = db.query(Club).filter(Club.id == meeting_data.get('club_id')).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다.")

        # 모임 생성
        meeting = Meeting(name=meeting_data.get('name'),
                          description=meeting_data.get('description'),
                          location=meeting_data.get('location'),
                          meeting_time=datetime.fromisoformat(meeting_data.get('meeting_time').replace('Z', '+00:00'))
                          if meeting_data.get('meeting_time') else None,
                          tee_time=datetime.strptime(meeting_data.get('tee_time'), '%H:%M').time()
                          if meeting_data.get('tee_time') and ':' in meeting_data.get('tee_time') else None,
                          max_participants=meeting_data.get('max_participants', 4),
                          meeting_type=MeetingType.ROUND,
                          meeting_subtype=meeting_data.get('meeting_subtype'),
                          total_cost=meeting_data.get('total_cost'),
                          green_fee=meeting_data.get('green_fee'),
                          caddy_fee=meeting_data.get('caddy_fee'),
                          cart_fee=meeting_data.get('cart_fee'),
                          settlement_method=meeting_data.get('settlement_method'),
                          course_name=meeting_data.get('course_name'),
                          hole_count=meeting_data.get('hole_count'),
                          reservation_name=meeting_data.get('reservation_name'),
                          club_id=meeting_data.get('club_id'),
                          status=MeetingStatus.SCHEDULED)

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 매니저로 자동 참가
        participant = MeetingParticipant(meeting_id=meeting.id,
                                         user_id=current_user['id'],
                                         status=MeetingParticipantStatus.CONFIRMED,
                                         role=MeetingParticipantRole.ORGANIZER)
        db.add(participant)
        db.commit()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            1,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except Exception as e:
        logger.error(f"관리자 라운딩 모임 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라운딩 모임 생성 중 오류가 발생했습니다")


@router.post("/meetings/event")
async def create_admin_event_meeting(meeting_data: dict,
                                     db: Session = Depends(get_db),
                                     current_user: dict = Depends(get_admin_user)):
    """관리자용 이벤트 모임 생성"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole
        from utils import generate_id
        from datetime import datetime

        # 클럽 존재 확인
        club = db.query(Club).filter(Club.id == meeting_data.get('club_id')).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다.")

        # 모임 생성
        meeting = Meeting(name=meeting_data.get('name'),
                          description=meeting_data.get('description'),
                          meeting_time=datetime.fromisoformat(meeting_data.get('meeting_time').replace('Z', '+00:00'))
                          if meeting_data.get('meeting_time') else None,
                          max_participants=meeting_data.get('max_participants', 20),
                          meeting_type=MeetingType.SOCIAL,
                          venue_name=meeting_data.get('venue_name'),
                          social_cost=meeting_data.get('social_cost'),
                          social_settlement_method=meeting_data.get('social_settlement_method'),
                          club_id=meeting_data.get('club_id'),
                          status=MeetingStatus.SCHEDULED)

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 매니저로 자동 참가
        participant = MeetingParticipant(meeting_id=meeting.id,
                                         user_id=current_user['id'],
                                         status=MeetingParticipantStatus.CONFIRMED,
                                         role=MeetingParticipantRole.ORGANIZER)
        db.add(participant)
        db.commit()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "venue_name":
            meeting.venue_name,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            1,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except Exception as e:
        logger.error(f"관리자 이벤트 모임 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이벤트 모임 생성 중 오류가 발생했습니다")


@router.post("/meetings")
async def create_admin_meeting(meeting_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 생성 (일반)"""
    # 관리자용 모임 생성은 별도 엔드포인트를 사용하세요
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="관리자용 모임 생성은 /admin/meetings/rounding 또는 /admin/meetings/event 엔드포인트를 사용하세요")


@router.put("/meetings/{meeting_id}")
async def update_admin_meeting(meeting_id: int,
                               meeting_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 수정"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingParticipantStatus
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 모임 데이터 업데이트
        update_fields = ['name', 'description', 'location', 'meeting_time', 'max_participants', 'status']
        for field in update_fields:
            if field in meeting_data:
                setattr(meeting, field, meeting_data[field])

        meeting.updated_at = get_kst_now()
        db.commit()
        db.refresh(meeting)

        # 클럽 정보 조회
        club = db.query(Club).filter(Club.id == meeting.club_id).first()

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            and_(MeetingParticipant.meeting_id == meeting.id,
                 MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "venue_name":
            meeting.venue_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            participant_count,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 수정 중 오류가 발생했습니다")


@router.delete("/meetings/{meeting_id}")
async def delete_admin_meeting(meeting_id: int,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 삭제"""
    try:
        logger.info(f"관리자 모임 삭제 시작 - meeting_id: {meeting_id}")

        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다")

        # 모임 삭제 (실제 삭제 또는 소프트 삭제)
        # 참가자, 팀 등 관련 데이터도 함께 삭제됨 (CASCADE 설정)
        db.delete(meeting)
        db.commit()

        logger.info(f"관리자 모임 삭제 완료 - meeting_id: {meeting_id}")
        return {"message": "모임이 삭제되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 오류: {str(e)}")


@router.get("/payments")
async def get_admin_payments(page: int = 1,
                             size: int = 20,
                             status_filter: Optional[str] = None,
                             user_id: Optional[int] = None,
                             db: Session = Depends(get_db),
                             current_user: dict = Depends(get_admin_user)):
    """관리자용 결제 목록 조회"""
    try:
        from models import Payment, PaymentStatus, User
        from schemas import PaymentResponse
        from sqlalchemy import desc

        query = db.query(Payment)

        # 필터 적용
        if status_filter:
            query = query.filter(Payment.status == PaymentStatus(status_filter))
        if user_id:
            query = query.filter(Payment.user_id == user_id)

        # 총 개수 조회
        total = query.count()

        # 정렬 및 페이징
        payments = query.order_by(desc(Payment.created_at))\
                       .offset((page - 1) * size)\
                       .limit(size)\
                       .all()

        # 응답 생성
        payment_responses = []
        for payment in payments:
            payment_responses.append({
                "id": payment.id,
                "user_id": payment.user_id,
                "subscription_id": payment.subscription_id,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status.value,
                "payment_method": payment.payment_method.value,
                "payment_provider": getattr(payment, 'payment_provider', 'TOSS_PAYMENTS'),
                "provider_payment_id": getattr(payment, 'provider_payment_id', ''),
                "payment_key": payment.payment_key,
                "order_id": payment.order_id,
                "order_name": payment.order_name,
                "transaction_id": payment.transaction_id,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "canceled_at": payment.canceled_at.isoformat() if payment.canceled_at else None,
                "cancel_reason": payment.cancel_reason,
                "description": payment.description,
                "created_at": payment.created_at.isoformat() if payment.created_at else None,
                "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
            })

        return {"data": payment_responses, "total": total, "page": page, "size": size}

    except Exception as e:
        logger.error(f"관리자 결제 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="결제 목록 조회 중 오류가 발생했습니다")


@router.get("/plans")
async def get_admin_plans(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 플랜 목록 조회"""
    try:
        from models import Plan
        from sqlalchemy import desc

        # 간단한 플랜 목록 조회
        plans = db.query(Plan).order_by(desc(Plan.created_at)).limit(20).all()

        # 완전한 플랜 정보 응답 생성
        plan_list = []
        for plan in plans:
            plan_list.append({
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "detailed_description": getattr(plan, 'detailed_description', ''),
                "type": plan.type.value if plan.type else "BASIC",
                "price": float(plan.price) if plan.price else 0,
                "billing_cycle": plan.billing_cycle.value if plan.billing_cycle else "MONTHLY",
                "features": plan.features,
                "max_clubs": plan.max_clubs,
                "max_members_per_club": plan.max_members_per_club,
                "max_meetings_per_month": plan.max_meetings_per_month,
                "is_active": plan.is_active,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            })

        return {"data": plan_list, "total": len(plan_list)}

    except Exception as e:
        logger.error(f"관리자 플랜 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.post("/payments/{payment_id}/cancel")
async def admin_cancel_payment(payment_id: int,
                               cancel_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 결제 취소 (정책에 따른 환불/구독해지)"""
    try:
        from models import Payment, PaymentStatus, ClubMembership, MeetingParticipant, Meeting, MeetingType, Subscription
        from datetime import datetime, date

        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="결제 내역을 찾을 수 없습니다")

        if payment.status != PaymentStatus.SUCCEEDED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="취소 가능한 결제가 아닙니다")

        # 결제 취소 정책 확인
        user_id = payment.user_id
        payment_date = payment.created_at.date()
        today = date.today()

        # 1. 사용자 활동 확인 (팀생성/모임개설/이벤트개설)
        has_activity = False

        # 클럽 멤버십 확인 (사용자가 클럽에 가입한 경우)
        club_memberships_count = db.query(ClubMembership).filter(ClubMembership.user_id == user_id,
                                                                 ClubMembership.created_at >= payment_date).count()

        # 모임 참가 확인 (사용자가 모임에 참가한 경우)
        meeting_participations_count = db.query(MeetingParticipant).filter(
            MeetingParticipant.user_id == user_id, MeetingParticipant.created_at >= payment_date).count()

        # 소셜 모임 생성 확인 (사용자가 소셜 모임을 생성한 경우)
        # Phase 3에서 Event 모델 제거됨, Meeting (SOCIAL 타입)으로 대체
        socials_count = db.query(Meeting).filter(
            Meeting.meeting_type == MeetingType.SOCIAL,
            Meeting.club_id.in_(db.query(ClubMembership.club_id).filter(ClubMembership.user_id == user_id)),
            Meeting.created_at >= payment_date).count()

        if club_memberships_count > 0 or meeting_participations_count > 0 or socials_count > 0:
            has_activity = True

        # 2. 결제일 확인 (당일 여부)
        is_same_day = payment_date == today

        # 3. 취소 정책 결정
        if is_same_day and not has_activity:
            # 당일 + 활동 없음 → 즉시 환불
            cancel_type = "refund"
            cancel_message = "당일 결제로 활동이 없어 즉시 환불 처리됩니다."
        else:
            # 활동 있음 또는 당일이 아님 → 구독 해지 (다음달부터)
            cancel_type = "subscription_cancel"
            cancel_message = "활동이 있거나 당일이 아니어서 다음달부터 구독이 해지됩니다."

        # 4. 취소 처리 실행
        if cancel_type == "refund":
            # 즉시 환불 처리
            if payment.payment_key:
                # 실제 토스페이먼츠 결제인 경우
                from utils.toss_payments import toss_payments

                try:
                    toss_result = toss_payments.cancel_payment(payment_key=payment.payment_key,
                                                               cancel_reason=cancel_data.get("reason", "관리자 취소"),
                                                               cancel_amount=cancel_data.get("amount"))

                    # 결제 상태 업데이트
                    payment.status = PaymentStatus.CANCELED
                    payment.canceled_at = datetime.now()
                    payment.cancel_reason = cancel_data.get("reason", "관리자 취소")

                    db.commit()

                    return {
                        "success": True,
                        "cancel_type": "refund",
                        "message": "결제가 성공적으로 취소되었습니다. (즉시 환불)",
                        "toss_result": toss_result,
                        "policy_info": {
                            "is_same_day": is_same_day,
                            "has_activity": has_activity,
                            "club_memberships": club_memberships_count,
                            "meeting_participations": meeting_participations_count,
                            "socials_created": socials_count
                        }
                    }

                except Exception as toss_error:
                    logger.error(f"토스페이먼츠 취소 실패: {str(toss_error)}")

                    # 테스트 결제키의 경우 내부적으로만 취소 처리
                    if "404" in str(toss_error) or "Not Found" in str(toss_error):
                        logger.info("테스트 결제키로 판단되어 내부적으로만 취소 처리합니다.")
                        payment.status = PaymentStatus.CANCELED
                        payment.canceled_at = datetime.now()
                        payment.cancel_reason = cancel_data.get("reason", "관리자 취소")

                        db.commit()

                        return {
                            "success": True,
                            "cancel_type": "refund",
                            "message": "결제가 성공적으로 취소되었습니다. (테스트 결제 - 내부 처리)",
                            "policy_info": {
                                "is_same_day": is_same_day,
                                "has_activity": has_activity,
                                "club_memberships": club_memberships_count,
                                "meeting_participations": meeting_participations_count,
                                "socials_created": socials_count
                            }
                        }
                    else:
                        # 실제 에러인 경우
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                            detail=f"결제 취소 실패: {str(toss_error)}")
            else:
                # 토스페이먼츠 키가 없는 경우 내부적으로만 취소 처리
                payment.status = PaymentStatus.CANCELED
                payment.canceled_at = datetime.now()
                payment.cancel_reason = cancel_data.get("reason", "관리자 취소")

                db.commit()

                return {
                    "success": True,
                    "cancel_type": "refund",
                    "message": "결제가 성공적으로 취소되었습니다. (즉시 환불)",
                    "policy_info": {
                        "is_same_day": is_same_day,
                        "has_activity": has_activity,
                        "club_memberships": club_memberships_count,
                        "meeting_participations": meeting_participations_count,
                        "socials_created": socials_count
                    }
                }

        else:  # subscription_cancel
            # 구독 해지 처리 (다음달부터)
            # 활성 구독 찾기
            active_subscription = db.query(Subscription).filter(Subscription.user_id == user_id,
                                                                Subscription.status == "ACTIVE").first()

            if active_subscription:
                # 구독 상태를 다음달 해지로 변경
                active_subscription.status = "CANCELED"
                active_subscription.CANCELED_at = datetime.now()
                active_subscription.cancel_reason = cancel_data.get("reason", "관리자 취소")

                db.commit()

                return {
                    "success": True,
                    "cancel_type": "subscription_cancel",
                    "message": "구독이 다음달부터 해지됩니다. (현재 달은 유지)",
                    "policy_info": {
                        "is_same_day": is_same_day,
                        "has_activity": has_activity,
                        "club_memberships": club_memberships_count,
                        "meeting_participations": meeting_participations_count,
                        "socials_created": socials_count,
                        "subscription_id": active_subscription.id
                    }
                }
            else:
                # 활성 구독이 없는 경우 결제만 취소
                payment.status = PaymentStatus.CANCELED
                payment.canceled_at = datetime.now()
                payment.cancel_reason = cancel_data.get("reason", "관리자 취소")

                db.commit()

                return {
                    "success": True,
                    "cancel_type": "payment_cancel",
                    "message": "결제가 취소되었습니다. (활성 구독 없음)",
                    "policy_info": {
                        "is_same_day": is_same_day,
                        "has_activity": has_activity,
                        "club_memberships": club_memberships_count,
                        "meeting_participations": meeting_participations_count,
                        "socials_created": socials_count
                    }
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 결제 취소 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 오류: {str(e)}")


@router.get("/refunds")
async def get_admin_refunds(page: int = 1,
                            size: int = 20,
                            status_filter: Optional[str] = None,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 환불 내역 조회"""
    try:
        from models import Payment, PaymentStatus, User
        from sqlalchemy import desc

        # 취소된 결제들을 환불 내역으로 조회
        query = db.query(Payment).join(User, Payment.user_id == User.id)\
                                .filter(Payment.status == PaymentStatus.FAILED)\
                                .filter(Payment.canceled_at.isnot(None))

        # 총 개수 조회
        total = query.count()

        # 정렬 및 페이징
        refunds = query.order_by(desc(Payment.canceled_at))\
                      .offset((page - 1) * size)\
                      .limit(size)\
                      .all()

        # 응답 생성
        refund_responses = []
        for refund in refunds:
            refund_responses.append({
                "id": refund.id,
                "user_id": refund.user_id,
                "user_name": refund.user.nickname if refund.user else "알 수 없음",
                "user_email": refund.user.email if refund.user else "알 수 없음",
                "amount": float(refund.amount),
                "currency": refund.currency,
                "payment_method": refund.payment_method.value if refund.payment_method else "알 수 없음",
                "order_name": refund.order_name,
                "cancel_reason": refund.cancel_reason,
                "canceled_at": refund.canceled_at.isoformat() if refund.canceled_at else None,
                "created_at": refund.created_at.isoformat() if refund.created_at else None,
                "payment_key": refund.payment_key
            })

        return {
            "data": refund_responses,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size
        }

    except Exception as e:
        logger.error(f"관리자 환불 내역 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.post("/plans")
async def create_admin_plan(plan_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 플랜 생성"""
    try:
        from models import Plan, PlanType, BillingCycle
        import secrets
        import string

        # 플랜 ID 생성
        chars = string.ascii_lowercase + string.digits
        plan_id = ''.join(secrets.choice(chars) for _ in range(20))

        # 플랜 생성
        plan = Plan(id=plan_id,
                    name=plan_data.get('name'),
                    description=plan_data.get('description'),
                    detailed_description=plan_data.get('detailed_description', ''),
                    type=PlanType(plan_data.get('type', 'BASIC')),
                    price=plan_data.get('price', 0),
                    billing_cycle=BillingCycle(plan_data.get('billing_cycle', 'MONTHLY')),
                    features=plan_data.get('features', {}),
                    max_clubs=plan_data.get('max_clubs'),
                    max_members_per_club=plan_data.get('max_members_per_club'),
                    max_meetings_per_month=plan_data.get('max_meetings_per_month'),
                    is_active=plan_data.get('is_active', True))

        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "detailed_description": getattr(plan, 'detailed_description', ''),
            "type": plan.type.value,
            "price": float(plan.price),
            "billing_cycle": plan.billing_cycle.value,
            "features": plan.features,
            "max_clubs": plan.max_clubs,
            "max_members_per_club": plan.max_members_per_club,
            "max_meetings_per_month": plan.max_meetings_per_month,
            "is_active": plan.is_active,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
        }

    except Exception as e:
        logger.error(f"관리자 플랜 생성 중 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"플랜 생성 실패: {str(e)}")


@router.put("/plans/{plan_id}")
async def update_admin_plan(plan_id: int,
                            plan_data: dict,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 플랜 수정"""
    try:
        from models import Plan, PlanType, BillingCycle

        # 플랜 조회
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")

        # 플랜 정보 업데이트
        if 'name' in plan_data:
            plan.name = plan_data['name']
        if 'description' in plan_data:
            plan.description = plan_data['description']
        if 'detailed_description' in plan_data:
            plan.detailed_description = plan_data['detailed_description']
        if 'type' in plan_data:
            plan.type = PlanType(plan_data['type'])
        if 'price' in plan_data:
            plan.price = plan_data['price']
        if 'billing_cycle' in plan_data:
            plan.billing_cycle = BillingCycle(plan_data['billing_cycle'])
        if 'features' in plan_data:
            plan.features = plan_data['features']
        if 'max_clubs' in plan_data:
            plan.max_clubs = plan_data['max_clubs']
        if 'max_members_per_club' in plan_data:
            plan.max_members_per_club = plan_data['max_members_per_club']
        if 'max_meetings_per_month' in plan_data:
            plan.max_meetings_per_month = plan_data['max_meetings_per_month']
        if 'is_active' in plan_data:
            plan.is_active = plan_data['is_active']

        db.commit()
        db.refresh(plan)

        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "detailed_description": getattr(plan, 'detailed_description', ''),
            "type": plan.type.value,
            "price": float(plan.price),
            "billing_cycle": plan.billing_cycle.value,
            "features": plan.features,
            "max_clubs": plan.max_clubs,
            "max_members_per_club": plan.max_members_per_club,
            "max_meetings_per_month": plan.max_meetings_per_month,
            "is_active": plan.is_active,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 플랜 수정 중 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"플랜 수정 실패: {str(e)}")


@router.delete("/plans/{plan_id}")
async def delete_admin_plan(plan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 플랜 삭제"""
    try:
        from models import Plan, Subscription

        # 플랜 조회
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")

        # 활성 구독이 있는지 확인
        active_subscriptions = db.query(Subscription).filter(Subscription.plan_id == plan_id,
                                                             Subscription.status == "ACTIVE").count()

        if active_subscriptions > 0:
            raise HTTPException(status_code=400, detail="활성 구독이 있는 플랜은 삭제할 수 없습니다")

        # 플랜 삭제
        db.delete(plan)
        db.commit()

        return {"message": "플랜이 성공적으로 삭제되었습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 플랜 삭제 중 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"플랜 삭제 실패: {str(e)}")


@router.get("/subscriptions")
async def get_admin_subscriptions(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 구독 목록 조회"""
    try:
        from models import Subscription
        from sqlalchemy import desc

        # 간단한 구독 목록 조회
        subscriptions = db.query(Subscription).order_by(desc(Subscription.created_at)).limit(20).all()

        # 간단한 응답 생성
        subscription_list = []
        for subscription in subscriptions:
            subscription_list.append({
                "id":
                subscription.id,
                "user_id":
                subscription.user_id,
                "plan_id":
                subscription.plan_id,
                "status":
                subscription.status.value,
                "start_date":
                subscription.start_date.isoformat() if subscription.start_date else None,
                "end_date":
                subscription.end_date.isoformat() if subscription.end_date else None,
                "created_at":
                subscription.created_at.isoformat() if subscription.created_at else None
            })

        return {"data": subscription_list, "total": len(subscription_list)}

    except Exception as e:
        logger.error(f"관리자 구독 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.get("/terms")
async def get_admin_terms(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 약관 목록 조회"""
    try:
        from sqlalchemy import desc

        # 간단한 약관 목록 조회
        terms = db.query(Terms).order_by(desc(Terms.created_at)).limit(20).all()

        # 간단한 응답 생성
        term_list = []
        for term in terms:
            term_list.append({
                "id": term.id,
                "title": term.title,
                "type": term.type.value,
                "content": term.content,
                "is_active": term.is_active,
                "is_required": term.is_required,
                "published_at": term.published_at.isoformat() if term.published_at else None,
                "created_at": term.created_at.isoformat() if term.created_at else None
            })

        return {"data": term_list, "total": len(term_list)}

    except Exception as e:
        logger.error(f"관리자 약관 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


# =============================================================================
# 관리자용 이벤트 API (레거시 - Phase 3에서 Event 모델 제거됨)
# =============================================================================
# 소셜 모임은 /api/v1/socials API를 사용하세요

# @router.get("/events")
# @router.get("/events/{event_id}")
# 위 엔드포인트들은 Event 모델 제거로 작동하지 않음
# Event 관련 함수들은 Phase 3에서 Event 모델 제거로 더 이상 작동하지 않습니다.
# 소셜 모임 관리는 /api/v1/socials API를 사용하세요.


@router.post("/terms")
async def create_admin_terms(terms_data: dict,
                             db: Session = Depends(get_db),
                             current_user: dict = Depends(get_admin_user)):
    """관리자용 약관 생성"""
    try:
        import secrets
        import string

        # ID 생성
        chars = string.ascii_lowercase + string.digits
        term_id = ''.join(secrets.choice(chars) for _ in range(20))

        # 같은 타입의 기존 약관들을 비활성화 (새 약관이 활성화될 경우)
        if terms_data.get('is_active', True):
            db.query(Terms).filter(Terms.type == TermsType(terms_data.get('type', 'SERVICE'))).update(
                {"is_active": False})

        # 약관 생성
        new_term = Terms(id=term_id,
                         type=TermsType(terms_data.get('type', 'SERVICE')),
                         title=terms_data.get('title', ''),
                         content=terms_data.get('content', ''),
                         is_active=terms_data.get('is_active', True),
                         is_required=terms_data.get('is_required', False),
                         published_at=datetime.now())

        db.add(new_term)
        db.commit()
        db.refresh(new_term)

        return {
            "id": new_term.id,
            "title": new_term.title,
            "type": new_term.type.value,
            "content": new_term.content,
            "is_active": new_term.is_active,
            "is_required": new_term.is_required,
            "published_at": new_term.published_at.isoformat() if new_term.published_at else None,
            "created_at": new_term.created_at.isoformat() if new_term.created_at else None
        }

    except Exception as e:
        logger.error(f"관리자 약관 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 생성 중 오류가 발생했습니다")


# 약관 관리 API (타입 기반) - 더 구체적인 경로를 먼저 정의
@router.put("/terms/{terms_type}")
async def update_terms(terms_type: str,
                       terms_data: dict,
                       db: Session = Depends(get_db),
                       current_user: dict = Depends(get_admin_user)):
    """약관 수정 (타입 기반)"""
    try:

        # 약관 타입 매핑
        type_mapping = {
            'service': 'SERVICE',
            'privacy': 'PRIVACY',
            'privacy_collection': 'PRIVACY_COLLECTION',
            'marketing': 'MARKETING'
        }

        if terms_type not in type_mapping:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 약관 타입입니다")

        db_terms_type = type_mapping[terms_type]

        # 필수 필드 검증
        if 'title' not in terms_data or 'content' not in terms_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="제목과 내용은 필수입니다")

        # 기존 약관 조회
        terms = db.query(Terms).filter(Terms.type == db_terms_type, Terms.is_active == True).first()

        if terms:
            # 기존 약관 수정
            terms.title = terms_data['title']
            terms.content = terms_data['content']
            terms.updated_at = get_kst_now()
        else:
            # 새 약관 생성
            terms = Terms(type=db_terms_type, title=terms_data['title'], content=terms_data['content'], is_active=True)
            db.add(terms)

        db.commit()

        return {"message": "약관이 성공적으로 저장되었습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"약관 저장 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


@router.put("/terms/id/{term_id}")
async def update_admin_terms(term_id: int,
                             terms_data: dict,
                             db: Session = Depends(get_db),
                             current_user: dict = Depends(get_admin_user)):
    """관리자용 약관 수정"""
    try:
        import secrets
        import string

        logger.info(f"약관 수정 시작 - term_id: {term_id}, data: {terms_data}")

        # 기존 약관 조회
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            logger.error(f"약관을 찾을 수 없음 - term_id: {term_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")

        logger.info(f"기존 약관 정보 - type: {term.type}")

        # 약관 정보 업데이트
        if 'type' in terms_data:
            term.type = TermsType(terms_data['type'])
        if 'title' in terms_data:
            term.title = terms_data['title']
        if 'content' in terms_data:
            term.content = terms_data['content']
        if 'is_active' in terms_data:
            term.is_active = terms_data['is_active']
        if 'is_required' in terms_data:
            term.is_required = terms_data['is_required']

        term.updated_at = datetime.now()

        db.commit()
        db.refresh(term)

        return {
            "id": term.id,
            "title": term.title,
            "type": term.type.value,
            "content": term.content,
            "is_active": term.is_active,
            "is_required": term.is_required,
            "published_at": term.published_at.isoformat() if term.published_at else None,
            "created_at": term.created_at.isoformat() if term.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 수정 중 오류가 발생했습니다")


@router.put("/terms/{term_id}/activate")
async def activate_admin_terms(term_id: int,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 약관 활성화 (같은 타입의 다른 버전들은 비활성화)"""
    try:
        # 활성화할 약관 조회
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")

        # 같은 타입의 모든 약관을 비활성화
        db.query(Terms).filter(Terms.type == term.type, Terms.id != term_id).update({"is_active": False})

        # 선택된 약관을 활성화
        term.is_active = True

        db.commit()
        db.refresh(term)

        return {
            "message": "약관이 활성화되었습니다",
            "term": {
                "id": term.id,
                "title": term.title,
                "type": term.type.value,
                "is_active": term.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 활성화 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 활성화 중 오류가 발생했습니다")


@router.put("/terms/{term_id}/deactivate")
async def deactivate_admin_terms(term_id: int,
                                 db: Session = Depends(get_db),
                                 current_user: dict = Depends(get_admin_user)):
    """관리자용 약관 비활성화"""
    try:
        # 비활성화할 약관 조회
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")

        # 약관 비활성화
        term.is_active = False

        db.commit()
        db.refresh(term)

        return {
            "message": "약관이 비활성화되었습니다",
            "term": {
                "id": term.id,
                "title": term.title,
                "type": term.type.value,
                "is_active": term.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 비활성화 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 비활성화 중 오류가 발생했습니다")


@router.get("/notices")
async def get_admin_notices(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 공지사항 목록 조회"""
    try:
        from models import Notice
        from sqlalchemy import desc

        # 간단한 공지사항 목록 조회
        notices = db.query(Notice).order_by(desc(Notice.created_at)).limit(20).all()

        # 간단한 응답 생성
        notice_list = []
        for notice in notices:
            notice_list.append({
                "id": notice.id,
                "title": notice.title,
                "type": notice.type.value,
                "is_published": notice.is_published,
                "created_at": notice.created_at.isoformat() if notice.created_at else None
            })

        return {"data": notice_list, "total": len(notice_list)}

    except Exception as e:
        logger.error(f"관리자 공지사항 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.post("/notices")
async def create_admin_notice(notice_data: dict,
                              db: Session = Depends(get_db),
                              current_user: dict = Depends(get_admin_user)):
    """관리자용 공지사항 생성"""
    try:
        from models import Notice
        from utils import generate_id

        # 필수 필드 검증
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in notice_data or not notice_data[field]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} 필드는 필수입니다")

        # 공지사항 생성
        new_notice = Notice(title=notice_data['title'],
                            content=notice_data['content'],
                            author_id=current_user['id'],
                            is_important=notice_data.get('is_important', False))

        db.add(new_notice)
        db.commit()
        db.refresh(new_notice)

        # 모든 사용자에게 새 시스템 공지사항 알림 전송
        try:
            from utils.notification_service import create_notice_notification
            from models import User, UserStatus

            # 모든 활성 사용자 조회
            active_users = db.query(User).filter(User.status == UserStatus.ACTIVE).all()

            for user in active_users:
                create_notice_notification(db=db, user_id=user.id, notice_title=notice_data['title'])
        except Exception as e:
            logger.error(f"시스템 공지사항 알림 전송 실패: {str(e)}")

        return {
            "id": new_notice.id,
            "title": new_notice.title,
            "content": new_notice.content,
            "is_important": new_notice.is_important,
            "created_at": new_notice.created_at.isoformat() if new_notice.created_at else None,
            "updated_at": new_notice.updated_at.isoformat() if new_notice.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 생성 중 오류: {str(e)}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"공지사항 생성 중 오류가 발생했습니다: {str(e)}")


@router.put("/notices/{notice_id}")
async def update_admin_notice(notice_id: int,
                              notice_data: dict,
                              db: Session = Depends(get_db),
                              current_user: dict = Depends(get_admin_user)):
    """관리자용 공지사항 수정"""
    try:
        from models import Notice

        notice = db.query(Notice).filter(Notice.id == notice_id).first()

        if not notice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")

        # 필드 업데이트
        if 'title' in notice_data:
            notice.title = notice_data['title']
        if 'content' in notice_data:
            notice.content = notice_data['content']
        if 'is_important' in notice_data:
            notice.is_important = notice_data['is_important']

        notice.updated_at = get_kst_now()

        db.commit()
        db.refresh(notice)

        return {
            "id": notice.id,
            "title": notice.title,
            "content": notice.content,
            "is_important": notice.is_important,
            "created_at": notice.created_at.isoformat() if notice.created_at else None,
            "updated_at": notice.updated_at.isoformat() if notice.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공지사항 수정 중 오류가 발생했습니다")


@router.delete("/notices/{notice_id}")
async def delete_admin_notice(notice_id: int,
                              db: Session = Depends(get_db),
                              current_user: dict = Depends(get_admin_user)):
    """관리자용 공지사항 삭제"""
    try:
        from models import Notice

        notice = db.query(Notice).filter(Notice.id == notice_id).first()

        if not notice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")

        # 소프트 삭제
        notice.deleted_at = get_kst_now()

        db.commit()

        return {"message": "공지사항이 성공적으로 삭제되었습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공지사항 삭제 중 오류가 발생했습니다")


@router.get("/inquiries")
async def get_admin_inquiries(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 문의 목록 조회"""
    try:
        from models import Inquiry
        from sqlalchemy import desc

        # 간단한 문의 목록 조회 (user 관계 포함)
        inquiries = db.query(Inquiry).join(User).order_by(desc(Inquiry.created_at)).limit(20).all()

        # 간단한 응답 생성
        inquiry_list = []
        for inquiry in inquiries:
            inquiry_list.append({
                "id": inquiry.id,
                "title": inquiry.title,
                "type": inquiry.type.value,
                "status": inquiry.status.value,
                "priority": inquiry.priority,
                "user_nickname": inquiry.user.nickname if inquiry.user else "알 수 없음",
                "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None
            })

        return {"data": inquiry_list, "total": len(inquiry_list)}

    except Exception as e:
        logger.error(f"관리자 문의 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="문의 목록 조회 중 오류가 발생했습니다")


@router.get("/inquiries/{inquiry_id}")
async def get_admin_inquiry_detail(inquiry_id: int,
                                   db: Session = Depends(get_db),
                                   current_user: dict = Depends(get_admin_user)):
    """관리자용 문의 상세 조회"""
    try:
        from models import Inquiry, InquiryResponse

        # 문의 상세 조회
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다")

        # 답변 목록 조회
        responses = db.query(InquiryResponse).filter(InquiryResponse.inquiry_id == inquiry_id).order_by(
            InquiryResponse.created_at).all()

        # 응답 생성
        response_list = []
        for response in responses:
            response_list.append({
                "id": response.id,
                "content": response.content,
                "is_admin": response.is_admin,
                "created_at": response.created_at.isoformat() if response.created_at else None
            })

        return {
            "inquiry": {
                "id": inquiry.id,
                "title": inquiry.title,
                "content": inquiry.content,
                "type": inquiry.type.value,
                "status": inquiry.status.value,
                "priority": inquiry.priority,
                "user_nickname": inquiry.user.nickname if inquiry.user else "알 수 없음",
                "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None
            },
            "responses": response_list
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 문의 상세 조회 중 오류: {str(e)}")
        import traceback
        logger.error(f"상세 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"문의 상세 조회 중 오류가 발생했습니다: {str(e)}")


@router.put("/inquiries/{inquiry_id}/status")
async def update_admin_inquiry_status(inquiry_id: int,
                                      status_data: dict,
                                      db: Session = Depends(get_db),
                                      current_user: dict = Depends(get_admin_user)):
    """관리자용 문의 상태 업데이트"""
    try:
        from models import Inquiry, InquiryStatus

        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다")

        new_status = status_data.get('status')
        if new_status:
            inquiry.status = InquiryStatus(new_status)
            db.commit()

        return {"message": "문의 상태가 성공적으로 업데이트되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 문의 상태 업데이트 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="문의 상태 업데이트 중 오류가 발생했습니다")


@router.post("/inquiries/{inquiry_id}/responses")
async def create_admin_inquiry_response(inquiry_id: int,
                                        response_data: dict,
                                        db: Session = Depends(get_db),
                                        current_user: dict = Depends(get_admin_user)):
    """관리자용 문의 답변 생성"""
    try:
        from models import Inquiry, InquiryResponse
        import secrets
        import string

        # 문의 존재 확인
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다")

        # 답변 ID 생성
        chars = string.ascii_lowercase + string.digits
        response_id = ''.join(secrets.choice(chars) for _ in range(20))

        # 답변 생성
        new_response = InquiryResponse(
            id=response_id,
            inquiry_id=inquiry_id,
            content=response_data.get('content', ''),
            is_admin=True,  # 관리자가 작성한 답변
            is_internal=response_data.get('is_internal', False))

        db.add(new_response)
        db.commit()

        # 문의 작성자에게 답변 알림 전송
        try:
            from utils.notification_service import create_inquiry_response_notification
            create_inquiry_response_notification(db=db,
                                                 user_id=inquiry.user_id,
                                                 inquiry_title=inquiry.title,
                                                 response_content=response_data.get('content', ''))
        except Exception as e:
            logger.error(f"문의 답변 알림 전송 실패: {str(e)}")

        return {"message": "답변이 성공적으로 생성되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 문의 답변 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="문의 답변 생성 중 오류가 발생했습니다")


# =============================================================================
# 관리자용 알림 관리 API
# =============================================================================


@router.get("/notifications")
async def get_admin_notifications(page: int = 1,
                                  limit: int = 20,
                                  status_filter: Optional[str] = None,
                                  type_filter: Optional[str] = None,
                                  db: Session = Depends(get_db),
                                  current_user: dict = Depends(get_admin_user)):
    """관리자용 알림 목록 조회"""
    try:
        from models import Notification, NotificationType, NotificationStatus
        from sqlalchemy import desc

        # 페이지네이션 계산
        offset = (page - 1) * limit

        # 알림 조회 쿼리
        query = db.query(Notification).filter(Notification.user_id == current_user.get('id'))

        if status_filter:
            # DB에 저장된 값은 문자열이므로 Enum.value로 비교
            status_value = NotificationStatus(status_filter).value if hasattr(
                NotificationStatus(status_filter), 'value') else str(NotificationStatus(status_filter))
            query = query.filter(Notification.status == status_value)

        if type_filter:
            # DB에 저장된 값은 문자열이므로 Enum.value로 비교
            type_value = NotificationType(type_filter).value if hasattr(NotificationType(type_filter),
                                                                        'value') else str(NotificationType(type_filter))
            query = query.filter(Notification.type == type_value)

        total = query.count()
        notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()

        notification_responses = []
        for notification in notifications:
            notification_responses.append({
                "id":
                notification.id,
                "user_id":
                notification.user_id,
                "type":
                notification.type.value if hasattr(notification.type, 'value') else str(notification.type),
                "title":
                notification.title,
                "content":
                notification.content,
                "status":
                notification.status.value if hasattr(notification.status, 'value') else str(notification.status),
                "read_at":
                notification.read_at.isoformat() if notification.read_at else None,
                "created_at":
                notification.created_at.isoformat() if notification.created_at else None
            })

        return notification_responses

    except Exception as e:
        logger.error(f"관리자 알림 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="알림 목록 조회 중 오류가 발생했습니다")


@router.put("/notifications/{notification_id}/read")
async def mark_admin_notification_as_read(notification_id: int,
                                          db: Session = Depends(get_db),
                                          current_user: dict = Depends(get_admin_user)):
    """관리자용 알림 읽음 처리"""
    try:
        from models import Notification, NotificationStatus
        from datetime import datetime

        # 알림 조회
        notification = db.query(Notification).filter(Notification.id == notification_id,
                                                     Notification.user_id == current_user.get('id')).first()

        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다")

        # 읽음 처리
        notification.status = NotificationStatus.READ.value
        notification.read_at = datetime.now()

        db.commit()

        return {"message": "알림을 읽음으로 표시했습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 알림 읽음 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="알림 읽음 처리 중 오류가 발생했습니다")


@router.put("/notifications/read-all")
async def mark_all_admin_notifications_as_read(db: Session = Depends(get_db),
                                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모든 알림 읽음 처리"""
    try:
        from models import Notification, NotificationStatus
        from datetime import datetime

        # 사용자의 모든 읽지 않은 알림 조회
        unread_notifications = db.query(Notification).filter(
            Notification.user_id == current_user.get('id'),
            Notification.status == NotificationStatus.UNREAD.value).all()

        # 모든 알림을 읽음으로 처리
        for notification in unread_notifications:
            notification.status = NotificationStatus.READ.value
            notification.read_at = datetime.now()

        db.commit()

        return {"message": f"{len(unread_notifications)}개의 알림을 읽음으로 표시했습니다", "success": True}

    except Exception as e:
        logger.error(f"관리자 모든 알림 읽음 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="알림 읽음 처리 중 오류가 발생했습니다")


@router.get("/scores")
async def get_admin_scores(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 점수 목록 조회"""
    try:
        from models import Score
        from sqlalchemy import desc

        # 간단한 점수 목록 조회
        scores = db.query(Score).order_by(desc(Score.created_at)).limit(20).all()

        # 간단한 응답 생성
        score_list = []
        for score in scores:
            score_list.append({
                "id": score.id,
                "user_id": score.user_id,
                "meeting_id": score.meeting_id,
                "score": score.score,
                "handicap": score.handicap,
                "created_at": score.created_at.isoformat() if score.created_at else None
            })

        return {"data": score_list, "total": len(score_list)}

    except Exception as e:
        logger.error(f"관리자 점수 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.get("/meeting_participants")
async def get_admin_meeting_participants(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 참가자 목록 조회"""
    try:
        from models import MeetingParticipant
        from sqlalchemy import desc

        # 간단한 모임 참가자 목록 조회
        participants = db.query(MeetingParticipant).order_by(desc(MeetingParticipant.created_at)).limit(20).all()

        # 간단한 응답 생성
        participant_list = []
        for participant in participants:
            participant_list.append({
                "id": participant.id,
                "meeting_id": participant.meeting_id,
                "user_id": participant.user_id,
                "status": participant.status.value,
                "created_at": participant.created_at.isoformat() if participant.created_at else None
            })

        return {"data": participant_list, "total": len(participant_list)}

    except Exception as e:
        logger.error(f"관리자 모임 참가자 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.put("/meeting_participants/{participant_id}/status")
async def update_admin_participant_status(participant_id: int,
                                          status_data: dict,
                                          db: Session = Depends(get_db),
                                          current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 참가자 상태 업데이트"""
    try:
        from models import MeetingParticipant, MeetingParticipantStatus

        participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == participant_id).first()

        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임 참가자를 찾을 수 없습니다")

        # 상태 업데이트
        if 'status' in status_data:
            try:
                participant.status = MeetingParticipantStatus(status_data['status'])
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 상태입니다")

        participant.updated_at = get_kst_now()

        db.commit()
        db.refresh(participant)

        return {
            "message": "모임 참가자 상태가 성공적으로 업데이트되었습니다",
            "success": True,
            "participant": {
                "id": participant.id,
                "status": participant.status.value if hasattr(participant.status, 'value') else str(participant.status)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 모임 참가자 상태 업데이트 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 참가자 상태 업데이트 중 오류가 발생했습니다")


@router.get("/profile")
async def get_admin_profile(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """관리자 프로필 조회"""
    try:
        logger.info(f"Admin profile request - current_user: {current_user}")
        admin_id = current_user.get("id")
        logger.info(f"Admin profile request - admin_id: {admin_id}")

        if not admin_id:
            logger.error("Admin profile request - No admin_id in current_user")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")

        admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
        logger.info(f"Admin profile request - admin found: {admin is not None}")

        if not admin:
            logger.error(f"Admin profile request - Admin not found for id: {admin_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")

        response_data = {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": "ADMIN",
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
            "updated_at": admin.updated_at.isoformat() if admin.updated_at else None
        }

        logger.info(f"Admin profile response: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 프로필 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


@router.put("/profile")
async def update_admin_profile(profile_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자 프로필 수정"""
    try:
        admin_id = current_user.get("id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")

        admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")

        # 이름 업데이트
        if 'name' in profile_data:
            admin.name = profile_data['name']

        admin.updated_at = get_kst_now()
        db.commit()
        db.refresh(admin)

        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": "ADMIN",
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
            "updated_at": admin.updated_at.isoformat() if admin.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 프로필 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


@router.put("/password")
async def change_admin_password(password_data: dict,
                                db: Session = Depends(get_db),
                                current_user: dict = Depends(get_admin_user)):
    """관리자 비밀번호 변경"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")

        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="모든 비밀번호 필드를 입력해주세요")

        # 새 비밀번호와 확인 비밀번호 일치 확인
        if new_password != confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호와 확인 비밀번호가 일치하지 않습니다")

        # 비밀번호 유효성 검사
        from routers.auth import validate_password
        password_validation = validate_password(new_password)
        if not password_validation["is_valid"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="; ".join(password_validation["errors"]))

        admin = db.query(Admin).filter(Admin.id == user_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")

        # 현재 비밀번호 확인
        import hashlib
        current_password_hash = hashlib.sha256(current_password.encode()).hexdigest()
        if admin.password != current_password_hash:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다")

        # 새 비밀번호 해시화 및 저장
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        admin.password = new_password_hash
        admin.updated_at = get_kst_now()

        db.commit()

        return {"message": "비밀번호가 성공적으로 변경되었습니다", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 비밀번호 변경 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


# 약관 관리 API
@router.get("/terms/{terms_type}")
async def get_terms(terms_type: str, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """약관 조회"""
    try:

        # 약관 타입 검증
        # 약관 타입 매핑
        type_mapping = {
            'service': 'SERVICE',
            'privacy': 'PRIVACY',
            'privacy_collection': 'PRIVACY_COLLECTION',
            'marketing': 'MARKETING'
        }

        if terms_type not in type_mapping:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 약관 타입입니다")

        db_terms_type = type_mapping[terms_type]

        # 약관 조회
        terms = db.query(Terms).filter(Terms.type == db_terms_type, Terms.is_active == True).first()

        if not terms:
            # 기본 약관 생성
            terms = Terms(type=db_terms_type,
                          title=get_default_terms_title(terms_type),
                          content=get_default_terms_content(terms_type),
                          is_active=True)
            db.add(terms)
            db.commit()
            db.refresh(terms)

        return {
            "title": terms.title,
            "content": terms.content,
            "updated_at": terms.updated_at.isoformat() if terms.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"약관 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


def get_default_terms_title(terms_type: str) -> str:
    """기본 약관 제목 반환"""
    titles = {'service': '서비스 이용약관', 'privacy': '개인정보처리방침', 'collection': '개인정보 수집 및 이용동의', 'marketing': '마케팅정보 수신동의'}
    return titles.get(terms_type, '약관')


def get_default_terms_content(terms_type: str) -> str:
    """기본 약관 내용 반환 (HTML 형식)"""
    contents = {
        'service': '<h2>제1조 (목적)</h2><p>본 약관은 TeeUp 서비스의 이용과 관련하여 회사와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.</p>',
        'privacy': '<h2>제1조 (개인정보의 처리목적)</h2><p>회사는 다음의 목적을 위하여 개인정보를 처리합니다.</p>',
        'collection': '<h2>제1조 (개인정보의 수집 및 이용목적)</h2><p>회사는 다음의 목적을 위하여 개인정보를 수집 및 이용합니다.</p>',
        'marketing': '<h2>제1조 (마케팅정보 수신동의)</h2><p>회사는 이용자에게 다양한 정보를 제공하기 위해 마케팅 정보를 수신하는 것에 동의를 받습니다.</p>'
    }
    return contents.get(terms_type, '<p>약관 내용을 입력해주세요.</p>')


# Phase 3에서 Event 모델 제거됨 - 레거시 코드 주석 처리
# @router.post("/events")
# async def create_admin_event(
#     event_data: dict,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_admin_user)
# ):
#     """관리자용 이벤트 생성 (레거시 - 더 이상 사용하지 않음)"""
#     # Event 모델이 제거되어 작동하지 않음
#     # 소셜 모임은 /socials API를 사용하세요
#     raise HTTPException(
#         status_code=status.HTTP_410_GONE,
#         detail="이 API는 더 이상 사용되지 않습니다. /api/v1/socials를 사용하세요."
#     )

# Phase 3에서 Event 모델 제거됨 - 레거시 함수들 주석 처리
# 소셜 모임은 /api/v1/socials API를 사용하세요

# @router.put("/events/{event_id}")
# @router.delete("/events/{event_id}")
# @router.post("/events/{event_id}/cancel")
# 위 엔드포인트들은 Event 모델 제거로 작동하지 않음
