from abc import ABC, abstractmethod
from typing import Optional

from src.core.models import PostContent


class ContentGeneratorInterface(ABC):
    """콘텐츠 생성기 인터페이스"""

    @abstractmethod
    async def generate_content(self, topic: str, **kwargs) -> PostContent:
        """콘텐츠 생성"""
        pass


class OutlineGeneratorInterface(ABC):
    """개요 생성기 인터페이스"""

    @abstractmethod
    async def generate_outline(self, topic: str) -> list[str]:
        """개요 생성"""
        pass


class ContentWriterInterface(ABC):
    """콘텐츠 작성기 인터페이스"""

    @abstractmethod
    async def write_content(self, topic: str, outline: list[str]) -> str:
        """콘텐츠 작성"""
        pass


class SEOOptimizerInterface(ABC):
    """SEO 최적화기 인터페이스"""

    @abstractmethod
    async def optimize_content(self, content: str, topic: str) -> dict[str, str]:
        """SEO 최적화"""
        pass


class ImageGeneratorInterface(ABC):
    """이미지 생성기 인터페이스"""

    @abstractmethod
    async def generate_image(
        self, 
        prompt: str, 
        output_path: str,
        alt_text: Optional[str] = None
    ) -> str:
        """이미지 생성"""
        pass