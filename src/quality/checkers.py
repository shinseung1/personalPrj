import re
from typing import Optional
from bs4 import BeautifulSoup
import httpx
from openai import AsyncOpenAI

from src.core.config import settings
from src.core.models import QualityCheckResult, PostContent
from src.interfaces.quality_checker import (
    QualityCheckerInterface,
    SpellCheckerInterface,
    PlagiarismCheckerInterface,
    GrammarCheckerInterface,
    LinkCheckerInterface
)


class OpenAISpellChecker(SpellCheckerInterface):
    """OpenAI를 사용한 맞춤법 검사기"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def check_spelling(self, text: str) -> list[str]:
        """맞춤법 검사"""
        prompt = f"""
다음 텍스트의 맞춤법 오류를 찾아주세요:

{text[:2000]}  # 텍스트 길이 제한

오류가 있다면 다음 형식으로 반환해주세요:
- [오류] -> [수정안]

오류가 없다면 "오류 없음"이라고 반환해주세요.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        
        if "오류 없음" in result:
            return []
        
        # 오류 파싱
        errors = []
        for line in result.split('\n'):
            if '->' in line:
                errors.append(line.strip())
        
        return errors


class SimpleGrammarChecker(GrammarCheckerInterface):
    """간단한 문법 검사기"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def check_grammar(self, text: str) -> list[str]:
        """문법 검사"""
        prompt = f"""
다음 텍스트의 문법 오류를 찾아주세요:

{text[:2000]}  # 텍스트 길이 제한

문법 오류가 있다면 간단히 설명해주세요.
문제없다면 "문법 오류 없음"이라고 반환해주세요.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        
        if "문법 오류 없음" in result:
            return []
        
        return [result]


class SimplePlagiarismChecker(PlagiarismCheckerInterface):
    """간단한 표절 검사기 (웹 검색 기반)"""

    async def check_plagiarism(self, text: str) -> float:
        """표절 검사 - 유사도 점수 반환"""
        # 텍스트에서 특징적인 구문 추출
        sentences = self._extract_unique_sentences(text)
        
        if not sentences:
            return 0.0
        
        similarity_scores = []
        
        # 각 문장에 대해 웹 검색 수행
        for sentence in sentences[:3]:  # 최대 3개 문장만 검사
            score = await self._check_sentence_similarity(sentence)
            similarity_scores.append(score)
        
        # 평균 유사도 반환
        return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

    def _extract_unique_sentences(self, text: str) -> list[str]:
        """특징적인 문장 추출"""
        # HTML 태그 제거
        soup = BeautifulSoup(text, 'html.parser')
        clean_text = soup.get_text()
        
        # 문장 분리
        sentences = re.split(r'[.!?]\s+', clean_text)
        
        # 10글자 이상의 의미있는 문장만 선택
        unique_sentences = [
            s.strip() for s in sentences 
            if len(s.strip()) > 10 and not s.strip().startswith(('그런데', '하지만', '또한'))
        ]
        
        return unique_sentences[:5]  # 최대 5개

    async def _check_sentence_similarity(self, sentence: str) -> float:
        """문장의 웹상 유사도 검사"""
        try:
            # 간단한 웹 검색 (실제로는 더 정교한 API 사용 권장)
            async with httpx.AsyncClient() as client:
                # Google 검색 시뮬레이션 (실제로는 검색 API 사용)
                response = await client.get(
                    f"https://www.google.com/search?q=\"{sentence}\"",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=5.0
                )
                
                # 검색 결과가 많으면 유사도가 높다고 가정
                content = response.text
                if "검색결과가 없습니다" in content or "did not match" in content:
                    return 0.0
                else:
                    return 30.0  # 기본 유사도 점수
                    
        except Exception:
            return 0.0  # 오류 시 유사도 0


class LinkChecker(LinkCheckerInterface):
    """링크 검사기"""

    async def check_links(self, html_content: str) -> list[str]:
        """404 링크 검사"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        broken_links = []
        
        for link in links:
            url = link['href']
            if url.startswith(('http://', 'https://')):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.head(url, timeout=10.0)
                        if response.status_code >= 400:
                            broken_links.append(url)
                except Exception:
                    broken_links.append(url)
        
        return broken_links


class ComprehensiveQualityChecker(QualityCheckerInterface):
    """종합 품질 검사기 (Composite Pattern)"""

    def __init__(self):
        self.spell_checker = OpenAISpellChecker(settings.openai_api_key)
        self.grammar_checker = SimpleGrammarChecker(settings.openai_api_key)
        self.plagiarism_checker = SimplePlagiarismChecker()
        self.link_checker = LinkChecker()

    async def check_quality(self, content: PostContent) -> QualityCheckResult:
        """종합 품질 검사"""
        issues = []
        suggestions = []
        score = 100.0  # 시작 점수
        
        # 1. 기본 검증
        word_count = self._count_words(content.content_html)
        if word_count < settings.min_word_count:
            issues.append(f"내용이 너무 짧습니다 ({word_count}자, 최소 {settings.min_word_count}자)")
            score -= 20
        elif word_count > settings.max_word_count:
            issues.append(f"내용이 너무 깁니다 ({word_count}자, 최대 {settings.max_word_count}자)")
            score -= 10
        
        # 2. 맞춤법 검사
        if settings.grammar_check_enabled:
            spell_errors = await self.spell_checker.check_spelling(content.content_html)
            if spell_errors:
                issues.extend(spell_errors)
                score -= len(spell_errors) * 5
        
        # 3. 문법 검사  
        grammar_errors = await self.grammar_checker.check_grammar(content.content_html)
        if grammar_errors:
            issues.extend(grammar_errors)
            score -= len(grammar_errors) * 3
        
        # 4. 표절 검사
        if settings.plagiarism_check_enabled:
            similarity_score = await self.plagiarism_checker.check_plagiarism(content.content_html)
            if similarity_score > 50:
                issues.append(f"높은 유사도 검출: {similarity_score:.1f}%")
                score -= similarity_score / 2
        
        # 5. 링크 검사
        broken_links = await self.link_checker.check_links(content.content_html)
        if broken_links:
            issues.extend([f"깨진 링크: {link}" for link in broken_links])
            score -= len(broken_links) * 10
        
        # 6. SEO 검사
        if not content.excerpt or len(content.excerpt) < 50:
            issues.append("메타 설명이 너무 짧습니다")
            score -= 5
            
        if len(content.slug) > 50:
            issues.append("슬러그가 너무 깁니다")
            score -= 3
        
        # 7. 개선 제안 생성
        if word_count < 1000:
            suggestions.append("더 자세한 내용을 추가하여 독자에게 더 많은 가치를 제공하세요")
        
        if not content.images:
            suggestions.append("시각적 요소를 추가하여 독자 경험을 향상시키세요")
        
        # 최종 점수 계산
        final_score = max(0, min(100, score))
        passed = final_score >= 70 and len(issues) <= 3
        
        return QualityCheckResult(
            passed=passed,
            score=final_score,
            issues=issues,
            suggestions=suggestions
        )

    def _count_words(self, html_content: str) -> int:
        """단어 수 계산"""
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # 한국어 단어 수 계산 (공백 기준)
        words = len([word for word in text.split() if word.strip()])
        return words


def create_quality_checker() -> ComprehensiveQualityChecker:
    """품질 검사기 팩토리 함수"""
    return ComprehensiveQualityChecker()