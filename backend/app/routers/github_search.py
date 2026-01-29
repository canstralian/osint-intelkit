"""
GitHub search endpoints for repository intelligence gathering.

Provides search capabilities for:
- Code snippets across repositories
- Documentation files
- Past implementations and examples
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re

from ..clients.github_client import GitHubClient
from ..config.logging import get_logger
from ..middleware.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter()

# Initialize GitHub client (will use GITHUB_TOKEN env var if available)
github_client = GitHubClient()


class CodeSearchRequest(BaseModel):
    """Request model for code search."""
    query: str = Field(..., description="Search query for code snippets", min_length=1, max_length=256)
    language: Optional[str] = Field(None, description="Programming language filter (e.g., python, javascript)")
    repo: Optional[str] = Field(None, description="Filter by repository (format: owner/repo)")
    org: Optional[str] = Field(None, description="Filter by organization")
    per_page: int = Field(default=30, description="Results per page", ge=1, le=100)
    page: int = Field(default=1, description="Page number", ge=1)

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        v = v.strip()
        
        # Security: prevent potential injection
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError('Query contains invalid characters')
        
        return v

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate programming language."""
        if v is None:
            return v
        
        v = v.lower().strip()
        
        # Allow alphanumeric and common language names
        if not re.match(r'^[a-z0-9+#\-]+$', v):
            raise ValueError('Invalid language format')
        
        return v

    @field_validator('repo')
    @classmethod
    def validate_repo(cls, v):
        """Validate repository format."""
        if v is None:
            return v
        
        v = v.strip()
        
        # Must be in format "owner/repo"
        if not re.match(r'^[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+$', v):
            raise ValueError('Repository must be in format "owner/repo"')
        
        return v

    @field_validator('org')
    @classmethod
    def validate_org(cls, v):
        """Validate organization name."""
        if v is None:
            return v
        
        v = v.strip()
        
        # Organization names should be alphanumeric with hyphens
        if not re.match(r'^[a-zA-Z0-9\-]+$', v):
            raise ValueError('Invalid organization name format')
        
        return v


class RepoSearchRequest(BaseModel):
    """Request model for repository search."""
    query: str = Field(..., description="Search query for repositories", min_length=1, max_length=256)
    language: Optional[str] = Field(None, description="Programming language filter")
    sort: str = Field(default="stars", description="Sort field: stars, forks, updated, or help-wanted-issues")
    order: str = Field(default="desc", description="Sort order: asc or desc")
    per_page: int = Field(default=30, description="Results per page", ge=1, le=100)
    page: int = Field(default=1, description="Page number", ge=1)

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate search query."""
        v = v.strip()
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError('Query contains invalid characters')
        return v

    @field_validator('sort')
    @classmethod
    def validate_sort(cls, v):
        """Validate sort field."""
        allowed_sorts = ['stars', 'forks', 'updated', 'help-wanted-issues']
        if v not in allowed_sorts:
            raise ValueError(f'Sort must be one of: {", ".join(allowed_sorts)}')
        return v

    @field_validator('order')
    @classmethod
    def validate_order(cls, v):
        """Validate sort order."""
        if v not in ['asc', 'desc']:
            raise ValueError('Order must be "asc" or "desc"')
        return v


class DocumentationSearchRequest(BaseModel):
    """Request model for documentation search."""
    query: str = Field(..., description="Search query for documentation", min_length=1, max_length=256)
    repo: Optional[str] = Field(None, description="Filter by repository (format: owner/repo)")
    org: Optional[str] = Field(None, description="Filter by organization")
    per_page: int = Field(default=30, description="Results per page", ge=1, le=100)
    page: int = Field(default=1, description="Page number", ge=1)

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate search query."""
        v = v.strip()
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError('Query contains invalid characters')
        return v


