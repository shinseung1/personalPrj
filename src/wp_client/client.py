import base64
from datetime import datetime
from typing import Optional
import aiofiles
import httpx
from slugify import slugify

from src.core.config import settings
from src.core.models import WordPressPost, WordPressMedia, Category, Tag, PostStatus
from src.interfaces.wordpress_client import WordPressClientInterface


class WordPressClient(WordPressClientInterface):
    """WordPress REST API 클라이언트 구현"""

    def __init__(self, base_url: str, username: str, app_password: str):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/wp-json/wp/v2"
        self.username = username
        self.app_password = app_password
        
        # Basic Auth 헤더 생성
        credentials = f"{username}:{app_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

    async def create_post(self, post: WordPressPost) -> WordPressPost:
        """포스트 생성"""
        data = {
            "title": post.title,
            "content": post.content,
            "excerpt": post.excerpt,
            "slug": post.slug,
            "status": post.status.value,
            "categories": post.categories,
            "tags": post.tags,
        }
        
        if post.featured_media:
            data["featured_media"] = post.featured_media
            
        if post.date:
            data["date"] = post.date.isoformat()
            
        if post.meta:
            data["meta"] = post.meta

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/posts",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return WordPressPost(
                id=result["id"],
                title=result["title"]["rendered"],
                content=result["content"]["rendered"],
                excerpt=result["excerpt"]["rendered"],
                slug=result["slug"],
                status=PostStatus(result["status"]),
                date=datetime.fromisoformat(result["date"].replace("Z", "+00:00")) if result.get("date") else None,
                categories=result.get("categories", []),
                tags=result.get("tags", []),
                featured_media=result.get("featured_media"),
                meta=result.get("meta", {})
            )

    async def update_post(self, post_id: int, post: WordPressPost) -> WordPressPost:
        """포스트 업데이트"""
        data = {
            "title": post.title,
            "content": post.content,
            "excerpt": post.excerpt,
            "slug": post.slug,
            "status": post.status.value,
            "categories": post.categories,
            "tags": post.tags,
        }
        
        if post.featured_media:
            data["featured_media"] = post.featured_media
            
        if post.date:
            data["date"] = post.date.isoformat()
            
        if post.meta:
            data["meta"] = post.meta

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/posts/{post_id}",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return WordPressPost(
                id=result["id"],
                title=result["title"]["rendered"],
                content=result["content"]["rendered"],
                excerpt=result["excerpt"]["rendered"],
                slug=result["slug"],
                status=PostStatus(result["status"]),
                date=datetime.fromisoformat(result["date"].replace("Z", "+00:00")) if result.get("date") else None,
                categories=result.get("categories", []),
                tags=result.get("tags", []),
                featured_media=result.get("featured_media"),
                meta=result.get("meta", {})
            )

    async def get_post(self, post_id: int) -> Optional[WordPressPost]:
        """포스트 조회"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_base}/posts/{post_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                return WordPressPost(
                    id=result["id"],
                    title=result["title"]["rendered"],
                    content=result["content"]["rendered"],
                    excerpt=result["excerpt"]["rendered"],
                    slug=result["slug"],
                    status=PostStatus(result["status"]),
                    date=datetime.fromisoformat(result["date"].replace("Z", "+00:00")) if result.get("date") else None,
                    categories=result.get("categories", []),
                    tags=result.get("tags", []),
                    featured_media=result.get("featured_media"),
                    meta=result.get("meta", {})
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def delete_post(self, post_id: int) -> bool:
        """포스트 삭제"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.api_base}/posts/{post_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError:
                return False

    async def upload_media(self, file_path: str, title: str, alt_text: str) -> WordPressMedia:
        """미디어 업로드"""
        async with aiofiles.open(file_path, 'rb') as file:
            file_content = await file.read()
            
        filename = file_path.split('/')[-1]
        
        # multipart/form-data 헤더 (Content-Type 제거)
        upload_headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Disposition": f'attachment; filename="{filename}"'
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/media",
                headers=upload_headers,
                content=file_content
            )
            response.raise_for_status()
            result = response.json()
            
            # ALT 텍스트 업데이트
            await client.post(
                f"{self.api_base}/media/{result['id']}",
                headers=self.headers,
                json={"alt_text": alt_text, "title": title}
            )
            
            return WordPressMedia(
                id=result["id"],
                title=title,
                alt_text=alt_text,
                source_url=result["source_url"],
                mime_type=result["mime_type"]
            )

    async def get_categories(self) -> list[Category]:
        """카테고리 목록 조회"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/categories",
                headers=self.headers
            )
            response.raise_for_status()
            results = response.json()
            
            return [
                Category(
                    id=cat["id"],
                    name=cat["name"],
                    slug=cat["slug"]
                )
                for cat in results
            ]

    async def create_category(self, name: str, slug: str) -> Category:
        """카테고리 생성"""
        data = {
            "name": name,
            "slug": slug or slugify(name)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/categories",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return Category(
                id=result["id"],
                name=result["name"],
                slug=result["slug"]
            )

    async def get_tags(self) -> list[Tag]:
        """태그 목록 조회"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/tags",
                headers=self.headers
            )
            response.raise_for_status()
            results = response.json()
            
            return [
                Tag(
                    id=tag["id"],
                    name=tag["name"],
                    slug=tag["slug"]
                )
                for tag in results
            ]

    async def create_tag(self, name: str, slug: str) -> Tag:
        """태그 생성"""
        data = {
            "name": name,
            "slug": slug or slugify(name)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/tags",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return Tag(
                id=result["id"],
                name=result["name"],
                slug=result["slug"]
            )


def create_wordpress_client() -> WordPressClient:
    """WordPress 클라이언트 팩토리 함수"""
    return WordPressClient(
        base_url=settings.wordpress_url,
        username=settings.wordpress_username,
        app_password=settings.wordpress_app_password
    )