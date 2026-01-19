# 인증 관련 유틸리티 함수들 (레거시 호환성 유지)
# 이 파일은 하위 호환성을 위해 유지되며, 모든 함수는 routers.auth의 JWT 기반 함수를 재사용합니다.
# 새로운 코드에서는 routers.auth를 직접 사용하는 것을 권장합니다.

from routers.auth import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_current_admin_user_jwt,
    get_current_user_or_admin
)

# 하위 호환성을 위해 함수들을 재export
__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_current_admin_user_jwt",
    "get_current_user_or_admin"
]