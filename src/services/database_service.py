import json
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.config import settings
from src.core.models import GenerationJob, PostContent


class DatabaseService:
    """데이터베이스 서비스 (Repository Pattern)"""
    
    def __init__(self):
        self.db_path = self._get_db_path()
        
    def _get_db_path(self) -> str:
        """데이터베이스 경로 생성"""
        if settings.database_url.startswith("sqlite:///"):
            path = settings.database_url.replace("sqlite:///", "")
            # 상대 경로를 절대 경로로 변환
            if not Path(path).is_absolute():
                path = Path.cwd() / path
            
            # 디렉토리 생성
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            return str(path)
        else:
            raise ValueError("현재 SQLite만 지원됩니다")

    async def init_database(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS generation_jobs (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    scheduled_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    wp_post_id INTEGER,
                    error_message TEXT,
                    content_json TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    wp_post_id INTEGER,
                    title TEXT,
                    slug TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    quality_score REAL,
                    job_id TEXT,
                    FOREIGN KEY (job_id) REFERENCES generation_jobs (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS prompts_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    prompt_type TEXT,
                    prompt_text TEXT,
                    response_text TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES generation_jobs (id)
                )
            """)
            
            await db.commit()

    async def save_job(self, job: GenerationJob):
        """작업 저장"""
        await self.init_database()
        
        async with aiosqlite.connect(self.db_path) as db:
            content_json = None
            if job.content:
                content_json = job.content.model_dump_json()
            
            await db.execute("""
                INSERT OR REPLACE INTO generation_jobs 
                (id, topic, status, created_at, scheduled_at, completed_at, wp_post_id, error_message, content_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.topic,
                job.status,
                job.created_at,
                job.scheduled_at,
                job.completed_at,
                job.wp_post_id,
                job.error_message,
                content_json
            ))
            
            await db.commit()

    async def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """작업 조회"""
        await self.init_database()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM generation_jobs WHERE id = ?
            """, (job_id,)) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                content = None
                if row[8]:  # content_json
                    content_dict = json.loads(row[8])
                    content = PostContent(**content_dict)
                
                return GenerationJob(
                    id=row[0],
                    topic=row[1],
                    status=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    scheduled_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    wp_post_id=row[6],
                    error_message=row[7],
                    content=content
                )

    async def get_recent_jobs(
        self, 
        limit: int = 10, 
        status: Optional[str] = None
    ) -> list[dict]:
        """최근 작업 목록 조회"""
        await self.init_database()
        
        query = """
            SELECT id, topic, status, created_at, completed_at, wp_post_id, error_message
            FROM generation_jobs
        """
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        "id": row[0],
                        "title": row[1],  # topic을 title로 사용
                        "status": row[2],
                        "created_at": row[3],
                        "completed_at": row[4],
                        "wp_post_id": row[5],
                        "error_message": row[6],
                        "quality_score": "N/A"  # 품질 점수는 별도 계산 필요
                    })
                
                return results

    async def save_prompt_log(
        self,
        job_id: str,
        prompt_type: str,
        prompt_text: str,
        response_text: str
    ):
        """프롬프트 로그 저장"""
        await self.init_database()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO prompts_log (job_id, prompt_type, prompt_text, response_text, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                prompt_type,
                prompt_text,
                response_text,
                datetime.now()
            ))
            
            await db.commit()

    async def get_prompt_logs(self, job_id: str) -> list[dict]:
        """프롬프트 로그 조회"""
        await self.init_database()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT prompt_type, prompt_text, response_text, created_at
                FROM prompts_log
                WHERE job_id = ?
                ORDER BY created_at
            """, (job_id,)) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "prompt_type": row[0],
                        "prompt_text": row[1],
                        "response_text": row[2],
                        "created_at": row[3]
                    }
                    for row in rows
                ]

    async def get_statistics(self) -> dict:
        """통계 정보 조회"""
        await self.init_database()
        
        async with aiosqlite.connect(self.db_path) as db:
            # 총 작업 수
            async with db.execute("SELECT COUNT(*) FROM generation_jobs") as cursor:
                total_jobs = (await cursor.fetchone())[0]
            
            # 성공/실패 작업 수
            async with db.execute("SELECT status, COUNT(*) FROM generation_jobs GROUP BY status") as cursor:
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # 오늘 생성된 작업 수
            today = datetime.now().date()
            async with db.execute(
                "SELECT COUNT(*) FROM generation_jobs WHERE date(created_at) = ?",
                (today,)
            ) as cursor:
                today_jobs = (await cursor.fetchone())[0]
            
            return {
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "today_jobs": today_jobs,
                "success_rate": status_counts.get("completed", 0) / total_jobs * 100 if total_jobs > 0 else 0
            }