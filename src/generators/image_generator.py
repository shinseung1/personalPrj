import os
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI
from PIL import Image
import httpx

from src.core.config import settings
from src.core.models import ImageInfo
from src.interfaces.content_generator import ImageGeneratorInterface


class OpenAIImageGenerator(ImageGeneratorInterface):
    """OpenAI DALL-E를 사용한 이미지 생성기"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_image(
        self, 
        prompt: str, 
        output_path: str,
        alt_text: Optional[str] = None
    ) -> str:
        """DALL-E로 이미지 생성"""
        
        # 한국어 프롬프트를 영어로 번역 (간단한 버전)
        english_prompt = await self._translate_prompt(prompt)
        
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=english_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        image_url = response.data[0].url
        
        # 이미지 다운로드
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
            # 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        # WebP로 변환 및 최적화
        optimized_path = await self._optimize_image(output_path)
        
        return optimized_path

    async def _translate_prompt(self, korean_prompt: str) -> str:
        """간단한 프롬프트 번역"""
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"다음 한국어 프롬프트를 DALL-E용 영어 프롬프트로 번역해주세요: {korean_prompt}"
            }],
            temperature=0.3
        )
        return response.choices[0].message.content

    async def _optimize_image(self, image_path: str) -> str:
        """이미지 최적화 (WebP 변환 + 압축)"""
        # 원본 이미지 열기
        with Image.open(image_path) as img:
            # WebP 경로 생성
            webp_path = image_path.rsplit('.', 1)[0] + '.webp'
            
            # WebP로 변환 및 압축
            img.save(webp_path, 'WebP', quality=80, optimize=True)
        
        # 원본 파일 삭제
        os.remove(image_path)
        
        return webp_path


class ImageProcessor:
    """이미지 처리 유틸리티 클래스"""

    @staticmethod
    async def generate_alt_text(image_path: str, topic: str) -> str:
        """이미지에 대한 ALT 텍스트 자동 생성"""
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # 이미지 분석 후 ALT 텍스트 생성
        prompt = f"""
주제 "{topic}"와 관련된 이미지의 ALT 텍스트를 생성해주세요.
- SEO 친화적
- 접근성을 고려한 설명
- 50자 이내
- 한국어

ALT 텍스트만 반환해주세요:
"""
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()

    @staticmethod
    async def create_featured_image(topic: str, output_dir: str = "images") -> ImageInfo:
        """주제에 맞는 대표 이미지 생성"""
        generator = OpenAIImageGenerator(settings.openai_api_key)
        
        # 이미지 프롬프트 생성
        prompt = f"{topic}를 표현하는 현대적이고 전문적인 이미지"
        
        # 파일 경로 생성
        from slugify import slugify
        filename = f"{slugify(topic)}-featured.webp"
        output_path = os.path.join(output_dir, filename)
        
        # 이미지 생성
        image_path = await generator.generate_image(prompt, output_path)
        
        # ALT 텍스트 생성
        alt_text = await ImageProcessor.generate_alt_text(image_path, topic)
        
        return ImageInfo(
            path=image_path,
            alt=alt_text,
            use_as_featured=True
        )


def create_image_generator() -> OpenAIImageGenerator:
    """이미지 생성기 팩토리 함수"""
    return OpenAIImageGenerator(api_key=settings.openai_api_key)