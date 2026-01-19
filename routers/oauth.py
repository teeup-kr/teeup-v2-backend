"""
OAuth 인증 라우터
"""
import secrets
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import GoogleOAuthBody, UserStatus, Provider
from schemas import OAuthLoginRequest, OAuthCallbackRequest, OAuthUserInfo
from utils.google_oauth import google_oauth
from utils.jwt_auth import jwt_auth
from utils.cuid import generate_cuid
import hashlib

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])
logger = logging.getLogger(__name__)

@router.get("/google")
async def google_oauth_login():
    """Google OAuth 로그인 시작"""
    try:
        # # Google OAuth 설정 검증
        # if not google_oauth.client_id or not google_oauth.client_secret:
        #     logger.error("Google OAuth 클라이언트 ID 또는 시크릿이 설정되지 않았습니다")
        #     raise HTTPException(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         detail="Google OAuth 설정이 완료되지 않았습니다. 관리자에게 문의하세요."
        #     )
        
        # 상태 값 생성 (CSRF 보호용)
        state = secrets.token_urlsafe(32)
        
        # Google OAuth 인증 URL 생성
        auth_url = google_oauth.get_authorization_url(state)
        
        logger.info("Google OAuth 로그인 시작")
        return {
            "auth_url": auth_url,
            "state": state
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth 로그인 시작 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth 로그인 시작에 실패했습니다"
        )

@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="OAuth 인증 코드"),
    state: str = Query(None, description="OAuth 상태 값"),
    db: Session = Depends(get_db)
):
    """Google OAuth 콜백 처리"""
    try:
        # 인증 코드를 액세스 토큰으로 교환
        token_data = google_oauth.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        id_token = token_data.get("id_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="액세스 토큰을 받지 못했습니다"
            )
        
        # 사용자 정보 조회
        user_info = google_oauth.get_user_info(access_token)
        
        # Google 사용자 정보 파싱
        google_user = OAuthUserInfo(
            provider="google",
            provider_id=user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name"),
            picture=user_info.get("picture"),
            verified_email=user_info.get("verified_email", False)
        )
        
        # 사용자 생성 또는 조회
        user, is_new_user = await create_or_get_oauth_user(google_user, db)
        
        # JWT 토큰 생성
        token_data = {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role.value if user.role else None,
            "provider": user.provider.value if user.provider else None
        }
        
        access_token = jwt_auth.create_access_token(token_data)
        refresh_token = jwt_auth.create_refresh_token(token_data)
        
        logger.info(f"Google OAuth 로그인 성공: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_auth.expire_minutes * 60,
            "user": {
                "id": user.id,                "email": user.email,
                "nickname": user.nickname,
                "role": user.role.value,
                "status": user.status.value,
                "provider": user.provider.value,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "profile_image": user.profile_image,
                "phone": user.phone_number
            },
            "is_new_user": is_new_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth 콜백 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth 콜백 처리에 실패했습니다"
        )

@router.get("/drive/callback", response_class=HTMLResponse)
async def drive_token_callback(code: str = None, state: str = None):
    """드라이브 전용 토큰 발급을 위한 간단한 콜백 페이지.
    브라우저 주소창의 code 값을 복사해 콘솔 스크립트 2번 단계에 붙여넣으면 됩니다.
    """
    html = """
    <html>
      <head><meta charset='utf-8'><title>Google Drive Token Callback</title></head>
      <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; padding: 24px;">
        <h2>드라이브 토큰 발급 콜백</h2>
        <p>아래 <b>code</b> 값을 복사해 터미널의 스크립트(2번 단계)에 붙여넣으세요.</p>
        <pre style="background:#f5f5f5;padding:12px;border-radius:8px;">code: {code}</pre>
        <pre style="background:#f5f5f5;padding:12px;border-radius:8px;">state: {state}</pre>
      </body>
    </html>
    """.format(code=code or "(없음)", state=state or "(없음)")
    return HTMLResponse(content=html)

@router.post("/google/callback")
async def google_oauth_callback_post(
    request: GoogleOAuthBody,
    db: Session = Depends(get_db)
):
    """Google OAuth 콜백 처리 (POST)"""
    try:
        authorizationCode = request.authorizationCode
        codeVerifier = request.codeVerifier

        logger.info(
            f"Google OAuth callback: "
            f"code={authorizationCode[:10]}..., "
            f"verifier_len={len(codeVerifier)}"
        )

        token_data = google_oauth.exchange_code_for_token(
            authorizationCode=authorizationCode,
            codeVerifier=codeVerifier
        )

        print("!!!!!!!!!!!!!token_data:", token_data)
        
        # 사용자 정보 조회
        user_info = google_oauth.get_user_info(token_data["access_token"])
        
        # Google 사용자 정보 파싱
        google_user = OAuthUserInfo(
            provider="google",
            provider_id=user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name"),
            picture=user_info.get("picture"),
            verified_email=user_info.get("verified_email", False)
        )
        
        # 사용자 생성 또는 조회
        user, is_new_user = await create_or_get_oauth_user(google_user, db)
        
        # JWT 토큰 생성
        token_data = {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role.value if user.role else None,
            "provider": user.provider.value if user.provider else None
        }
        
        access_token = jwt_auth.create_access_token(token_data)
        refresh_token = jwt_auth.create_refresh_token(token_data)
        
        logger.info(f"Google OAuth 로그인 성공: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_auth.expire_minutes * 60,
            "user": {
                "id": user.id,                "email": user.email,
                "nickname": user.nickname,
                "role": user.role.value,
                "status": user.status.value,
                "provider": user.provider.value,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "profile_image": user.profile_image,
                "phone": user.phone_number
            },
            "is_new_user": is_new_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth 콜백 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth 콜백 처리에 실패했습니다"
        )

