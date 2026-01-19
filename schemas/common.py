# 기본 응답 스키마
from pydantic import BaseModel
from typing import List, Generic, TypeVar

T = TypeVar('T')

class MessageResponse(BaseModel):
    message: str
    success: bool

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

