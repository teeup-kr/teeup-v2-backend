# Enum 정의 (str, Enum 상속으로 OpenAPI 친화적)
from enum import Enum

class ClubType(str, Enum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"

class ClubStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ClubRole(str, Enum):
    MEMBER = "MEMBER"
    MANAGER = "MANAGER"
    LEADER = "LEADER"

class BillingCycle(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"

class MeetingType(str, Enum):
    ROUND = "ROUND"
    SOCIAL = "SOCIAL"

class MeetingSubtype(str, Enum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"
    ONE_TIME = "ONE_TIME"

class SettlementMethod(str, Enum):
    EQUAL_SPLIT = "EQUAL_SPLIT"
    INDIVIDUAL = "INDIVIDUAL"

class SocialSettlementMethod(str, Enum):
    EQUAL_SPLIT = "EQUAL_SPLIT"
    TREASURER_PREPAID = "TREASURER_PREPAID"
    CLUB_FUND = "CLUB_FUND"

class MeetingStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"

class ParticipantType(str, Enum):
    USER = "USER"
    GUEST = "GUEST"

class RegulationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"

class MembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELED = "CANCELED"

class TeamFormationMode(str, Enum):
    """팀 편성 모드 (2단계 선택 방식)"""
    # 성별 분리 + 편성 기준
    GENDER_SEPARATED_HANDICAP = "GENDER_SEPARATED_HANDICAP"  # 성별 분리 + 핸디캡 기준
    GENDER_SEPARATED_PREVIOUS_RECORD = "GENDER_SEPARATED_PREVIOUS_RECORD"  # 성별 분리 + 직전대회 성적 기준
    GENDER_SEPARATED_RANDOM = "GENDER_SEPARATED_RANDOM"  # 성별 분리 + 랜덤
    # 성별 혼합 + 편성 기준
    GENDER_MIXED_HANDICAP = "GENDER_MIXED_HANDICAP"  # 성별 혼합 + 핸디캡 기준
    GENDER_MIXED_PREVIOUS_RECORD = "GENDER_MIXED_PREVIOUS_RECORD"  # 성별 혼합 + 직전대회 성적 기준
    GENDER_MIXED_RANDOM = "GENDER_MIXED_RANDOM"  # 성별 혼합 + 랜덤

class TeamStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"

class NotificationType(str, Enum):
    MEETING_CANCELLATION = "MEETING_CANCELLATION"
    MEETING_SETTLEMENT_COMPLETED = "MEETING_SETTLEMENT_COMPLETED"
    MEETING_COMPLETED = "MEETING_COMPLETED"
    MEETING_REMINDER = "MEETING_REMINDER"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    CLUB_INVITATION = "CLUB_INVITATION"
    GENERAL = "GENERAL"
    SYSTEM = "SYSTEM"
    OTHER = "OTHER"
    NEW_NOTICE = "NEW_NOTICE"
    CLUB_MEMBERSHIP_APPROVED = "CLUB_MEMBERSHIP_APPROVED"
    CLUB_MEMBERSHIP_REJECTED = "CLUB_MEMBERSHIP_REJECTED"
    CLUB_MEMBERSHIP_REQUEST = "CLUB_MEMBERSHIP_REQUEST"
    TEAM_FORMATION_COMPLETED = "TEAM_FORMATION_COMPLETED"
    SOCIAL_SETTLEMENT_COMPLETED = "SOCIAL_SETTLEMENT_COMPLETED"

class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"

class PlanType(str, Enum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

class PaymentStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    PENDING = "PENDING"
    FAILED = "FAILED"

class PaymentMethod(str, Enum):
    CARD = "CARD"
    VIRTUAL_ACCOUNT = "VIRTUAL_ACCOUNT"
    TRANSFER = "TRANSFER"

class PaymentMethodStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"

class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"

class TermsType(str, Enum):
    SERVICE = "SERVICE"
    PRIVACY = "PRIVACY"
    PRIVACY_COLLECTION = "PRIVACY_COLLECTION"
    MARKETING = "MARKETING"

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"
    DELETED = "DELETED"

class NoticeType(str, Enum):
    GENERAL = "GENERAL"
    SYSTEM = "SYSTEM"
    EVENT = "EVENT"
    MAINTENANCE = "MAINTENANCE"

class InquiryType(str, Enum):
    GENERAL = "GENERAL"
    TECHNICAL = "TECHNICAL"
    BILLING = "BILLING"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    BUG_REPORT = "BUG_REPORT"
    ACCOUNT = "ACCOUNT"
    PAYMENT = "PAYMENT"


class InquiryStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"

class Provider(str, Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"
    KAKAO = "KAKAO"
    NAVER = "NAVER"
