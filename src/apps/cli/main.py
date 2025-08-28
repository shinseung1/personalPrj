import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from src.core.config import settings
from src.core.models import ScheduleInfo, ScheduleMode, PostStatus
from src.services.blog_service import BlogService

app = typer.Typer(help="WordPress 자동 블로그 포스팅 시스템")
console = Console()


@app.command("create")
def create_post(
    topic: str = typer.Argument(..., help="블로그 포스트 주제"),
    schedule: Optional[str] = typer.Option(None, "--schedule", "-s", help="예약 시간 (YYYY-MM-DD HH:MM)"),
    categories: Optional[str] = typer.Option(None, "--categories", "-c", help="카테고리 (쉼표로 구분)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="태그 (쉼표로 구분)"),
    draft: bool = typer.Option(False, "--draft", "-d", help="임시글로 저장"),
    publish: bool = typer.Option(False, "--publish", "-p", help="즉시 발행"),
):
    """새 블로그 포스트 생성"""
    asyncio.run(_create_post_async(topic, schedule, categories, tags, draft, publish))


async def _create_post_async(
    topic: str,
    schedule: Optional[str],
    categories: Optional[str],
    tags: Optional[str],
    draft: bool,
    publish: bool
):
    """비동기 포스트 생성"""
    console.print(f"[bold blue]주제:[/bold blue] {topic}")
    
    # 스케줄 정보 파싱
    schedule_info = _parse_schedule_info(schedule, draft, publish)
    
    # 카테고리, 태그 파싱
    category_list = categories.split(',') if categories else None
    tag_list = tags.split(',') if tags else None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("포스트 생성 중...", total=None)
        
        try:
            blog_service = BlogService()
            
            progress.update(task, description="콘텐츠 생성 중...")
            result = await blog_service.create_and_publish_post(
                topic=topic,
                schedule_info=schedule_info,
                categories=category_list,
                tags=tag_list
            )
            
            progress.update(task, description="완료!")
            
            # 결과 출력
            _display_creation_result(result)
            
        except Exception as e:
            console.print(f"[red]오류 발생:[/red] {e}")


def _parse_schedule_info(
    schedule: Optional[str],
    draft: bool,
    publish: bool
) -> ScheduleInfo:
    """스케줄 정보 파싱"""
    if draft:
        return ScheduleInfo(mode=ScheduleMode.DRAFT)
    elif publish:
        return ScheduleInfo(mode=ScheduleMode.PUBLISH)
    elif schedule:
        try:
            dt = datetime.strptime(schedule, "%Y-%m-%d %H:%M")
            return ScheduleInfo(mode=ScheduleMode.SCHEDULE, datetime=dt)
        except ValueError:
            console.print("[red]잘못된 날짜 형식입니다. YYYY-MM-DD HH:MM 형식을 사용하세요.[/red]")
            raise typer.Exit(1)
    else:
        return ScheduleInfo(mode=ScheduleMode.DRAFT)


def _display_creation_result(result: dict):
    """생성 결과 출력"""
    panel = Panel.fit(
        f"""[green]✅ 포스트 생성 완료![/green]

[bold]WordPress ID:[/bold] {result.get('wp_post_id', 'N/A')}
[bold]제목:[/bold] {result.get('title', 'N/A')}
[bold]상태:[/bold] {result.get('status', 'N/A')}
[bold]URL:[/bold] {result.get('url', 'N/A')}
[bold]품질 점수:[/bold] {result.get('quality_score', 'N/A')}/100
        """,
        title="생성 결과",
        border_style="green"
    )
    console.print(panel)


@app.command("list")
def list_posts(
    limit: int = typer.Option(10, "--limit", "-l", help="표시할 포스트 수"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="필터링할 상태")
):
    """포스트 목록 조회"""
    asyncio.run(_list_posts_async(limit, status))


async def _list_posts_async(limit: int, status: Optional[str]):
    """비동기 포스트 목록 조회"""
    try:
        blog_service = BlogService()
        posts = await blog_service.get_recent_posts(limit=limit, status=status)
        
        if not posts:
            console.print("[yellow]포스트가 없습니다.[/yellow]")
            return
        
        table = Table(title="최근 포스트")
        table.add_column("ID", style="cyan")
        table.add_column("제목", style="white")
        table.add_column("상태", style="green")
        table.add_column("생성일", style="blue")
        table.add_column("품질점수", style="magenta")
        
        for post in posts:
            table.add_row(
                str(post.get('id', 'N/A')),
                post.get('title', 'N/A')[:50] + "..." if len(post.get('title', '')) > 50 else post.get('title', 'N/A'),
                post.get('status', 'N/A'),
                post.get('created_at', 'N/A'),
                f"{post.get('quality_score', 'N/A')}/100"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]오류 발생:[/red] {e}")


@app.command("preview")
def preview_post(
    topic: str = typer.Argument(..., help="미리보기할 주제")
):
    """포스트 미리보기 생성"""
    asyncio.run(_preview_post_async(topic))


async def _preview_post_async(topic: str):
    """비동기 포스트 미리보기"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("미리보기 생성 중...", total=None)
        
        try:
            blog_service = BlogService()
            
            progress.update(task, description="콘텐츠 생성 중...")
            content = await blog_service.generate_content_only(topic)
            
            progress.update(task, description="완료!")
            
            # 미리보기 출력
            console.print(Panel.fit(
                f"""[bold blue]주제:[/bold blue] {content.topic}

[bold green]개요:[/bold green]
{chr(10).join(['• ' + outline for outline in content.outline])}

[bold yellow]요약:[/bold yellow]
{content.excerpt}

[bold magenta]슬러그:[/bold magenta] {content.slug}
[bold cyan]카테고리:[/bold cyan] {', '.join(content.categories)}
[bold red]태그:[/bold red] {', '.join(content.tags)}
                """,
                title="포스트 미리보기",
                border_style="blue"
            ))
            
        except Exception as e:
            console.print(f"[red]오류 발생:[/red] {e}")


@app.command("config")
def show_config():
    """현재 설정 표시"""
    console.print(Panel.fit(
        f"""[bold]WordPress 설정[/bold]
URL: {settings.wordpress_url}
사용자명: {settings.wordpress_username}
타임존: {settings.wordpress_timezone}

[bold]콘텐츠 설정[/bold]
하루 최대 포스트: {settings.max_posts_per_day}
언어: {settings.content_language}
기본 카테고리: {settings.default_category}
기본 태그: {settings.default_tags}

[bold]품질 검사[/bold]
최소 단어수: {settings.min_word_count}
최대 단어수: {settings.max_word_count}
표절 검사: {"활성화" if settings.plagiarism_check_enabled else "비활성화"}
문법 검사: {"활성화" if settings.grammar_check_enabled else "비활성화"}
        """,
        title="현재 설정",
        border_style="green"
    ))


@app.command("setup")
def setup():
    """초기 설정"""
    console.print("[bold blue]WordPress 자동 블로그 시스템 초기 설정[/bold blue]")
    
    # .env 파일 존재 확인
    env_file = Path(".env")
    if not env_file.exists():
        console.print("[yellow].env 파일이 없습니다. .env.example을 복사하여 설정을 완료하세요.[/yellow]")
        
        # .env.example 복사
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(".env.example", ".env")
            console.print("[green].env 파일이 생성되었습니다. 설정을 편집하세요.[/green]")
    
    # 필요한 디렉토리 생성
    directories = ["data", "logs", "images", "runs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    console.print("[green]초기 설정이 완료되었습니다![/green]")


if __name__ == "__main__":
    app()