from datetime import datetime
from typing import Optional

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from models.region import Sido, Gungu

ADMIN_REGION_API_URL = settings.ADMIN_REGION_API_URL
DATA_GO_KR_API_KEY = settings.DATA_GO_KR_API_KEY


def get_active_sido_list(db: Session) -> list[dict]:
    sidos = db.query(Sido).filter(Sido.is_active == True).order_by(Sido.code).all()
    return [{"code": sido.code, "name": sido.name} for sido in sidos]


def get_active_gungu_list(db: Session, sido_code: str) -> list[dict]:
    gungus = (db.query(Gungu).filter(Gungu.is_active == True, Gungu.sido_code == sido_code).order_by(Gungu.code).all())
    return [{"code": gungu.code, "name": gungu.name} for gungu in gungus]


def validate_sido_code(db: Session, sido_code: str) -> None:
    if not sido_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="시도를 선택하셔야 합니다.")

    sido = db.query(Sido).filter(Sido.code == sido_code, Sido.is_active == True).first()
    if not sido:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="존재하지 않는 sido_code입니다.")


def validate_gungu_codes(db: Session, sido_code: str, gungu_codes: list[str]) -> list[str]:
    validate_sido_code(db, sido_code)

    unique_codes = list(dict.fromkeys(gungu_codes))
    if not (1 <= len(unique_codes) <= 4):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="최소 1개를 선택하셔야하며, 최대 4개까지 선택하실 수 있습니다.")

    gungus = db.query(Gungu).filter(Gungu.code.in_(unique_codes), Gungu.is_active == True).all()
    found_codes = {gungu.code for gungu in gungus}
    missing = [code for code in unique_codes if code not in found_codes]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"존재하지 않는 gungu_code가 있습니다: {missing}")

    invalid = [gungu.code for gungu in gungus if gungu.sido_code != sido_code]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"sido_code 하위가 아닌 gungu_code가 있습니다: {invalid}")

    return unique_codes


# 전체 정보 조회
def fetch_all_regions() -> list[dict]:
    page_no = 1
    all_rows: list[dict] = []

    while True:
        params = {
            "ServiceKey": DATA_GO_KR_API_KEY,
            "type": "json",
            "numOfRows": 1000,
            "pageNo": page_no,
            "flag": "Y",
        }

        print("Region API Request : ", params)

        res = requests.get(
            ADMIN_REGION_API_URL,
            params=params,
            timeout=60,
        )
        res.raise_for_status()

        data = res.json()
        print("Region API Result : ", data)

        if not (isinstance(data, dict) and "StanReginCd" in data):
            break

        rows = data["StanReginCd"][1].get("row", [])

        if not rows:
            break

        all_rows.extend(rows)
        page_no += 1

    return all_rows


def _get_region_level(row: dict) -> Optional[str]:
    level = row.get("region_level")
    if level:
        return str(level)

    sgg_cd = str(row.get("sgg_cd", ""))
    umd_cd = str(row.get("umd_cd", ""))
    ri_cd = str(row.get("ri_cd", ""))

    if sgg_cd == "000" and umd_cd == "000" and ri_cd == "00":
        return "1"
    if sgg_cd != "000" and umd_cd == "000" and ri_cd == "00":
        return "2"
    return None


def _to_str(value) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value if value != "" else None


def _derive_sido_name(locatadd_nm: str) -> str:
    return locatadd_nm.split(" ")[0] if locatadd_nm else ""


