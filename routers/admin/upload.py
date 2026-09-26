"""
백오피스 파일 업로드 API
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from config import settings
from utils.google_oauth import GoogleOAuthError, upload_to_drive

from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload")
async def admin_upload_file(
    file: UploadFile = File(...),
    share: str | None = Query(default=None, description="'link' 지정 시 anyone-with-link viewer 권한 부여"),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 파일 업로드 (Google Drive 클럽 폴더)

    예전에는 컨테이너 로컬 디스크에 썼다. 그 경로에는 볼륨이 없었고 서빙하는
    곳도 없어서, 올린 파일에 다시 도달할 방법이 없었다. 응답도 filename 만
    돌려줬기 때문에 백오피스 미리보기가 조용히 건너뛰어졌다.
    /api/v1/upload/ 와 /admin/notices/upload 가 쓰는 Drive 경로로 맞춘다.
    """
    from routers.upload import generate_filename, validate_file

    if not validate_file(file):
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF만 업로드 가능합니다.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다.")

    folder_id = settings.GOOGLE_DRIVE_CLUB_FOLDER_ID
    if not folder_id:
        raise HTTPException(status_code=500, detail="클럽 등록용 Google Drive 폴더 ID(GOOGLE_DRIVE_CLUB_FOLDER_ID)가 설정되지 않았습니다.")

    new_filename = generate_filename(file.filename)

    try:
        meta = upload_to_drive(file_bytes, new_filename, folder_id, share=share)
    except GoogleOAuthError as e:
        msg = str(e)
        if "리프레시 토큰이 만료" in msg or "토큰을 재발급" in msg:
            raise HTTPException(status_code=503, detail="Google Drive 토큰이 만료되었습니다. 관리자에게 문의하거나 토큰을 재발급해주세요.")
        logger.error("관리자 파일 업로드 실패: %s", msg)
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다")

    logger.info("관리자 파일 업로드 성공: %s -> %s (%s)", file.filename, new_filename, meta["file_id"])

    return {
        "success": True,
        "message": "파일이 성공적으로 업로드되었습니다.",
        "filename": new_filename,
        "original_filename": file.filename,
        "file_size": len(file_bytes),
        "file_id": meta["file_id"],
        "web_view_link": meta["web_view_link"],
        "web_content_link": meta["web_content_link"],
        "mime_type": meta["mime_type"],
    }
