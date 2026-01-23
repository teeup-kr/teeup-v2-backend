from collections import defaultdict
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.region import Sido, Gungu
from utils.region import fetch_all_regions, sync_regions

logger = logging.getLogger(__name__)

# 저장된 리스트 조회 라우터
region_router = APIRouter(prefix="", tags=["region"])


@region_router.get("/region-list")
def get_region_list(db: Session = Depends(get_db)):
    # 1. 활성 시도 전체
    sidos = (db.query(Sido).filter(Sido.is_active == True).order_by(Sido.code).all())

    # 2. 활성 시군구 전체
    sigungus = (db.query(Gungu).filter(Gungu.is_active == True).order_by(Gungu.code).all())

    # 3. 시도코드 기준으로 시군구 묶기
    sigungu_map = defaultdict(list)
    for s in sigungus:
        sigungu_map[s.sido_code].append({
            "code": s.code,
            "name": s.name,
        })

    # 4. 계층화 결과 생성
    result = []
    for sido in sidos:
        result.append({
            "code": sido.code,
            "name": sido.name,
            "sigungu": sigungu_map.get(sido.code, []),
        })

    return result


# 테스트용
@region_router.post("/region-list")
def refresh_region_list(db: Session = Depends(get_db)):
    regions = fetch_all_regions()
    result = sync_regions(db, regions)

    return {"success": True, "fetchedCount": len(regions), "syncedCount": result.get("synced", None), "message": "Region list synchronized successfully"}

    # return fetch_all_regions()
