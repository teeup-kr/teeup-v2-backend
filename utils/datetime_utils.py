"""
날짜/시간 유틸리티 함수
한국 표준시(KST, UTC+9)를 일관되게 사용하기 위한 유틸리티
"""
from datetime import datetime, timezone, timedelta

# 한국 표준시 (UTC+9)
KST = timezone(timedelta(hours=9))


def get_kst_now() -> datetime:
    """
    현재 시간을 KST(한국 표준시)로 반환
    
    Returns:
        datetime: KST 타임존이 설정된 현재 시간
    """
    return datetime.now(KST)


def get_kst_date() -> datetime:
    """
    오늘 날짜의 시작 시간(00:00:00)을 KST로 반환
    
    Returns:
        datetime: 오늘 날짜의 시작 시간 (KST)
    """
    now = get_kst_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