@router.get("/search/code")
@limiter.limit("30/minute")
async def search_code(
    request: Request,
    query: str = Query(..., description="Search query for code snippets"),
    language: Optional[str] = Query(None, description="Programming language filter"),
    repo: Optional[str] = Query(None, description="Repository filter (owner/repo)"),
    org: Optional[str] = Query(None, description="Organization filter"),
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    Search for code snippets across GitHub repositories.

    This endpoint allows you to search for specific code patterns, functions,
    or implementations across public GitHub repositories.

    **Rate limit:** 30 requests per minute

    **Examples:**
    - Search for authentication implementations: `?query=authentication&language=python`
    - Find FastAPI examples: `?query=fastapi router&language=python`
    - Search in specific repo: `?query=api&repo=owner/repository`

    **Returns:** List of code files matching the search criteria with repository information.
    """
    try:
        # Validate inputs using Pydantic model
        request = CodeSearchRequest(
            query=query,
            language=language,
            repo=repo,
            org=org,
            per_page=per_page,
            page=page
        )

        logger.info("github_code_search_request", 
                   query=request.query, 
                   language=request.language,
                   repo=request.repo)

        # Perform search
        results = await github_client.search_code(
            query=request.query,
            language=request.language,
            repo=request.repo,
            org=request.org,
            per_page=request.per_page,
            page=request.page
        )

        return {
            "status": "success",
            "search_type": "code",
            "query": request.query,
            "filters": {
                "language": request.language,
                "repo": request.repo,
                "org": request.org
            },
            "results": results
        }

    except ValueError as e:
        logger.warning("invalid_search_request", error=str(e), query=query)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("github_search_failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/repositories")
@limiter.limit("30/minute")
async def search_repositories(
    request: Request,
    query: str = Query(..., description="Search query for repositories"),
    language: Optional[str] = Query(None, description="Programming language filter"),
    sort: str = Query("stars", description="Sort by: stars, forks, updated, or help-wanted-issues"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    Search for repositories on GitHub.

    Find repositories with similar implementations or technologies.

    **Rate limit:** 30 requests per minute

    **Examples:**
    - Search for OSINT tools: `?query=osint&language=python&sort=stars`
    - Find FastAPI projects: `?query=fastapi&sort=stars&order=desc`

    **Returns:** List of repositories matching the search criteria.
    """
    try:
        # Validate inputs
        request = RepoSearchRequest(
            query=query,
            language=language,
            sort=sort,
            order=order,
            per_page=per_page,
            page=page
        )

        logger.info("github_repo_search_request",
                   query=request.query,
                   language=request.language,
                   sort=request.sort)

        # Perform search
        results = await github_client.search_repositories(
            query=request.query,
            language=request.language,
            sort=request.sort,
            order=request.order,
            per_page=request.per_page,
            page=request.page
        )

        return {
            "status": "success",
            "search_type": "repositories",
            "query": request.query,
            "filters": {
                "language": request.language,
                "sort": request.sort,
                "order": request.order
            },
            "results": results
        }

    except ValueError as e:
        logger.warning("invalid_search_request", error=str(e), query=query)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("github_search_failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/documentation")
@limiter.limit("30/minute")
async def search_documentation(
    request: Request,
    query: str = Query(..., description="Search query for documentation"),
    repo: Optional[str] = Query(None, description="Repository filter (owner/repo)"),
    org: Optional[str] = Query(None, description="Organization filter"),
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    Search for documentation files across GitHub repositories.

    Find documentation, README files, and guides related to your search query.
    Searches in markdown (.md), reStructuredText (.rst), and text (.txt) files.

    **Rate limit:** 30 requests per minute

    **Examples:**
    - Find API documentation: `?query=api authentication`
    - Search specific repo docs: `?query=installation&repo=owner/repository`

    **Returns:** List of documentation files matching the search criteria.
    """
    try:
        # Validate inputs
        request = DocumentationSearchRequest(
            query=query,
            repo=repo,
            org=org,
            per_page=per_page,
            page=page
        )

        logger.info("github_docs_search_request",
                   query=request.query,
                   repo=request.repo)

        # Perform search
        results = await github_client.search_documentation(
            query=request.query,
            repo=request.repo,
            org=request.org,
            per_page=request.per_page,
            page=request.page
        )

        return {
            "status": "success",
            "search_type": "documentation",
            "query": request.query,
            "filters": {
                "repo": request.repo,
                "org": request.org
            },
            "results": results
        }

    except ValueError as e:
        logger.warning("invalid_search_request", error=str(e), query=query)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("github_search_failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/similar-implementations")
@limiter.limit("30/minute")
async def search_similar_implementations(
    request: Request,
    feature: str = Query(..., description="Feature or implementation to find"),
    language: Optional[str] = Query(None, description="Programming language filter"),
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    Search for similar implementations of a feature across repositories.

    This is a convenience endpoint that combines code and repository search
    to find past implementations of similar features.

    **Rate limit:** 30 requests per minute

    **Examples:**
    - Find authentication implementations: `?feature=jwt authentication&language=python`
    - Search for rate limiting: `?feature=rate limiting fastapi`

    **Returns:** Combined results from code and repository searches.
    """
    try:
        logger.info("github_similar_impl_search",
                   feature=feature,
                   language=language)

        # Search both code and repositories
        code_results = await github_client.search_code(
            query=feature,
            language=language,
            per_page=per_page,
            page=page
        )

        repo_results = await github_client.search_repositories(
            query=feature,
            language=language,
            sort="stars",
            order="desc",
            per_page=min(per_page, 10),  # Limit repo results
            page=1
        )

        return {
            "status": "success",
            "search_type": "similar_implementations",
            "feature": feature,
            "language": language,
            "code_snippets": {
                "total_count": code_results.get("total_count", 0),
                "items": code_results.get("items", [])
            },
            "example_repositories": {
                "total_count": repo_results.get("total_count", 0),
                "items": repo_results.get("items", [])
            },
            "rate_limit_remaining": code_results.get("rate_limit_remaining")
        }

    except Exception as e:
        logger.error("github_search_failed", error=str(e), feature=feature)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
