# OAuth 관련 스키마
from pydantic import BaseModel, Field
from typing import Optional

class OAuthLoginRequest(BaseModel):
    provider: str = Field(..., description="OAuth 제공자")
    redirect_uri: Optional[str] = Field(None, description="리다이렉트 URI")

class OAuthCallbackRequest(BaseModel):
    code: str = Field(..., description="인증 코드")
    state: Optional[str] = Field(None, description="상태 값")
    redirect_uri: Optional[str] = Field(None, description="리다이렉트 URI")

class OAuthUserInfo(BaseModel):
    provider: str
    provider_id: str
    email: str
    name: str
    picture: Optional[str]
    verified_email: bool

class GoogleOAuthBody(BaseModel):
    authorizationCode: str = Field(..., description="Google OAuth 인증 코드")
    codeVerifier: Optional[str] = Field(None, description="PKCE 코드 검증자")
    redirectUri: Optional[str] = Field(
        None, description="OAuth 리다이렉트 URI"
    )
    push_token: Optional[str] = Field(None, description="디바이스 푸시 토큰(선택)")
    token_type: Optional[str] = Field("FCM", description="푸시 토큰 타입(선택)")
    enabled: Optional[bool] = Field(True, description="토큰 활성화 여부(선택)")
