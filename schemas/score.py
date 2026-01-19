# 스코어 관련 스키마
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
# 스코어 관련 스키마
class ScoreCreate(BaseModel):
    participant_id: int = Field(..., description="참가자 ID")
    hole_number: int = Field(..., ge=1, le=18, description="홀 번호")
    strokes: int = Field(..., ge=1, le=20, description="타수")
    par: int = Field(..., ge=3, le=6, description="파")
    score_to_par: int = Field(..., description="파 대비 점수")

class ScoreUpdate(BaseModel):
    hole_number: Optional[int] = Field(None, ge=1, le=18, description="홀 번호")
    strokes: Optional[int] = Field(None, ge=1, le=20, description="타수")
    par: Optional[int] = Field(None, ge=3, le=6, description="파")
    score_to_par: Optional[int] = Field(None, description="파 대비 점수")

class ScoreResponse(BaseModel):
    id: int
    participant_id: int
    user_id: int
    user_name: str
    user_nickname: str
    meeting_id: int
    meeting_name: str
    hole_number: int
    strokes: int
    par: int
    score_to_par: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class SimpleScoreCreate(BaseModel):
    gross_score: int = Field(..., ge=55, le=144, description="라운딩 스코어 (55-144)")

class SimpleScoreResponse(BaseModel):
    message: str
    score_history_id: Optional[int] = None
    updated_handicap: Optional[float] = None

class ScoreListResponse(BaseModel):
    scores: List[ScoreResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class ScoreStats(BaseModel):
    total_strokes: int
    total_par: int
    total_score_to_par: int
    average_strokes: float
    average_par: float
    average_score_to_par: float
    best_hole: int
    worst_hole: int
    birdies: int
    pars: int
    bogeys: int
    double_bogeys: int
    triple_bogeys: int
    worse: int

