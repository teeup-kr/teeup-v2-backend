# 모임 관련 스키마
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from .enums import MeetingType, MeetingSubtype, SettlementMethod, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole, ParticipantType
from .team import GuestCreate

class RoundingMeetingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="모임 이름")
    description: Optional[str] = Field(None, description="모임 설명")
    location: Optional[str] = Field(None, max_length=255, description="모임 장소")
    meeting_time: datetime = Field(..., description="모임 시간")
    tee_times: List[str] = Field(..., description="티타임 목록")
    max_participants: int = Field(..., ge=1, description="최대 참가자 수")
    meeting_type: MeetingType = Field(default=MeetingType.ROUND, description="모임 타입")
    meeting_subtype: MeetingSubtype = Field(..., description="모임 하위 타입")
    total_cost: Optional[float] = Field(None, ge=0, description="총 비용")
    green_fee: Optional[float] = Field(None, ge=0, description="그린피")
    caddy_fee: Optional[float] = Field(None, ge=0, description="캐디피")
    cart_fee: Optional[float] = Field(None, ge=0, description="카트비")
    settlement_method: SettlementMethod = Field(..., description="정산 방법")
    course_name: Optional[str] = Field(None, max_length=255, description="코스 이름")
    hole_count: Optional[int] = Field(None, ge=1, le=18, description="홀 수")
    reservation_name: Optional[str] = Field(None, max_length=255, description="예약자명")
    application_deadline: Optional[datetime] = Field(None, description="신청 마감일")
    club_id: int = Field(..., ge=1, description="클럽 ID")
    team_formation_mode: Optional[str] = Field(None, max_length=50, description="팀 구성 방식")
    team_size: Optional[int] = Field(None, ge=1, description="팀 크기")
    is_private: Optional[bool] = Field(False, description="프라이빗 라운딩 여부")
    selected_participants: Optional[List[int]] = Field(None, description="선택된 참가자 user_id 목록 (프라이빗 라운딩일 때 필수)")
    selected_guests: Optional[List[GuestCreate]] = Field(None, description="선택된 게스트 목록 (프라이빗 라운딩일 때 선택사항)")
    
    @field_validator('meeting_time', 'application_deadline', mode='before')
    @classmethod
    def remove_timezone(cls, v):
        """한국 시간 타임존(+09:00)을 제거하고 naive datetime으로 변환"""
        if v is None:
            return v
        if isinstance(v, datetime):
            # 타임존 정보가 있으면 제거 (한국 시간으로 저장)
            if v.tzinfo is not None:
                # 한국 시간(+09:00)이면 타임존 제거
                return v.replace(tzinfo=None)
            return v
        return v

class MeetingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="모임 이름")
    description: Optional[str] = Field(None, description="모임 설명")
    location: Optional[str] = Field(None, max_length=255, description="모임 장소")
    meeting_time: Optional[datetime] = Field(None, description="모임 시간")
    application_deadline: Optional[datetime] = Field(None, description="신청 마감일")
    tee_times: Optional[List[str]] = Field(None, description="티타임 목록")
    max_participants: Optional[int] = Field(None, ge=1, description="최대 참가자 수")
    # meeting_type은 수정할 수 없음 (보안상 이유)
    meeting_subtype: Optional[MeetingSubtype] = Field(None, description="모임 하위 타입")
    status: Optional[MeetingStatus] = Field(None, description="모임 상태")
    cancel_reason: Optional[str] = Field(None, description="취소 사유")
    total_cost: Optional[float] = Field(None, ge=0, description="총 비용")
    green_fee: Optional[float] = Field(None, ge=0, description="그린피")
    caddy_fee: Optional[float] = Field(None, ge=0, description="캐디피")
    cart_fee: Optional[float] = Field(None, ge=0, description="카트비")
    settlement_method: Optional[SettlementMethod] = Field(None, description="정산 방법")
    social_settlement_method: Optional[SettlementMethod] = Field(None, description="소셜 정산 방법")
    course_name: Optional[str] = Field(None, max_length=255, description="코스 이름")
    hole_count: Optional[int] = Field(None, ge=1, le=18, description="홀 수")
    reservation_name: Optional[str] = Field(None, max_length=255, description="예약자명")
    venue_name: Optional[str] = Field(None, max_length=255, description="장소명")
    social_cost: Optional[float] = Field(None, ge=0, description="소셜 비용")
    social_notes: Optional[str] = Field(None, description="소셜 모임 메모")
    is_private: Optional[bool] = Field(None, description="프라이빗 라운딩 여부")

class MeetingResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    location: Optional[str]
    meeting_time: Optional[datetime]
    application_deadline: Optional[datetime]
    tee_times: List[str] = Field(default_factory=list)
    max_participants: Optional[int]
    meeting_type: MeetingType
    meeting_subtype: Optional[MeetingSubtype]
    team_formation_mode: Optional[str]
    team_size: Optional[int]
    total_cost: Optional[float]
    green_fee: Optional[float]
    caddy_fee: Optional[float]
    cart_fee: Optional[float]
    settlement_method: Optional[SettlementMethod]
    social_settlement_method: Optional[SettlementMethod]
    course_name: Optional[str]
    hole_count: Optional[int]
    reservation_name: Optional[str]
    venue_name: Optional[str]
    club_id: int
    status: MeetingStatus
    cancel_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    club_name: str
    participant_count: int
    social_cost: Optional[float]
    social_notes: Optional[str]
    application_closed_early: bool = False
    team_formation_confirmed_at: Optional[datetime] = None
    rounding_started_at: Optional[datetime] = None
    rounding_completed_at: Optional[datetime] = None
    settlement_confirmed: bool = False
    is_completed: bool = False
    is_private: bool = False
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}

class MeetingParticipantResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    guest_id: Optional[int] = None
    participant_type: ParticipantType
    user_name: str
    user_nickname: str
    status: MeetingParticipantStatus
    role: MeetingParticipantRole
    handicap_index: Optional[int]
    recent_avg_score: Optional[int]
    pace_preference: Optional[str]
    tee_preference: Optional[str]
    is_newbie: bool
    prefer_with: Optional[List[str]]
    avoid_with: Optional[List[str]]
    created_at: Optional[datetime]
    
    model_config = {"from_attributes": True}

# 소셜 모임 관련 스키마
class SocialMeetingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="소셜 모임 이름")
    description: Optional[str] = Field(None, description="소셜 모임 설명")
    meeting_time: datetime = Field(..., description="모임 시간")
    max_participants: Optional[int] = Field(None, ge=0, description="최대 참가자 수 (0 또는 null이면 제한 없음)")
    venue_name: str = Field(..., min_length=1, max_length=255, description="장소명")
    social_cost: float = Field(..., ge=0, description="소셜 비용 (필수)")
    social_settlement_method: SettlementMethod = Field(..., description="소셜 정산 방법")
    club_id: int = Field(..., description="클럽 ID")
    application_deadline: Optional[datetime] = Field(None, description="신청 마감일")
    social_notes: Optional[str] = Field(None, description="추가 메모")
    
    @field_validator('meeting_time', 'application_deadline', mode='before')
    @classmethod
    def remove_timezone(cls, v):
        """한국 시간 타임존(+09:00)을 제거하고 naive datetime으로 변환"""
        if v is None:
            return v
        if isinstance(v, datetime):
            # 타임존 정보가 있으면 제거 (한국 시간으로 저장)
            if v.tzinfo is not None:
                # 한국 시간(+09:00)이면 타임존 제거
                return v.replace(tzinfo=None)
            return v
        return v
