from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Sido(Base):
    __tablename__ = "sido"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    region_cd: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    sido_cd: Mapped[str] = mapped_column(String(2), nullable=False)
    sgg_cd: Mapped[str] = mapped_column(String(3), nullable=False)
    umd_cd: Mapped[str] = mapped_column(String(3), nullable=False)
    ri_cd: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    locatjumin_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locatjijuk_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locat_order: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    locat_rm: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    locathigh_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locallow_nm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    adpt_de: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Gungu(Base):
    __tablename__ = "gungu"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    sido_code: Mapped[str] = mapped_column(String(2), ForeignKey("sido.code"), nullable=False)
    region_cd: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    sido_cd: Mapped[str] = mapped_column(String(2), nullable=False)
    sgg_cd: Mapped[str] = mapped_column(String(3), nullable=False)
    umd_cd: Mapped[str] = mapped_column(String(3), nullable=False)
    ri_cd: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    locatjumin_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locatjijuk_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locat_order: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    locat_rm: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    locathigh_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    locallow_nm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    adpt_de: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
