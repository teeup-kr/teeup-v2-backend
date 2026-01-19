from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Notice, Notification, User, NoticeType
from schemas import NotificationType, NotificationStatus
from schemas import (
    NoticeCreate, NoticeUpdate, NoticeResponse, NoticeListResponse
)
from routers.admin import get_admin_user
from utils import generate_id, generate_cuid
from routers.upload import validate_file, generate_filename, MAX_FILE_SIZE
from config import settings
from utils.google_oauth import load_access_token, get_mime_type
import logging
import os
import requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("/", response_model=NoticeListResponse)
async def get_notices(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    type: Optional[str] = Query(None, description="공지사항 타입"),
    is_published: Optional[bool] = Query(None, description="발행 여부"),
    is_important: Optional[bool] = Query(None, description="중요 공지 여부"),
    search: Optional[str] = Query(None, description="제목 검색"),
    db: Session = Depends(get_db)
):
    """공지사항 목록 조회"""
    try:
        query = db.query(Notice)
        
        # 필터 적용
        if type:
            query = query.filter(Notice.type == type)
        if is_published is not None:
            # is_published 필드가 있을 때만 필터링
            if hasattr(Notice, 'is_published'):
                query = query.filter(Notice.is_published == is_published)
        if is_important is not None:
            query = query.filter(Notice.is_important == is_important)
        if search:
            query = query.filter(Notice.title.contains(search))
        
        # 총 개수 조회
        total = query.count()
        
        # 정렬 및 페이징
        # published_at이 NULL일 수 있으므로 안전하게 처리
        try:
            # published_at이 있으면 사용, 없으면 created_at 사용
            from sqlalchemy import case
            notices = query.order_by(
                desc(Notice.is_important),
                desc(case((Notice.published_at.isnot(None), Notice.published_at), else_=Notice.created_at))
            ).offset((page - 1) * size).limit(size).all()
        except Exception as e:
            # published_at 필드가 없거나 에러 발생 시 created_at으로 정렬
            logger.warning(f"published_at 정렬 실패, created_at 사용: {e}")
            notices = query.order_by(desc(Notice.is_important), desc(Notice.created_at))\
                          .offset((page - 1) * size)\
                          .limit(size)\
                          .all()
        
        # 응답 데이터 변환
        notice_responses = []
        for notice in notices:
            try:
                view_count = getattr(notice, 'view_count', 0)
                
                # type 처리
                notice_type = notice.type.value if hasattr(notice.type, 'value') else str(notice.type)
                
                notice_responses.append(NoticeResponse(
                    id=notice.id,                    title=notice.title,
                    content=notice.content,
                    type=notice_type,
                    is_important=getattr(notice, 'is_important', False),
                    is_published=getattr(notice, 'is_published', False),
                    view_count=view_count,
                    published_at=getattr(notice, 'published_at', None),
                    attachment_file=getattr(notice, 'attachment_file', None),
                    web_view_link=getattr(notice, 'web_view_link', None),
                    created_at=getattr(notice, 'created_at', datetime.now()),
                    updated_at=getattr(notice, 'updated_at', datetime.now())
                ))
            except Exception as e:
                logger.error(f"공지사항 응답 변환 실패 (id: {notice.id}): {e}")
                import traceback
                traceback.print_exc()
                raise
        
        # total_pages 계산
        total_pages = (total + size - 1) // size if total > 0 else 1
        
        return NoticeListResponse(
            notices=notice_responses,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"공지사항 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"공지사항 목록 조회 실패: {str(e)}")


@router.post("/upload")
async def upload_notice_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_admin_user),
    share: str | None = Query(default=None, description="'link' 지정 시 anyone-with-link viewer 권한 부여")
):
    """공지사항 첨부파일을 Google Drive에 업로드 (관리자 전용)"""
    try:
        if not validate_file(file):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF만 업로드 가능합니다.")

        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다.")

        new_filename = generate_filename(file.filename)
        file_ext = os.path.splitext(new_filename)[1]
        mime_type = get_mime_type(file_ext)

        # 공지사항 폴더 ID 사용
        folder_id = settings.GOOGLE_DRIVE_NOTICE_FOLDER_ID
        if not folder_id:
            raise HTTPException(status_code=500, detail="공지사항용 Google Drive 폴더 ID(GOOGLE_DRIVE_NOTICE_FOLDER_ID)가 설정되지 않았습니다.")

        try:
            access_token = load_access_token()
        except Exception as e:
            logger.error(f"파일 업로드 중 오류: {e}")
            error_msg = str(e)
            if "리프레시 토큰이 만료" in error_msg or "토큰을 재발급" in error_msg:
                raise HTTPException(
                    status_code=503,
                    detail="Google Drive 토큰이 만료되었습니다. 관리자에게 문의하거나 토큰을 재발급해주세요."
                )
            raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {error_msg}")

        # multipart/related 구성
        boundary = "teeuplink_boundary"
        metadata = {
            "name": new_filename,
            "parents": [folder_id],
        }
        import json as _json
        body = (
            f"--{boundary}\r\n"
            f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
            f'{_json.dumps(metadata)}\r\n'
            f'--{boundary}\r\n'
            f'Content-Type: {mime_type}\r\n\r\n'
        ).encode('utf-8') + file_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        params = {
            "uploadType": "multipart",
            "fields": "id,webViewLink,webContentLink,name,size,mimeType"
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        }

        resp = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            params=params,
            headers=headers,
            data=body,
            timeout=60,
        )

        if resp.status_code not in (200, 201):
            logger.error("Drive 업로드 실패: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")

        file_id = resp.json().get("id")
        if not file_id:
            raise HTTPException(status_code=500, detail="파일 업로드는 성공했지만 파일 ID를 받지 못했습니다.")

        # 메타데이터 재조회
        resp_meta = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "id,webViewLink,webContentLink,name,size,mimeType"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )

        if resp_meta.status_code != 200:
            logger.warning("메타 조회 실패: %s %s", resp_meta.status_code, resp_meta.text)
            meta = resp.json()
        else:
            meta = resp_meta.json()

        result = {
            "success": True,
            "message": "파일이 성공적으로 업로드되었습니다.",
            "filename": new_filename,
            "original_filename": file.filename,
            "file_size": len(file_bytes),
            "file_id": meta.get("id"),
            "web_view_link": meta.get("webViewLink"),
            "web_content_link": meta.get("webContentLink"),
            "mime_type": meta.get("mimeType", mime_type),
        }

        # 옵션: anyone-with-link viewer 권한 부여
        try:
            if share == "link" and file_id:
                perm_body = {"role": "reader", "type": "anyone"}
                perm_resp = requests.post(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    params={"fields": "id"},
                    json=perm_body,
                    timeout=20,
                )
                if perm_resp.status_code not in (200, 201):
                    logger.warning("권한 부여 실패: %s %s", perm_resp.status_code, perm_resp.text)
                else:
                    # 공개 링크 보장을 위해 메타 재조회
                    resp_meta2 = requests.get(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}",
                        params={"fields": "id,webViewLink,webContentLink"},
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=20,
                    )
                    if resp_meta2.status_code == 200:
                        m2 = resp_meta2.json()
                        result["web_view_link"] = m2.get("webViewLink")
                        result["web_content_link"] = m2.get("webContentLink")
        except Exception as perm_e:
            logger.warning("권한 부여 처리 중 경고: %s", perm_e)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"공지사항 파일 업로드 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"공지사항 파일 업로드 중 오류가 발생했습니다: {str(e)}")


