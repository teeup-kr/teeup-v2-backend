"""
백오피스 파일 업로드 API
"""
import os
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
import logging

from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-upload"])


@router.post("/upload")
async def admin_upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_admin_user)):
    """관리자용 파일 업로드"""
    from routers.upload import validate_file, generate_filename

    try:
        if not validate_file(file):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF만 업로드 가능합니다.")
        file_content = await file.read()
        MAX_FILE_SIZE = 10 * 1024 * 1024
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다.")
        UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        new_filename = generate_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(new_filename)
            new_filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_DIR, new_filename)
            counter += 1
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        logger.info(f"관리자 파일 업로드 성공: {file.filename} -> {new_filename}")
        return {
            "success": True,
            "message": "파일이 성공적으로 업로드되었습니다.",
            "filename": new_filename,
            "original_filename": file.filename,
            "file_size": len(file_content),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 파일 업로드 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다")
