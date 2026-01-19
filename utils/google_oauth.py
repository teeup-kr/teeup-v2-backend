import json
import os
import time
from typing import Dict

import requests

from config import settings


class GoogleOAuthError(Exception):
    pass


def _read_token_file(path: str) -> Dict:
    if not os.path.exists(path):
        raise GoogleOAuthError("Google OAuth token.json 파일을 찾을 수 없습니다. 토큰 발급 스크립트를 먼저 실행하세요.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_token_file(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def load_access_token() -> str:
    """token.json을 로드하고 refresh_token으로 갱신하여 Access Token을 반환.
    
    유효기간(expiry) 체크 없이 항상 refresh_token으로 새 토큰을 발급받습니다.

    반환: 유효한 Access Token 문자열
    예외: GoogleOAuthError
    """
    token_path = settings.GOOGLE_TOKEN_FILE
    token = _read_token_file(token_path)

    # google-auth 포맷 또는 단순 포맷 모두 허용
    refresh_token = token.get("refresh_token")
    token_uri = token.get("token_uri") or "https://oauth2.googleapis.com/token"

    if not refresh_token:
        raise GoogleOAuthError("refresh_token이 없어 토큰 갱신을 할 수 없습니다. 토큰을 재발급하세요.")

    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    resp = requests.post(token_uri, data=data, timeout=20)
    if resp.status_code != 200:
        error_text = resp.text
        # invalid_grant 오류인 경우 더 명확한 메시지 제공
        if "invalid_grant" in error_text:
            raise GoogleOAuthError(
                "리프레시 토큰이 만료되었거나 무효합니다. "
                "토큰을 재발급해야 합니다. "
                "스크립트를 실행하세요: python scripts/renew_google_drive_token.py"
            )
        raise GoogleOAuthError(f"토큰 갱신 실패: {resp.status_code} {resp.text}")

    refreshed = resp.json()
    new_access_token = refreshed.get("access_token")

    if not new_access_token:
        raise GoogleOAuthError("갱신 응답에 access_token이 없습니다.")

    # 파일 포맷 보존 + 업데이트 (expiry 제거)
    token["access_token"] = new_access_token
    token["token"] = new_access_token
    # expiry 필드 제거 (있는 경우)
    if "expiry" in token:
        del token["expiry"]

    _write_token_file(token_path, token)
    return new_access_token


def get_mime_type(file_ext: str) -> str:
    ext = (file_ext or "").lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in (".png",):
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"

"""
Google OAuth 인증 유틸리티
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
import requests
from config import settings

logger = logging.getLogger(__name__)

class GoogleOAuth:
    """Google OAuth 인증 클래스"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scope = "openid email profile"
        
        # Google OAuth 엔드포인트
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Google OAuth 인증 URL 생성"""
        try:
            params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": self.scope,
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent"
            }
            
            if state:
                params["state"] = state
            
            # URL 파라미터 생성
            param_string = "&".join([f"{key}={value}" for key, value in params.items()])
            auth_url = f"{self.auth_url}?{param_string}"
            
            logger.info("Google OAuth 인증 URL 생성 완료")
            return auth_url
            
        except Exception as e:
            logger.error(f"Google OAuth 인증 URL 생성 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth 인증 URL 생성에 실패했습니다"
            )
    
    def exchange_code_for_token(self, codeVerifier: str, authorizationCode: str) -> Dict[str, Any]:
        """인증 코드를 액세스 토큰으로 교환"""
        try:
            # # 환경 변수 검증
            # if not self.client_id or not self.client_secret:
            #     logger.error("Google OAuth 클라이언트 ID 또는 시크릿이 설정되지 않았습니다")
            #     raise HTTPException(
            #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            #         detail="Google OAuth 설정이 완료되지 않았습니다"
            #     )
            
            data = {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": authorizationCode,
                "code_verifier": codeVerifier,
                "redirect_uri": self.redirect_uri,
            }

            # logger.info(f"Google OAuth 토큰 교환 요청: {data}")
            
            response = requests.post(self.token_url, data=data)
            
            # 응답 로깅
            logger.info(f"Google OAuth 응답 상태: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Google OAuth 응답 내용: {response.text}")
            
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Google OAuth 토큰 교환 성공")
            return token_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Google OAuth HTTP 에러: {str(e)}, 응답: {response.text if 'response' in locals() else 'N/A'}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth 토큰 교환에 실패했습니다: {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Google OAuth 요청 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth 토큰 교환에 실패했습니다"
            )
        except Exception as e:
            logger.error(f"Google OAuth 토큰 교환 중 오류: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth 토큰 교환 중 오류가 발생했습니다"
            )
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """액세스 토큰으로 사용자 정보 조회"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(self.user_info_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"Google 사용자 정보 조회 성공: {user_info.get('email')}")
            return user_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google 사용자 정보 조회 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 정보 조회에 실패했습니다"
            )
        except Exception as e:
            logger.error(f"Google 사용자 정보 조회 중 오류: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 정보 조회 중 오류가 발생했습니다"
            )
    
    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Google ID 토큰 검증"""
        try:
            # Google의 공개 키를 사용하여 ID 토큰 검증
            # 실제 구현에서는 google-auth 라이브러리를 사용하는 것이 좋습니다
            import jwt
            from jwt import PyJWKClient
            
            # Google의 JWKS 엔드포인트
            jwks_client = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")
            
            # JWT 헤더에서 키 ID 추출
            unverified_header = jwt.get_unverified_header(id_token)
            rsa_key = jwks_client.get_signing_key(unverified_header["kid"]).key
            
            # 토큰 검증
            payload = jwt.decode(
                id_token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer="https://accounts.google.com"
            )
            
            logger.info(f"Google ID 토큰 검증 성공: {payload.get('email')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Google ID 토큰이 만료되었습니다")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 만료되었습니다"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"유효하지 않은 Google ID 토큰: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        except Exception as e:
            logger.error(f"Google ID 토큰 검증 중 오류: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="토큰 검증 중 오류가 발생했습니다"
            )

# 전역 Google OAuth 인스턴스
google_oauth = GoogleOAuth()
