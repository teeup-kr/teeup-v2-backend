# 클럽 관련 스키마
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .enums import ClubType, ClubStatus, ClubRole, BillingCycle, RegulationStatus
# 클럽 관련 스키마
class ClubCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="클럽 이름")
    type: ClubType = Field(default=ClubType.REGULAR, description="클럽 타입")
    description: Optional[str] = Field(None, description="클럽 설명")
    member_count: int = Field(..., ge=1, description="예상 멤버 수")
    location: Optional[str] = Field(None, max_length=255, description="클럽 위치")
    contact_info: Optional[str] = Field(None, max_length=255, description="연락처")
    representative_name: Optional[str] = Field(None, max_length=255, description="대표자 이름")
    additional_info: Optional[str] = Field(None, description="추가 정보")

class ClubUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="클럽 이름")
    type: Optional[ClubType] = Field(None, description="클럽 타입")
    description: Optional[str] = Field(None, description="클럽 설명")
    member_count: Optional[int] = Field(None, ge=1, description="예상 멤버 수")
    location: Optional[str] = Field(None, max_length=255, description="클럽 위치")
    contact_info: Optional[str] = Field(None, max_length=255, description="연락처")
    representative_name: Optional[str] = Field(None, max_length=255, description="대표자 이름")
    additional_info: Optional[str] = Field(None, description="추가 정보")
    application_deadline: Optional[datetime] = Field(None, description="신청 마감일")

class ClubResponse(BaseModel):
    id: int
    display_id: Optional[str]
    name: str
    type: ClubType
    description: Optional[str]
    member_count: Optional[int]  # 예상 멤버 수 (레거시)
    current_member_count: Optional[int] = None  # 실제 멤버 수 (ACTIVE/APPROVED 상태)
    location: Optional[str]
    contact_info: Optional[str]
    representative_name: Optional[str]
    additional_info: Optional[str]
    status: ClubStatus
    created_at: datetime
    updated_at: datetime
    membership_status: Optional[str] = None  # 현재 사용자의 멤버십 상태
    membership_role: Optional[str] = None    # 현재 사용자의 멤버십 역할
    
    class Config:
        from_attributes = True

class ClubMembersResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_realname: Optional[str] = None
    user_nickname: str
    user_email: str
    user_phone_number: Optional[str] = None
    user_birthdate: Optional[str] = None
    user_gender: Optional[str] = None
    user_handicap: Optional[float] = None
    user_average_score: Optional[float] = None
    role: ClubRole
    status: str
    joined_at: datetime
    
    model_config = {"from_attributes": True}

class ClubMembershipResponse(BaseModel):
    id: int
    club_id: int
    user_id: int
    role: ClubRole
    status: str
    joined_at: datetime
    
    model_config = {"from_attributes": True}

class ClubMemberAddRequest(BaseModel):
    user_id: int
    role: ClubRole = ClubRole.MEMBER

class ClubMemberRoleUpdateRequest(BaseModel):
    role: ClubRole

class MemberNoteUpdate(BaseModel):
    note: Optional[str] = None

class MemberNoteResponse(BaseModel):
    note: Optional[str] = None
    updated_at: Optional[datetime] = None

class RegularFeeUpdate(BaseModel):
    has_regular_fee: bool = Field(..., description="정기 회비 사용 여부")
    regular_fee_amount: Optional[float] = Field(None, ge=0, description="정기 회비 금액")
    regular_fee_cycle: Optional[BillingCycle] = Field(None, description="정기 회비 주기")
    regular_fee_description: Optional[str] = Field(None, description="정기 회비 설명")

class RegularFeeResponse(BaseModel):
    has_regular_fee: bool
    regular_fee_amount: Optional[float] = None
    regular_fee_cycle: Optional[BillingCycle] = None
    regular_fee_description: Optional[str] = None
    updated_at: Optional[datetime] = None