# db 갱신
def sync_regions(db: Session, rows: list[dict]) -> dict:
    now = datetime.utcnow()

    inserted_sido = updated_sido = 0
    inserted_sigungu = updated_sigungu = 0
    reactivated_sido = reactivated_sigungu = 0

    # 전체 비활성화
    db.query(Sido).update({"is_active": False})
    db.query(Gungu).update({"is_active": False})

    sido_rows = []
    gungu_rows = []
    for row in rows:
        level = _get_region_level(row)
        if level == "1":
            sido_rows.append(row)
        elif level == "2":
            gungu_rows.append(row)

    for row in sido_rows:
        region_cd = row["region_cd"]
        sido_cd = row["sido_cd"]
        sgg_cd = row["sgg_cd"]
        umd_cd = row["umd_cd"]
        ri_cd = row["ri_cd"]
        full_name = row["locatadd_nm"]

        key = sido_cd
        sido = db.get(Sido, key)

        if not sido:
            sido = Sido(
                code=key,
                region_cd=region_cd,
                sido_cd=sido_cd,
                sgg_cd=sgg_cd,
                umd_cd=umd_cd,
                ri_cd=ri_cd,
                name=full_name,
                locatjumin_cd=_to_str(row.get("locatjumin_cd")),
                locatjijuk_cd=_to_str(row.get("locatjijuk_cd")),
                locat_order=_to_str(row.get("locat_order")),
                locat_rm=_to_str(row.get("locat_rm")),
                locathigh_cd=_to_str(row.get("locathigh_cd")),
                locallow_nm=_to_str(row.get("locallow_nm")),
                adpt_de=_to_str(row.get("adpt_de")),
                is_active=True,
                updated_at=now,
            )
            db.add(sido)
            inserted_sido += 1
        else:
            if not sido.is_active:
                reactivated_sido += 1

            if sido.name != full_name:
                updated_sido += 1

            sido.region_cd = region_cd
            sido.sido_cd = sido_cd
            sido.sgg_cd = sgg_cd
            sido.umd_cd = umd_cd
            sido.ri_cd = ri_cd
            sido.name = full_name
            sido.locatjumin_cd = _to_str(row.get("locatjumin_cd"))
            sido.locatjijuk_cd = _to_str(row.get("locatjijuk_cd"))
            sido.locat_order = _to_str(row.get("locat_order"))
            sido.locat_rm = _to_str(row.get("locat_rm"))
            sido.locathigh_cd = _to_str(row.get("locathigh_cd"))
            sido.locallow_nm = _to_str(row.get("locallow_nm"))
            sido.adpt_de = _to_str(row.get("adpt_de"))
            sido.is_active = True
            sido.updated_at = now

    db.flush()

    for row in gungu_rows:
        region_cd = row["region_cd"]
        sido_cd = row["sido_cd"]
        sgg_cd = row["sgg_cd"]
        umd_cd = row["umd_cd"]
        ri_cd = row["ri_cd"]
        full_name = row["locatadd_nm"]

        # 시도 행이 누락된 경우(순서/데이터 미포함), 최소 정보로 시도 생성
        if not db.get(Sido, sido_cd):
            sido_name = _derive_sido_name(full_name)
            sido = Sido(
                code=sido_cd,
                region_cd=_to_str(row.get("locathigh_cd")) or f"{sido_cd}00000000",
                sido_cd=sido_cd,
                sgg_cd="000",
                umd_cd="000",
                ri_cd="00",
                name=sido_name,
                locatjumin_cd=None,
                locatjijuk_cd=None,
                locat_order=None,
                locat_rm=None,
                locathigh_cd=None,
                locallow_nm=sido_name,
                adpt_de=None,
                is_active=True,
                updated_at=now,
            )
            db.add(sido)
            db.flush()

        key = f"{sido_cd}{sgg_cd}"
        sigungu = db.get(Gungu, key)

        if not sigungu:
            sigungu = Gungu(
                code=key,
                sido_code=sido_cd,
                region_cd=region_cd,
                sido_cd=sido_cd,
                sgg_cd=sgg_cd,
                umd_cd=umd_cd,
                ri_cd=ri_cd,
                name=full_name,
                locatjumin_cd=_to_str(row.get("locatjumin_cd")),
                locatjijuk_cd=_to_str(row.get("locatjijuk_cd")),
                locat_order=_to_str(row.get("locat_order")),
                locat_rm=_to_str(row.get("locat_rm")),
                locathigh_cd=_to_str(row.get("locathigh_cd")),
                locallow_nm=_to_str(row.get("locallow_nm")),
                adpt_de=_to_str(row.get("adpt_de")),
                is_active=True,
                updated_at=now,
            )
            db.add(sigungu)
            inserted_sigungu += 1
        else:
            if not sigungu.is_active:
                reactivated_sigungu += 1

            if sigungu.name != full_name:
                updated_sigungu += 1

            sigungu.region_cd = region_cd
            sigungu.sido_cd = sido_cd
            sigungu.sgg_cd = sgg_cd
            sigungu.umd_cd = umd_cd
            sigungu.ri_cd = ri_cd
            sigungu.name = full_name
            sigungu.locatjumin_cd = _to_str(row.get("locatjumin_cd"))
            sigungu.locatjijuk_cd = _to_str(row.get("locatjijuk_cd"))
            sigungu.locat_order = _to_str(row.get("locat_order"))
            sigungu.locat_rm = _to_str(row.get("locat_rm"))
            sigungu.locathigh_cd = _to_str(row.get("locathigh_cd"))
            sigungu.locallow_nm = _to_str(row.get("locallow_nm"))
            sigungu.adpt_de = _to_str(row.get("adpt_de"))
            sigungu.is_active = True
            sigungu.updated_at = now

    db.commit()

    return {
        "sido": {
            "inserted": inserted_sido,
            "updated": updated_sido,
            "reactivated": reactivated_sido,
        },
        "sigungu": {
            "inserted": inserted_sigungu,
            "updated": updated_sigungu,
            "reactivated": reactivated_sigungu,
        },
    }
