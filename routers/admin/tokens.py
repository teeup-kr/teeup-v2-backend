"""어드민 임시 토큰(admin_temp)의 일회용 보장.

발급은 routers/admin/auth.py 의 generate-client-token, 검증은
routers/auth.py 의 verify-admin-token 이 한다. 한 번 쓴 jti 를 여기에
기록해 재사용을 막는다.

원래 routers/admin.py 에 있었으나 그 파일은 같은 이름의 패키지에 가려져
로드되지 않았다. 그래서 verify-admin-token 이 ImportError 로 죽고
401 만 돌려주고 있었다. 이쪽으로 옮겨 되살린다.

[한계] 프로세스 메모리에 둔다. 인스턴스가 여러 개면 각자 다른 집합을 보므로
일회용이 인스턴스 단위로만 보장된다. Cloud Run 처럼 여러 인스턴스가 뜨는
환경에서 엄격히 막으려면 공유 저장소(DB 테이블 또는 Redis)로 옮겨야 한다.
토큰 수명이 5분이고 관리자만 쓰는 경로라 우선 기존 동작을 그대로 되살린다.
"""
import threading
import time

# jti -> 기록한 시각(단조 시계). 시각을 같이 두는 이유는 아래 _prune 이다.
_used_tokens: dict[str, float] = {}
_token_lock = threading.Lock()

# 토큰 자체가 5분이면 만료된다. 그보다 넉넉히 지난 기록은 들고 있을 이유가
# 없다. 예전 구현은 set 이라 프로세스가 사는 동안 계속 커졌다.
_RETENTION_SECONDS = 15 * 60


def _prune(now: float) -> None:
    """보존 기간이 지난 기록을 버린다. 호출자가 잠금을 잡고 있어야 한다."""
    if len(_used_tokens) < 128:
        return
    for jti, seen_at in list(_used_tokens.items()):
        if now - seen_at > _RETENTION_SECONDS:
            del _used_tokens[jti]


def mark_token_as_used(token_jti: str) -> None:
    """토큰을 사용됨으로 표시."""
    now = time.monotonic()
    with _token_lock:
        _prune(now)
        _used_tokens[token_jti] = now


def is_token_used(token_jti: str) -> bool:
    """토큰이 이미 사용되었는지 확인."""
    with _token_lock:
        return token_jti in _used_tokens
