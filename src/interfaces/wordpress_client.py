from abc import ABC, abstractmethod
from typing import Optional

from src.core.models import WordPressPost, WordPressMedia, Category, Tag


class WordPressClientInterface(ABC):
    """WordPress 클라이언트 인터페이스 (Interface Segregation Principle)"""

    @abstractmethod
    async def create_post(self, post: WordPressPost) -> WordPressPost:
        """포스트 생성"""
        pass

    @abstractmethod
    async def update_post(self, post_id: int, post: WordPressPost) -> WordPressPost:
        """포스트 업데이트"""
        pass

    @abstractmethod
    async def get_post(self, post_id: int) -> Optional[WordPressPost]:
        """포스트 조회"""
        pass

    @abstractmethod
    async def delete_post(self, post_id: int) -> bool:
        """포스트 삭제"""
        pass

    @abstractmethod
    async def upload_media(self, file_path: str, title: str, alt_text: str) -> WordPressMedia:
        """미디어 업로드"""
        pass

    @abstractmethod
    async def get_categories(self) -> list[Category]:
        """카테고리 목록 조회"""
        pass

    @abstractmethod
    async def create_category(self, name: str, slug: str) -> Category:
        """카테고리 생성"""
        pass

    @abstractmethod
    async def get_tags(self) -> list[Tag]:
        """태그 목록 조회"""
        pass

    @abstractmethod
    async def create_tag(self, name: str, slug: str) -> Tag:
        """태그 생성"""
        pass