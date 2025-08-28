# 왜 WordPress인가?

- **완전 자동화**가 공식 REST API로 안정적 지원: 글/미디어 생성, 예약, 수정 등. [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)

- **미디어 업로드**·대표이미지 설정도 표준 엔드포인트 제공. [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/media/?utm_source=chatgpt.com)

- **예약 발행**: `status=future` + `date` 로 스케줄링 가능(워드프레스 타임존 기준). [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)[DEV Community](https://dev.to/bramburn/a-comprehensive-guide-to-using-the-wordpress-api-authentication-and-post-scheduling-27me?utm_source=chatgpt.com)[Stack Overflow](https://stackoverflow.com/questions/42087015/how-to-add-a-post-via-wordpress-rest-api-with-publish-date-in-the-future?utm_source=chatgpt.com)

- (대안) **Blogger API v3**로도 완전 자동 발행 가능(구글 OAuth) — 단, 기능 유연성/확장성은 WP 대비 제한. [Google for Developers](https://developers.google.com/blogger/docs/3.0/using?utm_source=chatgpt.com)[Google Cloud](https://googleapis.dev/nodejs/googleapis/latest/Blogger.html?utm_source=chatgpt.com)

- (대안) **Ghost Admin API**도 포스트 생성·발행 가능(자체 호스팅/유료 SaaS). [docs.ghost.org+1](https://docs.ghost.org/admin-api?utm_source=chatgpt.com)

---

# 마이그레이션 큰 그림(SEO 안전 + 운영 자동화)

1. **새 플랫폼 준비**
   
   - WordPress + 필수 플러그인(SEO, 캐시, 보안) + 애플리케이션 패스워드/인증 구성.

2. **콘텐츠 이관(선택)**
   
   - 기존 글을 크롤링/추출→WP로 올림(슬러그/카테고리/태그/이미지 재매핑).

3. **리디렉션 전략**
   
   - **커스텀 도메인**을 원래부터 쓰고 있다면, 도메인만 WP로 **DNS 이전**해도 URL 유지가 가능. (경우에 따라 개별 리디렉션 불필요) [30분전](https://avada.tistory.com/2882?utm_source=chatgpt.com)
   
   - 티스토리 기본 서브도메인(`*.tistory.com`)에서 WP로 옮기는 경우엔 **규칙형 301 리디렉션**을 설계(가능한 범위에서 주소 규칙을 맞춰야 정확히 매핑). [워플:WPlaybook](https://wplaybook.com/en/how-to-redirect-a-tistory-blog-driving-traffic-to-wordpress/?utm_source=chatgpt.com)

4. **완전 자동 발행 파이프라인**
   
   - 키워드→아웃라인→초안→리라이트/SEO→이미지→품질검사→**API로 초안/예약/발행**.

5. **관측/롤백**
   
   - 실행 로그(요청/응답/프롬프트), 포스트 ID·URL, 실패 재시도/롤백 루틴.

---

# 개발 스펙 (WordPress 중심)

## 1) 인프라/런타임

- **언어**: Python 3.11+

- **배포**: Docker(개발=운영 일치), docker-compose

- **구성 요소**
  
  - `orchestrator`: 스케줄러(APScheduler), 재시도(지수 백오프), Job 큐
  
  - `wp_client`: WordPress REST API 어댑터
  
  - `generator`: 글 생성 체인(키워드→아웃라인→초안→리라이트→SEO 메타)
  
  - `media`: 이미지 생성/압축/WebP/ALT 자동 생성 → **WP 미디어 업로드**
  
  - `quality`: 맞춤법/유사도/링크체크(404)/금칙어
  
  - `publisher`: 초안/공개/예약 발행, 갱신, 비공개 저장
  
  - `storage`: SQLite (posts, runs, prompts, media_map)
  
  - `ui`: FastAPI 대시보드(미리보기/실행로그/재시도 버튼)

## 2) 인증/보안 (WP)

- **Application Passwords**(코어 지원) 또는 **JWT 인증** 중 택1.

- 비밀값은 `.env` + Pydantic Settings로 주입.

- 타임존은 WP 사이트 타임존과 일치시키기(예약 발행 시간 오차 방지). [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)

## 3) 핵심 REST 호출(예시)

- **글 생성**: `POST /wp-json/wp/v2/posts`  
  바디 주요 필드: `title`, `content`, `status`(`draft|publish|future`), `date`(예약시), `slug`, `categories`, `tags`, `excerpt` 등. [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)

- **미디어 업로드**: `POST /wp-json/wp/v2/media`  
  `Content-Disposition: attachment; filename="thumb.webp"` + 바이너리 전송 → 응답의 `id`를 `featured_media`로 연결. [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/media/?utm_source=chatgpt.com)[Stack Overflow](https://stackoverflow.com/questions/59671683/upload-media-to-wordpress-using-rest-api?utm_source=chatgpt.com)

- **예약 발행**: `status=future` + `date="2025-09-01T09:00:00"` (사이트 타임존 기준). [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)[DEV Community](https://dev.to/bramburn/a-comprehensive-guide-to-using-the-wordpress-api-authentication-and-post-scheduling-27me?utm_source=chatgpt.com)

> 참고 튜토리얼: REST로 포스트 생성/인증 예제들. [Misha Rudrastyh](https://rudrastyh.com/wordpress/rest-api-create-post.html?utm_source=chatgpt.com)[Ashvani Kumar](https://ashvanikumar.com/create-a-post-with-wordpress-rest-api/?utm_source=chatgpt.com)

## 4) 데이터 모델(JSON 스키마 요약)

{
"topic": "키워드/주제",
  "outline": ["H2/H3 구조..."],
  "content_html": "<h1>...</h1> ...",
  "excerpt": "요약(SEO 메타 설명)",
  "slug": "seo-friendly-slug",
  "categories": ["카테고리1", "카테고리2"],
  "tags": ["태그1","태그2"],
  "images": [
    {"path": "images/hero.webp", "alt": "설명", "use_as_featured": true}
  ],
  "schedule": {"mode": "publish|draft|schedule", "datetime": "YYYY-MM-DDTHH:mm:ss"}
}

## 5) 파이프라인 단계(완전 자동)

1. **키워드 인풋**(주제/톤/금칙어)

2. **리서치 요약**(출처 보관)

3. **아웃라인 생성** → **초안** → **리라이트/SEO 메타**

4. **이미지 생성/선정**(ALT 자동, 용량 최적화 후 WebP)

5. **품질검사**(맞춤법·유사도·링크 404·워드카운트·헤딩 규칙)

6. **WP 미디어 업로드** → 첨부 ID 수집

7. **포스트 생성**(슬러그/카테고리/태그/대표이미지/요약)

8. **예약/발행**(status/date)

9. **로그 저장**(요청/응답/실패 스냅샷/리플레이 토큰)

## 6) 테스트/디버깅

- **계약 테스트**: `wp_client`(posts/media) 모듈에 대해 VCR.py로 HTTP 캡쳐·재현.

- **E2E 시나리오**: “키워드→예약 발행” 한줄 파이프라인.

- **리그레션 방지**: 프롬프트/산출물 JSON 비교(diff), 클린 룸 실행.

- **관측**: 구조화 로그(JSON), 실패 시 스냅샷(`runs/{ts}.jsonl`).

## 7) 대시보드(FastAPI)

- **큐 상태/실행 로그**/예약 목록, **미리보기**(Jinja2 렌더), **재시도/취소** 버튼.

- **슬롯/레이트 제한**: 하루 N건, 시간대 분산(자연스러움).

---

# 티스토리 → WordPress 이전(선택) 스펙

## URL/SEO 전략

- **2차 도메인(개인지정)**를 이미 쓰고 있었다면, **DNS만 변경**해도 주소 유지 가능(리디렉션 불요). [30분전](https://avada.tistory.com/2882?utm_source=chatgpt.com)

- `*.tistory.com`에서 이전하는 경우:
  
  - 가능한 한 **같은 슬러그 규칙**으로 WP 퍼머링크 설계 → 규칙형 301 맵핑(Cloudflare/NGINX/워프 플러그인). [워플:WPlaybook](https://wplaybook.com/en/how-to-redirect-a-tistory-blog-driving-traffic-to-wordpress/?utm_source=chatgpt.com)
  
  - 주소 패턴이 달라지는 경우엔 개별 맵 테이블(csv)로 301 설정.

## 콘텐트/미디어 이관

- 수집기(crawler)로 본문/이미지/카테고리/태그/작성일 추출 → 변환 → WP API 업로드.

- 이미지 원본은 **WP 미디어**로 이관(경로 치환). [WordPress Developer Resources](https://developer.wordpress.org/rest-api/reference/media/?utm_source=chatgpt.com)

---

# 프로젝트 구조(제안)

auto-writer-wp/
  apps/
    cli/                # draft, schedule, publish, replay
    api/                # FastAPI 대시보드
  packages/
    core/               # 파이프라인/스케줄/재시도/로깅
    wp_client/          # posts/media/categories/tags REST 어댑터
    gen/                # 키워드→아웃라인→초안→리라이트→SEO
    media/              # 이미지 생성/압축/WebP/ALT
    quality/            # 맞춤법/유사도/링크체크
    migrator/           # (옵션) 티스토리→WP 이관기
  prompts/
  tests/
  runs/
  pyproject.toml
  docker-compose.yml
  .env.example

---

# 구현 우선순위(MVP → 확장)

**MVP(1~2일)**

- `wp_client`: `/wp-json/wp/v2/posts`, `/media` 최소 구현(인증/에러랩핑). [WordPress Developer Resources+1](https://developer.wordpress.org/rest-api/reference/posts/?utm_source=chatgpt.com)

- `draft→schedule` 한줄 파이프라인(대표이미지 1장 업로드 + `status=future`). [DEV Community](https://dev.to/bramburn/a-comprehensive-guide-to-using-the-wordpress-api-authentication-and-post-scheduling-27me?utm_source=chatgpt.com)

- CLI: `post:schedule --topic ... --datetime ...`

- 대시보드: 최근 20건 로그/미리보기

**확장(1~2주)**

- 카테고리/태그 동기화, 내부링크 자동 삽입

- 품질검사(금칙어·유사도·맞춤법) + 점수화

- 이관기(옵션): 티스토리 → WP 마이그레이션/301 매핑 도구

- 다계정/다블로그 멀티 테넌시

---

# 선택지가 WordPress가 아니라면?

- **Blogger**: `posts.insert`로 글/예약 발행 가능, OAuth2 필요(쿼터/기능 제한 고려). [Google for Developers](https://developers.google.com/blogger/docs/3.0/using?utm_source=chatgpt.com)

- **Ghost**: Admin API로 포스트 생성/발행, 토큰 인증. SaaS(ghost.org) 또는 자체 호스팅. [docs.ghost.org+1](https://docs.ghost.org/admin-api?utm_source=chatgpt.com)