async def create_or_get_oauth_user(oauth_user: OAuthUserInfo, db: Session) -> tuple[User, bool]:
    """OAuth 사용자 생성 또는 조회"""
    try:
        # 기존 사용자 조회 (이메일 또는 provider_id로)
        existing_user = db.query(User).filter(
            (User.email == oauth_user.email) | 
            (User.provider_id == oauth_user.provider_id)
        ).first()
        
        if existing_user:
            # 기존 사용자가 있는 경우
            if existing_user.provider == Provider.LOCAL:
                # 로컬 계정이 있는 경우 - 자동 변환하지 않고 에러 반환
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 일반 계정으로 가입된 이메일입니다. 일반 로그인을 이용하세요."
                )
                
                # [주석 처리] 자동 계정 변환 로직 (향후 필요시 활성화)
                # existing_user.provider = Provider.GOOGLE
                # existing_user.provider_id = oauth_user.provider_id
                # existing_user.email_verified = oauth_user.email_verified
                # if oauth_user.profile_image:
                #     existing_user.profile_image = oauth_user.profile_image
                # 
                # # 약관 동의가 없는 경우 기본 동의 처리
                # if existing_user.needs_terms_agreement:
                #     existing_user.needs_terms_agreement = False
                #     existing_user.terms_agreement = True
                #     existing_user.privacy_policy = True
                #     existing_user.privacy_collection = True
                #     # marketing_consent는 기존 값 유지
                # 
                # db.commit()
                # db.refresh(existing_user)
                # logger.info(f"기존 로컬 계정을 Google OAuth와 연결: {existing_user.email}")
            else:
                # 이미 OAuth 계정인 경우
                # 상태 값을 안전하게 문자열로 변환
                try:
                    user_status_str = existing_user.status.value if hasattr(existing_user.status, 'value') else str(existing_user.status)
                except:
                    user_status_str = str(existing_user.status)
                
                logger.info(f"OAuth 사용자 상태 확인: {existing_user.email}, status={user_status_str}")
                
                # 비활성화된 사용자 체크
                if user_status_str == "DEACTIVATED":
                    logger.warning(f"비활성화된 사용자 로그인 시도: {existing_user.email}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="관리자에 의해 비활성화 처리된 회원입니다."
                    )
                
                # 삭제된 사용자 체크
                if user_status_str == "DELETED":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="탈퇴한 계정입니다."
                    )
                
                # 활성 사용자만 로그인 가능
                if user_status_str != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="로그인할 수 없는 계정 상태입니다."
                    )
                
                # 정보 업데이트
                if oauth_user.picture:
                    existing_user.profile_image = oauth_user.picture
                if oauth_user.verified_email:
                    existing_user.email_verified = datetime.now()
                
                db.commit()
                db.refresh(existing_user)
                logger.info(f"기존 OAuth 계정 정보 업데이트: {existing_user.email}")
            
            return existing_user, False  # 기존 사용자
        
        # 새 사용자 생성
        # OAuth 사용자는 닉네임 유효성 검사 면제, 원본 그대로 사용
        base_nickname = oauth_user.name or "user"
        
        # 닉네임이 비어있거나 너무 짧으면 기본값 사용
        if not base_nickname or len(base_nickname.strip()) < 1:
            base_nickname = "user"
        
        nickname = base_nickname.strip()
        counter = 1
        
        # 중복만 확인하고 유효성 검사는 면제
        while db.query(User).filter(User.nickname == nickname).first():
            nickname = f"{base_nickname}{counter}"
            counter += 1
        
        new_user = User(
            email=oauth_user.email,
            realname=None,  # 소셜 로그인에서는 실명을 null로 설정
            nickname=nickname,
            provider=Provider.GOOGLE,
            provider_id=oauth_user.provider_id,
            email_verified=datetime.now() if oauth_user.verified_email else None,
            profile_image=oauth_user.picture,
            status=UserStatus.ACTIVE,
            average_score=100,  # OAuth 사용자 기본 평균타수 (100타)
            # OAuth 사용자 기본 약관 동의 처리
            needs_terms_agreement=False,  # 약관 동의 완료
            terms_agreement=True,         # 서비스이용약관 동의
            privacy_policy=True,          # 개인정보처리방침 동의
            privacy_collection=True,      # 개인정보 수집 및 이용동의
            marketing_consent=False       # 마케팅정보 수신동의 (선택 약관, 자동 동의 안 함)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"새 Google OAuth 사용자 생성: {new_user.email}")
        return new_user, True  # 새 사용자
        
    except HTTPException as he:
        # HTTPException은 그대로 전달
        logger.info(f"HTTPException 전달: status_code={he.status_code}, detail={he.detail}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"OAuth 사용자 생성/조회 실패: {type(e).__name__}: {str(e)}")
        # HTTPException이 아닌 다른 예외인 경우에만 일반 에러 메시지 반환
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 생성/조회에 실패했습니다"
        )

@router.get("/providers")
async def get_oauth_providers():
    """지원하는 OAuth 제공자 목록 조회"""
    return {
        "providers": [
            {
                "name": "google",
                "display_name": "Google",
                "enabled": bool(google_oauth.client_id),
                "auth_url": "/auth/oauth/google" if google_oauth.client_id else None
            }
        ]
    }
