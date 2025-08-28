import uuid
from datetime import datetime
from typing import Optional
from slugify import slugify

from src.core.config import settings
from src.core.models import (
    PostContent, 
    WordPressPost, 
    PostStatus, 
    ScheduleInfo, 
    ScheduleMode,
    GenerationJob
)
from src.wp_client.client import create_wordpress_client
from src.generators.openai_generator import create_openai_content_generator
from src.generators.image_generator import ImageProcessor
from src.quality.checkers import create_quality_checker
from src.services.database_service import DatabaseService


class BlogService:
    """블로그 서비스 (Facade Pattern + Service Layer)"""
    
    def __init__(self):
        self.wp_client = create_wordpress_client()
        self.content_generator = create_openai_content_generator()
        self.quality_checker = create_quality_checker()
        self.db_service = DatabaseService()

    async def create_and_publish_post(
        self,
        topic: str,
        schedule_info: ScheduleInfo,
        categories: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        generate_image: bool = True
    ) -> dict:
        """포스트 생성 및 발행 (메인 워크플로우)"""
        
        # 1. 작업 ID 생성 및 로깅
        job_id = str(uuid.uuid4())
        job = GenerationJob(
            id=job_id,
            topic=topic,
            status="started",
            created_at=datetime.now(),
            scheduled_at=schedule_info.datetime if schedule_info.mode == ScheduleMode.SCHEDULE else None
        )
        
        await self.db_service.save_job(job)
        
        try:
            # 2. 콘텐츠 생성
            content = await self.content_generator.generate_content(
                topic=topic,
                schedule_info=schedule_info,
                categories=categories,
                tags=tags
            )
            
            # 3. 이미지 생성 (선택사항)
            if generate_image:
                featured_image = await ImageProcessor.create_featured_image(topic)
                content.images = [featured_image]
            
            # 4. 품질 검사
            quality_result = await self.quality_checker.check_quality(content)
            
            if not quality_result.passed:
                # 품질 검사 실패 시 임시글로 저장
                content.schedule.mode = ScheduleMode.DRAFT
            
            # 5. WordPress 카테고리/태그 처리
            wp_categories = await self._get_or_create_categories(content.categories)
            wp_tags = await self._get_or_create_tags(content.tags)
            
            # 6. 이미지 업로드
            featured_media_id = None
            if content.images:
                for image in content.images:
                    if image.use_as_featured:
                        media = await self.wp_client.upload_media(
                            file_path=image.path,
                            title=f"{topic} - 대표 이미지",
                            alt_text=image.alt
                        )
                        featured_media_id = media.id
                        image.wp_media_id = media.id
                        break
            
            # 7. WordPress 포스트 생성
            wp_post = WordPressPost(
                title=content.topic,
                content=content.content_html,
                excerpt=content.excerpt,
                slug=content.slug,
                status=self._get_wp_status(content.schedule.mode),
                date=content.schedule.datetime,
                categories=[cat.id for cat in wp_categories],
                tags=[tag.id for tag in wp_tags],
                featured_media=featured_media_id
            )
            
            created_post = await self.wp_client.create_post(wp_post)
            
            # 8. 작업 완료 로깅
            job.status = "completed"
            job.completed_at = datetime.now()
            job.wp_post_id = created_post.id
            job.content = content
            
            await self.db_service.save_job(job)
            
            return {
                "job_id": job_id,
                "wp_post_id": created_post.id,
                "title": created_post.title,
                "status": created_post.status.value,
                "url": f"{settings.wordpress_url}/{created_post.slug}",
                "quality_score": quality_result.score,
                "quality_passed": quality_result.passed,
                "quality_issues": quality_result.issues
            }
            
        except Exception as e:
            # 오류 로깅
            job.status = "failed"
            job.error_message = str(e)
            await self.db_service.save_job(job)
            raise

    async def generate_content_only(self, topic: str) -> PostContent:
        """콘텐츠만 생성 (미리보기용)"""
        return await self.content_generator.generate_content(topic)

    async def get_recent_posts(
        self, 
        limit: int = 10, 
        status: Optional[str] = None
    ) -> list[dict]:
        """최근 포스트 목록 조회"""
        return await self.db_service.get_recent_jobs(limit=limit, status=status)

    async def retry_failed_job(self, job_id: str) -> dict:
        """실패한 작업 재시도"""
        job = await self.db_service.get_job(job_id)
        if not job:
            raise ValueError(f"작업을 찾을 수 없습니다: {job_id}")
        
        if job.status != "failed":
            raise ValueError("실패한 작업만 재시도할 수 있습니다")
        
        # 새 작업 ID로 재시도
        return await self.create_and_publish_post(
            topic=job.topic,
            schedule_info=ScheduleInfo(mode=ScheduleMode.DRAFT)
        )

    async def _get_or_create_categories(self, category_names: list[str]) -> list:
        """카테고리 조회 또는 생성"""
        existing_categories = await self.wp_client.get_categories()
        existing_names = {cat.name: cat for cat in existing_categories}
        
        result_categories = []
        
        for name in category_names:
            if name in existing_names:
                result_categories.append(existing_names[name])
            else:
                # 새 카테고리 생성
                new_category = await self.wp_client.create_category(
                    name=name,
                    slug=slugify(name)
                )
                result_categories.append(new_category)
        
        return result_categories

    async def _get_or_create_tags(self, tag_names: list[str]) -> list:
        """태그 조회 또는 생성"""
        existing_tags = await self.wp_client.get_tags()
        existing_names = {tag.name: tag for tag in existing_tags}
        
        result_tags = []
        
        for name in tag_names:
            if name in existing_names:
                result_tags.append(existing_names[name])
            else:
                # 새 태그 생성
                new_tag = await self.wp_client.create_tag(
                    name=name,
                    slug=slugify(name)
                )
                result_tags.append(new_tag)
        
        return result_tags

    def _get_wp_status(self, schedule_mode: ScheduleMode) -> PostStatus:
        """스케줄 모드를 WordPress 상태로 변환"""
        if schedule_mode == ScheduleMode.PUBLISH:
            return PostStatus.PUBLISH
        elif schedule_mode == ScheduleMode.SCHEDULE:
            return PostStatus.FUTURE
        else:
            return PostStatus.DRAFT