from abc import ABC, abstractmethod

from src.core.models import QualityCheckResult, PostContent


class QualityCheckerInterface(ABC):
    """품질 검사기 인터페이스"""

    @abstractmethod
    async def check_quality(self, content: PostContent) -> QualityCheckResult:
        """품질 검사"""
        pass


class SpellCheckerInterface(ABC):
    """맞춤법 검사기 인터페이스"""

    @abstractmethod
    async def check_spelling(self, text: str) -> list[str]:
        """맞춤법 검사"""
        pass


class PlagiarismCheckerInterface(ABC):
    """표절 검사기 인터페이스"""

    @abstractmethod
    async def check_plagiarism(self, text: str) -> float:
        """표절 검사 - 유사도 점수 반환 (0-100)"""
        pass


class GrammarCheckerInterface(ABC):
    """문법 검사기 인터페이스"""

    @abstractmethod
    async def check_grammar(self, text: str) -> list[str]:
        """문법 검사"""
        pass


class LinkCheckerInterface(ABC):
    """링크 검사기 인터페이스"""

    @abstractmethod
    async def check_links(self, html_content: str) -> list[str]:
        """링크 검사 - 404 링크 반환"""
        pass