"""클럽 설정 플래그 헬퍼 (모임·정산 API에서 공통 사용)."""


def club_settlement_enabled(club) -> bool:
    """클럽 정산 기능 사용 여부. 컬럼 없음·NULL은 True(기존 동작)."""
    if club is None:
        return True
    v = getattr(club, "settlement_enabled", True)
    if v is None:
        return True
    return bool(v)
