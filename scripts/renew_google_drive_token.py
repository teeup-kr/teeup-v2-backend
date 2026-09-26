"""Google Drive 리프레시 토큰 재발급.

utils/google_oauth.load_access_token 이 실패할 때 안내하는 스크립트다.
에러 메시지가 이 파일을 가리키는데 정작 파일이 없었다.

배경
----
리프레시 토큰은 발급한 OAuth 클라이언트에 묶인다. token.json 에 적힌
client_id 와 지금 코드가 갱신에 쓰는 GOOGLE_WEB_CLIENT_ID 가 서로 다르고,
token.json 쪽 client_id/client_secret 짝은 구글이 invalid_client 로 거부한다.
즉 예전 클라이언트의 시크릿이 남아 있지 않아 그 토큰은 되살릴 수 없다.
지금 설정된 클라이언트로 동의 절차를 다시 밟아 새 리프레시 토큰을 받는다.

사전 준비 (브라우저 필요, 1회)
------------------------------
Google Cloud Console > API 및 서비스 > 사용자 인증 정보 에서
GOOGLE_WEB_CLIENT_ID 에 해당하는 OAuth 클라이언트를 열고 '승인된 리디렉션
URI' 에 아래를 추가한다. 기존에 적혀 있던 dev.teeup.run 은 DNS 가 없어졌다.

    https://www.teeup.kr/api/v1/auth/oauth/drive/callback

그리고 .env 의 GOOGLE_DRIVE_REDIRECT_URI 를 같은 값으로 맞춘다.

사용법
------
    docker exec -it golf-backend-1 python scripts/renew_google_drive_token.py

1단계에서 출력되는 URL 을 브라우저로 연다. 파일을 넣어 둘 구글 계정으로
로그인하고 동의하면 콜백 페이지가 code 를 보여 준다. 그 값을 붙여넣는다.
"""
import json
import os
import sys
import urllib.parse

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import settings  # noqa: E402

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/drive.file"


def build_auth_url() -> str:
    params = {
        "client_id": settings.GOOGLE_WEB_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        # offline 이어야 refresh_token 이 내려온다.
        "access_type": "offline",
        # 이미 동의한 계정은 refresh_token 을 다시 주지 않는다. 재발급이
        # 목적이므로 동의 화면을 강제한다.
        "prompt": "consent",
        "state": "drive",
    }
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def exchange(code: str) -> dict:
    resp = requests.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": settings.GOOGLE_WEB_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        raise SystemExit(
            f"토큰 교환 실패 ({resp.status_code}): "
            f"{body.get('error')} - {body.get('error_description') or resp.text}"
        )
    return resp.json()


def write_token_file(payload: dict) -> str:
    """load_access_token 이 읽는 형식 그대로 쓴다."""
    path = settings.GOOGLE_TOKEN_FILE
    token = {
        "token": payload["access_token"],
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "token_uri": TOKEN_ENDPOINT,
        "client_id": settings.GOOGLE_WEB_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "scopes": [SCOPE],
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # rename 도 os.replace 도 쓰지 않는다. 이 파일은 컨테이너에 단일 파일
    # 바인드 마운트로 들어오기 때문에, 경로를 갈아끼우려 하면
    # OSError: [Errno 16] Device or resource busy 가 난다.
    # 백업은 내용 복사로, 본문은 제자리 덮어쓰기로 한다.
    if os.path.exists(path):
        backup = path + ".bak"
        with open(path, "rb") as src:
            old = src.read()
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as dst:
            dst.write(old)
        print(f"기존 내용을 {backup} 에 복사했다.")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(token, f)
    try:
        os.chmod(path, 0o600)
    except OSError as e:
        # 마운트 원본의 소유자가 달라 실패할 수 있다. 내용은 이미 썼으므로
        # 치명적이지 않다. 호스트에서 직접 좁히면 된다.
        print(f"권한 조정 실패(무시 가능): {e}")
    return path


def main() -> None:
    if not settings.GOOGLE_WEB_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise SystemExit("GOOGLE_WEB_CLIENT_ID / GOOGLE_CLIENT_SECRET 가 비어 있다.")
    if not settings.GOOGLE_DRIVE_REDIRECT_URI:
        raise SystemExit("GOOGLE_DRIVE_REDIRECT_URI 가 비어 있다.")

    print("1단계. 아래 URL 을 브라우저에서 연다.\n")
    print(build_auth_url())
    print(
        "\n리디렉션 URI 가 콘솔에 등록돼 있지 않으면 redirect_uri_mismatch 가 난다."
        f"\n현재 값: {settings.GOOGLE_DRIVE_REDIRECT_URI}\n"
    )
    code = input("2단계. 콜백 페이지에 나온 code 를 붙여넣어라: ").strip()
    if not code:
        raise SystemExit("code 가 비어 있다.")

    payload = exchange(code)
    if "refresh_token" not in payload:
        raise SystemExit(
            "응답에 refresh_token 이 없다. 이미 동의한 계정이면 구글이 생략한다. "
            "위 URL 에 prompt=consent 가 들어 있는지 확인하고 다시 시도하라."
        )

    path = write_token_file(payload)
    print(f"\n완료. {path} 를 새로 썼다.")
    print("확인: docker exec golf-backend-1 python -c "
          "\"from utils.google_oauth import load_access_token; print(len(load_access_token()))\"")


if __name__ == "__main__":
    main()