@router.post("/", response_model=NoticeResponse)
async def create_notice(
    notice_data: NoticeCreate,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """공지사항 작성 (관리자)"""
    try:
        # 공지사항 생성
        notice = Notice(            title=notice_data.title,
            content=notice_data.content,
            type=NoticeType[notice_data.type.name] if hasattr(notice_data.type, 'name') else NoticeType(notice_data.type.value) if hasattr(notice_data.type, 'value') else NoticeType(notice_data.type),
            author_id=current_user['id'],
            is_important=notice_data.is_important,
            is_published=notice_data.is_published,
            published_at=datetime.now() if notice_data.is_published else None,
            attachment_file=notice_data.attachment_file,
            web_view_link=notice_data.web_view_link
        )
        
        db.add(notice)
        db.commit()
        db.refresh(notice)
        
        # 새 공지사항 알림 전송 (발행된 경우에만)
        if getattr(notice, 'is_published', False):
            try:
                await send_new_notice_notification(notice.id, db)
            except Exception as e:
                print(f"새 공지사항 알림 전송 실패: {e}")
        
        view_count = getattr(notice, 'view_count', 0)
        
        return NoticeResponse(
            id=notice.id,            title=notice.title,
            content=notice.content,
            type=notice.type.value,
            is_important=notice.is_important,
            is_published=getattr(notice, 'is_published', False),
            view_count=view_count,
            published_at=getattr(notice, 'published_at', None),
            attachment_file=getattr(notice, 'attachment_file', None),
            web_view_link=getattr(notice, 'web_view_link', None),
            created_at=notice.created_at,
            updated_at=notice.updated_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"공지사항 작성 실패: {str(e)}")


@router.get("/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: int,
    db: Session = Depends(get_db)
):
    """공지사항 상세 조회"""
    try:
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")
        
        # 조회수 증가
        notice.view_count = (notice.view_count or 0) + 1
        db.commit()
        
        view_count = getattr(notice, 'view_count', 0)
        
        return NoticeResponse(
            id=notice.id,            title=notice.title,
            content=notice.content,
            type=notice.type.value,
            is_important=notice.is_important,
            is_published=getattr(notice, 'is_published', False),
            view_count=view_count,
            published_at=getattr(notice, 'published_at', None),
            attachment_file=getattr(notice, 'attachment_file', None),
            web_view_link=getattr(notice, 'web_view_link', None),
            created_at=notice.created_at,
            updated_at=notice.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공지사항 조회 실패: {str(e)}")


@router.put("/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: int,
    notice_data: NoticeUpdate,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """공지사항 수정 (관리자)"""
    try:
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")
        
        # 업데이트할 필드만 수정
        update_data = notice_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "type":
                # Enum 인스턴스인 경우 .value를 사용, 문자열인 경우 그대로 사용
                type_value = value.value if hasattr(value, 'value') else value
                setattr(notice, field, NoticeType(type_value))
            else:
                setattr(notice, field, value)
        
        # 발행 상태가 변경된 경우 published_at 업데이트
        if "is_published" in update_data and update_data["is_published"]:
            published_at = getattr(notice, 'published_at', None)
            if not published_at:
                notice.published_at = datetime.now()
        
        notice.updated_at = datetime.now()
        
        db.commit()
        db.refresh(notice)
        
        view_count = getattr(notice, 'view_count', 0)
        
        return NoticeResponse(
            id=notice.id,            title=notice.title,
            content=notice.content,
            type=notice.type.value,
            is_important=notice.is_important,
            is_published=getattr(notice, 'is_published', False),
            view_count=view_count,
            published_at=getattr(notice, 'published_at', None),
            attachment_file=getattr(notice, 'attachment_file', None),
            web_view_link=getattr(notice, 'web_view_link', None),
            created_at=notice.created_at,
            updated_at=notice.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"공지사항 수정 실패: {str(e)}")


@router.delete("/{notice_id}")
async def delete_notice(
    notice_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """공지사항 삭제 (관리자)"""
    try:
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")
        
        db.delete(notice)
        db.commit()
        
        return {"message": "공지사항이 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"공지사항 삭제 실패: {str(e)}")


@router.get("/types/", response_model=List[dict])
async def get_notice_types():
    """공지사항 타입 목록 조회"""
    return [
        {"id": "GENERAL", "name": "일반"},
        {"id": "SYSTEM", "name": "시스템"},
        {"id": "EVENT", "name": "이벤트"},
        {"id": "MAINTENANCE", "name": "점검"}
    ]


async def send_new_notice_notification(notice_id: int, db: Session):
    """새 공지사항 알림 전송"""
    try:
        from utils import generate_cuid
        
        # 공지사항 정보 조회
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            logger.error(f"공지사항을 찾을 수 없습니다: {notice_id}")
            return
        
        # 모든 활성 사용자 조회
        users = db.query(User).filter(
            User.status == 'ACTIVE',
            User.deleted_at.is_(None)
        ).all()
        
        if not users:
            logger.info("알림을 받을 사용자가 없습니다.")
            return
        
        # 각 사용자에게 알림 전송
        sent_count = 0
        for user in users:
            try:
                notification = Notification(
                    user_id=user.id,
                    type=NotificationType.NEW_NOTICE.value,
                    title=f"새 공지사항 - {notice.title}",
                    content=f"""
새로운 공지사항이 등록되었습니다.

📢 제목: {notice.title}
📅 등록일: {getattr(notice, 'published_at', None).strftime('%Y년 %m월 %d일 %H:%M') if getattr(notice, 'published_at', None) else '알 수 없음'}
{'⭐ 중요 공지사항입니다.' if getattr(notice, 'is_important', False) else ''}

자세한 내용은 공지사항에서 확인해주세요.
                    """.strip(),
                    status=NotificationStatus.UNREAD.value
                )
                
                db.add(notification)
                sent_count += 1
                
            except Exception as e:
                logger.error(f"새 공지사항 알림 생성 실패 - user_id: {user.id}, error: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"새 공지사항 알림 전송 완료 - notice_id: {notice_id}, sent_count: {sent_count}")
        
    except Exception as e:
        logger.error(f"새 공지사항 알림 전송 실패: {e}")
        db.rollback()
        raise
