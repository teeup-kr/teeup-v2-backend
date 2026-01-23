from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from utils.region import fetch_all_regions, sync_regions, get_active_sido_list, get_active_gungu_list, validate_sido_code

# 저장된 리스트 조회 라우터
region_router = APIRouter(prefix="", tags=["region"])


@region_router.get("/sido-list")
def get_sido_list(db: Session = Depends(get_db)):
    return get_active_sido_list(db)


@region_router.get("/gungu-list")
def get_gungu_list(sido_code: str = Query(..., description="시도 코드"), db: Session = Depends(get_db)):
    validate_sido_code(db, sido_code)
    return get_active_gungu_list(db, sido_code)


# 테스트용
@region_router.post("/region-list")
def refresh_region_list(db: Session = Depends(get_db)):
    regions = fetch_all_regions()
    result = sync_regions(db, regions)

    return {"success": True, "fetchedCount": len(regions), "syncedCount": result.get("synced", None), "message": "Region list synchronized successfully"}

    # return fetch_all_regions()