# 회비 항목 관련 스키마
class ClubFeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="회비 항목명")
    amount: float = Field(..., ge=0, description="회비 금액")
    cycle: Optional[BillingCycle] = Field(None, description="회비 주기")
    description: Optional[str] = Field(None, description="회비 설명")
    is_active: bool = Field(default=True, description="활성 여부")

class ClubFeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="회비 항목명")
    amount: Optional[float] = Field(None, ge=0, description="회비 금액")
    cycle: Optional[BillingCycle] = Field(None, description="회비 주기")
    description: Optional[str] = Field(None, description="회비 설명")
    is_active: Optional[bool] = Field(None, description="활성 여부")

class ClubFeeResponse(BaseModel):
    id: int
    club_id: int
    name: str
    amount: float
    cycle: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# 클럽 공지사항 관련 스키마
class ClubNoticeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="공지사항 제목")
    content: str = Field(..., min_length=1, description="공지사항 내용")
    is_important: bool = Field(default=False, description="중요 공지 여부")
    is_private: bool = Field(default=False, description="비공개 공지 여부")

class ClubNoticeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="공지사항 제목")
    content: Optional[str] = Field(None, min_length=1, description="공지사항 내용")
    is_important: Optional[bool] = Field(None, description="중요 공지 여부")
    is_private: Optional[bool] = Field(None, description="비공개 공지 여부")

class ClubNoticeResponse(BaseModel):
    id: int
    club_id: int
    title: str
    content: str
    is_important: bool
    is_private: bool
    author_id: int
    author_name: str
    view_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# 규정 관련 스키마
class RegulationCreate(BaseModel):
    category_id: int = Field(..., description="카테고리 ID")
    title: str = Field(..., min_length=1, max_length=255, description="규정 제목")
    content: str = Field(..., min_length=1, description="규정 내용")
    status: str = Field(default="ACTIVE", description="상태")

class RegulationUpdate(BaseModel):
    category_id: Optional[int] = Field(None, description="카테고리 ID")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="규정 제목")
    content: Optional[str] = Field(None, min_length=1, description="규정 내용")
    status: Optional[str] = Field(None, description="상태")

class RegulationResponse(BaseModel):
    id: int
    club_id: int
    category_id: int
    title: str
    content: str
    status: str
    created_by: int
    created_by_name: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class RegulationListResponse(BaseModel):
    regulations: List[RegulationResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# 규정 카테고리 관련 스키마
class RegulationCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="카테고리 이름")
    description: Optional[str] = Field(None, description="카테고리 설명")

class RegulationCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="카테고리 이름")
    description: Optional[str] = Field(None, description="카테고리 설명")

class RegulationCategoryResponse(BaseModel):
    id: int
    club_id: int
    name: str
    order: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# 클럽 규정 관련 스키마
class RegulationCategoryWithRegulations(RegulationCategoryResponse):
    regulations: List[RegulationResponse] = []

class ClubRegulationsResponse(BaseModel):
    categories: List[RegulationCategoryWithRegulations]
    total_categories: int = 0

class ClubRegulationResponse(BaseModel):
    id: int
    club_id: int
    category_id: int
    title: str
    content: str
    status: str
    created_by: int
    created_by_name: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # 추가 필드 (프론트엔드에서 사용)
    category_name: Optional[str] = None
    
    model_config = {"from_attributes": True}

class ClubRegulationCreate(BaseModel):
    category_id: int = Field(..., description="카테고리 ID")
    title: str = Field(..., min_length=1, max_length=255, description="규정 제목")
    content: str = Field(..., min_length=1, description="규정 내용")
    status: str = Field(default="ACTIVE", description="상태")

class ClubRegulationUpdate(BaseModel):
    category_id: Optional[int] = Field(None, description="카테고리 ID")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="규정 제목")
    content: Optional[str] = Field(None, min_length=1, description="규정 내용")
    status: Optional[str] = Field(None, description="상태")

