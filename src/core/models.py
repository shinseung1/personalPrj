from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class PostStatus(str, Enum):
    """포스트 상태"""
    DRAFT = "draft"
    PUBLISH = "publish"
    FUTURE = "future"
    PRIVATE = "private"


class ScheduleMode(str, Enum):
    """스케줄 모드"""
    DRAFT = "draft"
    PUBLISH = "publish"
    SCHEDULE = "schedule"


class ImageInfo(BaseModel):
    """이미지 정보"""
    path: str = Field(..., description="이미지 경로")
    alt: str = Field(..., description="이미지 ALT 텍스트")
    use_as_featured: bool = Field(default=False, description="대표 이미지로 사용")
    wp_media_id: Optional[int] = Field(default=None, description="WordPress 미디어 ID")


class ScheduleInfo(BaseModel):
    """스케줄 정보"""
    mode: ScheduleMode = Field(..., description="스케줄 모드")
    scheduled_at: datetime | None = Field(default=None, description="예약 일시")  # ← 이름 변경


class PostContent(BaseModel):
    """포스트 콘텐츠"""
    topic: str = Field(..., description="주제")
    outline: list[str] = Field(..., description="개요")
    content_html: str = Field(..., description="HTML 콘텐츠")
    excerpt: str = Field(..., description="요약")
    slug: str = Field(..., description="슬러그")
    categories: list[str] = Field(..., description="카테고리")
    tags: list[str] = Field(..., description="태그")
    images: list[ImageInfo] = Field(default_factory=list, description="이미지")
    schedule: ScheduleInfo = Field(..., description="스케줄 정보")


class WordPressPost(BaseModel):
    """WordPress 포스트"""
    id: Optional[int] = Field(default=None, description="포스트 ID")
    title: str = Field(..., description="제목")
    content: str = Field(..., description="내용")
    excerpt: str = Field(..., description="요약")
    slug: str = Field(..., description="슬러그")
    status: PostStatus = Field(..., description="상태")
    date: Optional[datetime] = Field(default=None, description="게시 일시")
    categories: list[int] = Field(default_factory=list, description="카테고리 ID")
    tags: list[int] = Field(default_factory=list, description="태그 ID")
    featured_media: Optional[int] = Field(default=None, description="대표 이미지 ID")
    meta: dict[str, Any] = Field(default_factory=dict, description="메타 데이터")


class WordPressMedia(BaseModel):
    """WordPress 미디어"""
    id: Optional[int] = Field(default=None, description="미디어 ID")
    title: str = Field(..., description="제목")
    alt_text: str = Field(..., description="ALT 텍스트")
    source_url: Optional[str] = Field(default=None, description="소스 URL")
    mime_type: Optional[str] = Field(default=None, description="MIME 타입")


class Category(BaseModel):
    """카테고리"""
    id: Optional[int] = Field(default=None, description="카테고리 ID")
    name: str = Field(..., description="카테고리 이름")
    slug: str = Field(..., description="슬러그")


class Tag(BaseModel):
    """태그"""
    id: Optional[int] = Field(default=None, description="태그 ID")
    name: str = Field(..., description="태그 이름")
    slug: str = Field(..., description="슬러그")


class QualityCheckResult(BaseModel):
    """품질 검사 결과"""
    passed: bool = Field(..., description="검사 통과 여부")
    score: float = Field(..., description="품질 점수 (0-100)")
    issues: list[str] = Field(default_factory=list, description="발견된 문제점")
    suggestions: list[str] = Field(default_factory=list, description="개선 제안")


class GenerationJob(BaseModel):
    """생성 작업"""
    id: str = Field(..., description="작업 ID")
    topic: str = Field(..., description="주제")
    status: str = Field(..., description="상태")
    created_at: datetime = Field(..., description="생성 시간")
    scheduled_at: datetime | None = Field(default=None, description="예약 일시")
    completed_at: Optional[datetime] = Field(default=None, description="완료 시간")
    wp_post_id: Optional[int] = Field(default=None, description="WordPress 포스트 ID")
    error_message: Optional[str] = Field(default=None, description="에러 메시지")
    content: Optional[PostContent] = Field(default=None, description="생성된 콘텐츠")