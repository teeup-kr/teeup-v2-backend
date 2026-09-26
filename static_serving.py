"""호스트별 정적 파일 서빙.

집 서버에서는 게이트웨이 nginx 가 이 일을 했다.

    teeup.kr / www.teeup.kr   root /var/www/teeup/dist          (RN 웹 내보내기)
    admin.teeup.kr            root /var/www/teeup-admin/dist    (백오피스, Basic 인증)
    양쪽 공통                  location /api/ -> 백엔드

Cloud Run 은 컨테이너 하나가 $PORT 하나를 듣는다. 앞단에 nginx 를 둘 수
없으므로 같은 규칙을 앱에서 그대로 재현한다.

폴백 순서는 nginx 의 `try_files $uri $uri.html $uri/ /index.html` 과 맞춘다.
Expo 정적 내보내기가 경로마다 .html 파일을 만들기 때문에 `$uri.html` 단계가
반드시 있어야 한다(/faq -> faq.html).
"""
import mimetypes
import os
import posixpath
import secrets
from pathlib import Path

from starlette.datastructures import Headers

from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

# 앱이 다루는 경로. 여기로 시작하면 정적 서빙이 손대지 않는다.
API_PREFIXES = ("/api/", "/health", "/static/")

# 해시가 박힌 자산은 영구 캐시가 안전하다. 내용이 바뀌면 파일명이 바뀐다.
IMMUTABLE_DIRS = ("/_expo/", "/assets/", "/js/", "/css/")


class HostStaticFiles:
    """호스트를 보고 정적 루트를 고르는 ASGI 미들웨어."""

    def __init__(
        self,
        app: ASGIApp,
        client_dir: str,
        admin_dir: str,
        admin_hosts: tuple[str, ...] = ("admin.teeup.kr",),
        admin_user: str = "",
        admin_password: str = "",
    ) -> None:
        self.app = app
        self.client_dir = Path(client_dir).resolve() if client_dir else None
        self.admin_dir = Path(admin_dir).resolve() if admin_dir else None
        self.admin_hosts = admin_hosts
        self.admin_user = admin_user
        self.admin_password = admin_password

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path.startswith(API_PREFIXES):
            await self.app(scope, receive, send)
            return

        if scope.get("method") not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        host = Headers(scope=scope).get("host", "").split(":")[0].lower()
        is_admin = host in self.admin_hosts

        root = self.admin_dir if is_admin else self.client_dir
        if root is None or not root.is_dir():
            # 정적 파일이 이미지에 없으면(백엔드만 띄운 경우) 앱으로 넘긴다.
            await self.app(scope, receive, send)
            return

        if is_admin:
            unauthorized = self._check_admin_auth(scope)
            if unauthorized is not None:
                await unauthorized(scope, receive, send)
                return

        target = self._resolve(root, path)
        if target is None:
            await self.app(scope, receive, send)
            return

        await self._file_response(target, path)(scope, receive, send)

    def _check_admin_auth(self, scope: Scope) -> Response | None:
        """nginx 의 server 레벨 auth_basic 과 같은 자리에 둔다.

        화면만 막고 API 를 열어두면 막은 의미가 없다. 이 미들웨어는 정적
        경로만 다루고 /api/ 는 위에서 이미 넘겼으므로, API 쪽 인증은
        기존 토큰 인증이 담당한다.
        """
        if not self.admin_user or not self.admin_password:
            # 자격증명이 설정되지 않았으면 잠근다. 열어두는 쪽으로 실패하지 않는다.
            return PlainTextResponse("관리자 자격증명이 설정되지 않았습니다.", status_code=503)

        header = Headers(scope=scope).get("authorization", "")
        if header.startswith("Basic "):
            import base64

            try:
                raw = base64.b64decode(header[6:]).decode("utf-8")
                user, _, password = raw.partition(":")
            except Exception:
                user = password = ""
            if secrets.compare_digest(user, self.admin_user) and secrets.compare_digest(
                password, self.admin_password
            ):
                return None

        return PlainTextResponse(
            "인증이 필요합니다.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Restricted"'},
        )

    def _resolve(self, root: Path, url_path: str) -> Path | None:
        """try_files $uri $uri.html $uri/ /index.html"""
        rel = posixpath.normpath(url_path).lstrip("/")
        # normpath 로도 남는 상위 참조를 막는다.
        if rel.startswith("..") or os.path.isabs(rel):
            return None

        candidates = []
        if rel:
            candidates.append(root / rel)
            candidates.append(root / (rel + ".html"))
            candidates.append(root / rel / "index.html")
        candidates.append(root / "index.html")

        for c in candidates:
            try:
                resolved = c.resolve()
            except OSError:
                continue
            # 심볼릭 링크로 루트 밖을 가리키는 경우를 막는다.
            if not resolved.is_relative_to(root):
                continue
            if resolved.is_file():
                return resolved
        return None

    def _file_response(self, target: Path, url_path: str) -> FileResponse:
        media_type, _ = mimetypes.guess_type(str(target))
        headers = {}
        if any(url_path.startswith(p) for p in IMMUTABLE_DIRS):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif target.name == "index.html":
            # 해시가 없다. 여기에 긴 캐시를 걸면 배포해도 옛 화면이 남는다.
            headers["Cache-Control"] = "no-cache"
        return FileResponse(target, media_type=media_type, headers=headers)


def mount_static(app, settings) -> None:
    """설정에 경로가 있고 실제로 존재할 때만 미들웨어를 단다."""
    client_dir = getattr(settings, "STATIC_CLIENT_DIR", "") or ""
    admin_dir = getattr(settings, "STATIC_ADMIN_DIR", "") or ""
    if not client_dir and not admin_dir:
        return
    hosts = tuple(
        h.strip().lower()
        for h in (getattr(settings, "ADMIN_HOSTS", "") or "admin.teeup.kr").split(",")
        if h.strip()
    )
    app.add_middleware(
        HostStaticFiles,
        client_dir=client_dir,
        admin_dir=admin_dir,
        admin_hosts=hosts,
        admin_user=getattr(settings, "ADMIN_BASIC_USER", "") or "",
        admin_password=getattr(settings, "ADMIN_BASIC_PASSWORD", "") or "",
    )
