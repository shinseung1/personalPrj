import json
from typing import Optional
from openai import AsyncOpenAI
from slugify import slugify

from src.core.config import settings
from src.core.models import PostContent, ScheduleInfo, ImageInfo
from src.interfaces.content_generator import (
    ContentGeneratorInterface, 
    OutlineGeneratorInterface, 
    ContentWriterInterface, 
    SEOOptimizerInterface
)


class OpenAIOutlineGenerator(OutlineGeneratorInterface):
    """OpenAI를 사용한 개요 생성기"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_outline(self, topic: str) -> list[str]:
        """주제에 대한 개요 생성"""
        prompt = f"""
주제 "{topic}"에 대한 블로그 포스트의 개요를 생성해주세요.
다음 조건을 만족해야 합니다:
- 5-8개의 주요 섹션으로 구성
- 각 섹션은 H2 또는 H3 헤딩 형태
- SEO와 독자 관심을 고려한 구성
- 한국어로 작성

JSON 배열 형태로 반환해주세요:
["섹션1", "섹션2", "섹션3", ...]
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # JSON 파싱 실패시 줄바꿈으로 분리
            return [line.strip() for line in content.split('\n') if line.strip()]


class OpenAIContentWriter(ContentWriterInterface):
    """OpenAI를 사용한 콘텐츠 작성기"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def write_content(self, topic: str, outline: list[str]) -> str:
        """개요를 바탕으로 콘텐츠 작성"""
        outline_text = '\n'.join([f"- {section}" for section in outline])
        
        prompt = f"""
주제: "{topic}"
개요:
{outline_text}

위의 개요를 바탕으로 상세한 블로그 포스트를 작성해주세요.
다음 조건을 만족해야 합니다:
- HTML 형태로 작성 (h1, h2, h3, p, ul, li 태그 사용)
- 각 섹션별로 충분한 내용 (최소 2-3 문단)
- SEO를 고려한 키워드 자연스러운 배치
- 독자에게 유용한 정보 제공
- 한국어로 작성
- 최소 800단어 이상

HTML 콘텐츠만 반환해주세요 (다른 설명 불필요):
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content


class OpenAISEOOptimizer(SEOOptimizerInterface):
    """OpenAI를 사용한 SEO 최적화기"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def optimize_content(self, content: str, topic: str) -> dict[str, str]:
        """SEO 최적화된 메타 정보 생성"""
        prompt = f"""
주제: "{topic}"
콘텐츠:
{content[:1000]}...

위의 콘텐츠를 바탕으로 SEO 최적화된 메타 정보를 생성해주세요:
- title: 매력적이고 SEO 친화적인 제목 (60자 이내)
- excerpt: 검색 엔진용 설명문 (150자 이내)
- slug: URL 친화적인 슬러그 (영문)
- keywords: 관련 키워드 (5개 이내, 쉼표로 구분)

JSON 형태로 반환해주세요:
{
    "title": "제목",
    "excerpt": "설명문",
    "slug": "url-slug",
    "keywords": "키워드1,키워드2,키워드3"
}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # 기본값 반환
            return {
                "title": topic,
                "excerpt": f"{topic}에 대한 상세한 정보를 제공합니다.",
                "slug": slugify(topic),
                "keywords": topic
            }


class OpenAIContentGenerator(ContentGeneratorInterface):
    """OpenAI 기반 통합 콘텐츠 생성기 (Facade Pattern)"""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.outline_generator = OpenAIOutlineGenerator(api_key, model)
        self.content_writer = OpenAIContentWriter(api_key, model)
        self.seo_optimizer = OpenAISEOOptimizer(api_key, model)

    async def generate_content(
        self, 
        topic: str, 
        schedule_info: Optional[ScheduleInfo] = None,
        categories: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        **kwargs
    ) -> PostContent:
        """완전한 콘텐츠 생성"""
        
        # 1. 개요 생성
        outline = await self.outline_generator.generate_outline(topic)
        
        # 2. 콘텐츠 작성
        content_html = await self.content_writer.write_content(topic, outline)
        
        # 3. SEO 최적화
        seo_meta = await self.seo_optimizer.optimize_content(content_html, topic)
        
        # 4. 기본값 설정
        if not schedule_info:
            from src.core.models import ScheduleMode
            schedule_info = ScheduleInfo(mode=ScheduleMode.DRAFT)
            
        if not categories:
            categories = [settings.default_category]
            
        if not tags:
            tags = settings.default_tags_list
            
        return PostContent(
            topic=topic,
            outline=outline,
            content_html=content_html,
            excerpt=seo_meta["excerpt"],
            slug=seo_meta["slug"],
            categories=categories,
            tags=tags,
            images=[],  # 이미지는 별도 모듈에서 처리
            schedule=schedule_info
        )


def create_openai_content_generator() -> OpenAIContentGenerator:
    """OpenAI 콘텐츠 생성기 팩토리 함수"""
    return OpenAIContentGenerator(
        api_key=settings.openai_api_key,
        model=settings.openai_model
    )