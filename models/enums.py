# Enum 클래스 정의
import enum

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"
    DELETED = "DELETED"

class Provider(str, enum.Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class ClubType(str, enum.Enum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"

class ClubStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ClubRole(str, enum.Enum):
    LEADER = "LEADER"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"

class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELED = "CANCELED"

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"

class ParticipantStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"
    WAITING_LIST = "WAITING_LIST"

class ParticipantRole(str, enum.Enum):
    PARTICIPANT = "PARTICIPANT"
    ORGANIZER = "ORGANIZER"
    CO_ORGANIZER = "CO_ORGANIZER"

class ParticipantType(str, enum.Enum):
    USER = "USER"
    GUEST = "GUEST"

class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "SUCCEEDED"
    PENDING = "PENDING"
    FAILED = "FAILED"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"

class BillingCycle(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    ONE_TIME = "ONE_TIME"

class TermsType(str, enum.Enum):
    SERVICE = "SERVICE"
    PRIVACY = "PRIVACY"
    PRIVACY_COLLECTION = "PRIVACY_COLLECTION"
    MARKETING = "MARKETING"

class InquiryType(str, enum.Enum):
    GENERAL = "GENERAL"
    TECHNICAL = "TECHNICAL"
    BILLING = "BILLING"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    BUG_REPORT = "BUG_REPORT"
    ACCOUNT = "ACCOUNT"
    PAYMENT = "PAYMENT"


class InquiryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"

class FeeType(str, enum.Enum):
    MONTHLY = "MONTHLY"
    SPECIAL = "SPECIAL"

class ExpenseStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"


class ExpenseItemType(str, enum.Enum):
    """비용 항목 타입 (그린피/캐디피/카트비/기타 = 행으로 관리)"""
    TOTAL = "TOTAL"          # 총액 (나머지 금액 등)
    GREEN_FEE = "GREEN_FEE"  # 그린피
    CADDY_FEE = "CADDY_FEE"  # 캐디피
    CART_FEE = "CART_FEE"    # 카트비
    OTHER = "OTHER"          # 기타 (소셜 커스텀 항목 포함)

class NoticeType(str, enum.Enum):
    GENERAL = "GENERAL"
    SYSTEM = "SYSTEM"
    EVENT = "EVENT"
    MAINTENANCE = "MAINTENANCE"

class TokenRevokeReason(str, enum.Enum):
    LOGOUT = "LOGOUT"

class HandicapUpdateMethod(str, enum.Enum):
    MANUAL = "MANUAL"  # 수동 입력
    AUTO = "AUTO"      # 자동 계산

class NotificationType(str, enum.Enum):
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

class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"
