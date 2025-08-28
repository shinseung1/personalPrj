from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # WordPress 설정
    wordpress_url: str = Field(..., description="WordPress 사이트 URL")
    wordpress_username: str = Field(..., description="WordPress 사용자명")
    wordpress_app_password: str = Field(..., description="WordPress 애플리케이션 패스워드")
    wordpress_timezone: str = Field(default="Asia/Seoul", description="WordPress 타임존")
    
    # OpenAI API 설정
    openai_api_key: str = Field(..., description="OpenAI API 키")
    openai_model: str = Field(default="gpt-4", description="사용할 OpenAI 모델")
    
    # 이미지 생성 설정
    image_generator: str = Field(default="openai", description="이미지 생성기")
    stability_api_key: str | None = Field(default=None, description="Stability API 키")
    
    # 데이터베이스 설정
    database_url: str = Field(default="sqlite:///./data/blog_automation.db", description="데이터베이스 URL")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    log_file: str = Field(default="./logs/app.log", description="로그 파일 경로")
    
    # 콘텐츠 생성 설정
    max_posts_per_day: int = Field(default=5, description="하루 최대 포스트 수")
    content_language: str = Field(default="ko", description="콘텐츠 언어")
    default_category: str = Field(default="AI", description="기본 카테고리")
    default_tags: str = Field(default="AI,자동화,블로그", description="기본 태그")
    
    # 품질 검사 설정
    min_word_count: int = Field(default=500, description="최소 단어 수")
    max_word_count: int = Field(default=3000, description="최대 단어 수")
    plagiarism_check_enabled: bool = Field(default=True, description="표절 검사 활성화")
    grammar_check_enabled: bool = Field(default=True, description="문법 검사 활성화")
    
    # 스케줄링 설정
    scheduler_timezone: str = Field(default="Asia/Seoul", description="스케줄러 타임존")
    post_schedule_hours: str = Field(default="09,14,19", description="게시 시간대")
    
    @property
    def schedule_hours_list(self) -> list[int]:
        """스케줄 시간을 리스트로 반환"""
        return [int(hour.strip()) for hour in self.post_schedule_hours.split(",")]
    
    @property
    def default_tags_list(self) -> list[str]:
        """기본 태그를 리스트로 반환"""
        return [tag.strip() for tag in self.default_tags.split(",")]


settings = Settings()