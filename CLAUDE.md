# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated WordPress content creation and publishing system written in Python. The system generates blog posts from keywords, handles SEO optimization, image generation, and publishes content via WordPress REST API with scheduling capabilities.

## Planned Architecture

The system is designed with a microservices-like architecture using the following components:

- `orchestrator/`: Job scheduler using APScheduler with exponential backoff retry logic
- `wp_client/`: WordPress REST API adapter for posts, media, categories, and tags
- `generator/`: Content generation pipeline (keyword → outline → draft → rewrite → SEO)
- `media/`: Image generation, compression, WebP conversion, and automatic ALT text
- `quality/`: Content quality checks (spell check, similarity, link validation, prohibited words)
- `publisher/`: Draft/publish/scheduled publishing with WordPress API
- `storage/`: SQLite database for posts, runs, prompts, and media mapping
- `ui/`: FastAPI dashboard for preview, logs, and manual controls
- `migrator/`: Optional Tistory → WordPress migration tools

## Development Commands

Since this project is in early planning phase, these commands are based on the planned Python structure:

```bash
# Install dependencies (when pyproject.toml exists)
pip install -e .

# Run tests (planned structure)
python -m pytest tests/

# Run the CLI (planned)
python -m apps.cli post:schedule --topic "topic" --datetime "2025-01-01T09:00:00"

# Start the dashboard (planned)
python -m apps.api

# Run linting (when implemented)
black .
ruff check .

# Type checking (when implemented)
mypy .
```

## WordPress Integration

The system integrates with WordPress via REST API:

- **Authentication**: Application Passwords or JWT authentication
- **Posts**: `/wp-json/wp/v2/posts` for CRUD operations
- **Media**: `/wp-json/wp/v2/media` for image uploads
- **Scheduling**: Uses `status=future` with `date` parameter for scheduled publishing
- **Categories/Tags**: Automatic synchronization and assignment

## Key Configuration

- WordPress site timezone alignment for accurate scheduling
- Environment variables for API credentials via `.env` file
- Pydantic Settings for configuration management
- Rate limiting and daily post quotas

## Content Pipeline

The automated content generation follows this flow:

1. Keyword input (topic/tone/restrictions)
2. Research and source gathering
3. Outline generation → Draft → Rewrite/SEO optimization
4. Image generation/selection with automatic ALT text
5. Quality checks (spell check, similarity, link validation)
6. WordPress media upload and ID collection
7. Post creation with metadata (slug/categories/tags/featured image)
8. Scheduled or immediate publishing
9. Structured logging with failure snapshots

## Data Models

Posts use this JSON structure:
```json
{
  "topic": "keyword/topic",
  "outline": ["H2/H3 structure..."],
  "content_html": "<h1>...</h1>...",
  "excerpt": "SEO meta description",
  "slug": "seo-friendly-slug",
  "categories": ["category1", "category2"],
  "tags": ["tag1", "tag2"],
  "images": [
    {"path": "images/hero.webp", "alt": "description", "use_as_featured": true}
  ],
  "schedule": {"mode": "publish|draft|schedule", "datetime": "YYYY-MM-DDTHH:mm:ss"}
}
```

## Testing Strategy

- Contract testing for `wp_client` modules using VCR.py for HTTP capture/replay
- End-to-end scenarios covering "keyword → scheduled publish" pipeline
- Regression prevention through prompt/output JSON comparison
- Structured logging with failure snapshots in `runs/{timestamp}.jsonl`

## Migration Features

Optional Tistory → WordPress migration capabilities:
- URL/SEO preservation strategies for custom domains
- 301 redirect mapping for different URL patterns
- Content and media migration via crawler → WordPress API upload
- Image path rewriting for WordPress media library

## Implementation Priority

**MVP Phase (1-2 days)**:
- Basic wp_client for posts and media endpoints
- Simple draft→schedule pipeline with featured image upload
- CLI interface for scheduling posts
- Basic dashboard for logs and preview

**Expansion Phase (1-2 weeks)**:
- Category/tag synchronization
- Quality assurance pipeline
- Migration tools for Tistory
- Multi-account/multi-blog support