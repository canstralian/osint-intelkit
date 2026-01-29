"""
GitHub API client for repository search capabilities.

Provides search functionality for:
- Code snippets across repositories
- Documentation files
- Past implementations
"""
import os
import aiohttp
from typing import Dict, List, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from ..config.logging import get_logger

logger = get_logger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_SEARCH_CODE_URL = f"{GITHUB_API_BASE_URL}/search/code"
GITHUB_SEARCH_REPOS_URL = f"{GITHUB_API_BASE_URL}/search/repositories"


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client.

        Args:
            token: GitHub personal access token (optional, but recommended for higher rate limits)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OSINT-IntelKit/1.0"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            logger.info("github_client_initialized", authenticated=True)
        else:
            logger.warning("github_client_initialized", authenticated=False,
                         message="No GitHub token provided. Rate limits will be lower.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        repo: Optional[str] = None,
        org: Optional[str] = None,
        per_page: int = 30,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for code snippets across GitHub repositories.

        Args:
            query: Search query string
            language: Filter by programming language (e.g., "python", "javascript")
            repo: Filter by specific repository (format: "owner/repo")
            org: Filter by organization
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            Dictionary containing search results and metadata

        Example:
            >>> client = GitHubClient()
            >>> results = await client.search_code("fastapi authentication", language="python")
        """
        # Build search query with filters
        search_query = query
        if language:
            search_query += f" language:{language}"
        if repo:
            search_query += f" repo:{repo}"
        if org:
            search_query += f" org:{org}"

        params = {
            "q": search_query,
            "per_page": min(per_page, 100),  # GitHub max is 100
            "page": page
        }

        logger.info("github_code_search", query=search_query, per_page=per_page, page=page)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    GITHUB_SEARCH_CODE_URL,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    # Check rate limiting
                    rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                    rate_limit_reset = response.headers.get("X-RateLimit-Reset")

                    if rate_limit_remaining:
                        logger.debug("github_rate_limit",
                                   remaining=rate_limit_remaining,
                                   reset=rate_limit_reset)

                    if response.status == 403:
                        logger.error("github_rate_limit_exceeded",
                                   reset_time=rate_limit_reset)
                        raise Exception("GitHub API rate limit exceeded")

                    response.raise_for_status()
                    data = await response.json()

                    logger.info("github_code_search_success",
                              total_count=data.get("total_count", 0),
                              items_returned=len(data.get("items", [])))

                    return {
                        "total_count": data.get("total_count", 0),
                        "incomplete_results": data.get("incomplete_results", False),
                        "items": self._format_code_results(data.get("items", [])),
                        "rate_limit_remaining": rate_limit_remaining,
                        "rate_limit_reset": rate_limit_reset
                    }

        except aiohttp.ClientError as e:
            logger.error("github_code_search_failed", error=str(e), query=search_query)
            raise Exception(f"GitHub API request failed: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_repositories(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for repositories on GitHub.

        Args:
            query: Search query string
            language: Filter by programming language
            sort: Sort by "stars", "forks", "updated", or "help-wanted-issues"
            order: Sort order "asc" or "desc"
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            Dictionary containing search results and metadata
        """
        search_query = query
        if language:
            search_query += f" language:{language}"

        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page
        }

        logger.info("github_repo_search", query=search_query, sort=sort, per_page=per_page)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    GITHUB_SEARCH_REPOS_URL,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                    rate_limit_reset = response.headers.get("X-RateLimit-Reset")

                    if response.status == 403:
                        logger.error("github_rate_limit_exceeded", reset_time=rate_limit_reset)
                        raise Exception("GitHub API rate limit exceeded")

                    response.raise_for_status()
                    data = await response.json()

                    logger.info("github_repo_search_success",
                              total_count=data.get("total_count", 0),
                              items_returned=len(data.get("items", [])))

                    return {
                        "total_count": data.get("total_count", 0),
                        "incomplete_results": data.get("incomplete_results", False),
                        "items": self._format_repo_results(data.get("items", [])),
                        "rate_limit_remaining": rate_limit_remaining,
                        "rate_limit_reset": rate_limit_reset
                    }

        except aiohttp.ClientError as e:
            logger.error("github_repo_search_failed", error=str(e), query=search_query)
            raise Exception(f"GitHub API request failed: {str(e)}")

    async def search_documentation(
        self,
        query: str,
        repo: Optional[str] = None,
        org: Optional[str] = None,
        per_page: int = 30,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for documentation files (markdown, rst, etc.).

        Args:
            query: Search query string
            repo: Filter by specific repository
            org: Filter by organization
            per_page: Results per page
            page: Page number

        Returns:
            Dictionary containing search results
        """
        # Add file extension filters for documentation
        doc_query = f"{query} extension:md OR extension:rst OR extension:txt"
        
        return await self.search_code(
            query=doc_query,
            repo=repo,
            org=org,
            per_page=per_page,
            page=page
        )

    def _format_code_results(self, items: List[Dict]) -> List[Dict]:
        """Format code search results for consistent response."""
        formatted = []
        for item in items:
            formatted.append({
                "name": item.get("name"),
                "path": item.get("path"),
                "url": item.get("html_url"),
                "repository": {
                    "name": item.get("repository", {}).get("full_name"),
                    "url": item.get("repository", {}).get("html_url"),
                    "description": item.get("repository", {}).get("description"),
                    "stars": item.get("repository", {}).get("stargazers_count", 0),
                },
                "score": item.get("score", 0)
            })
        return formatted

    def _format_repo_results(self, items: List[Dict]) -> List[Dict]:
        """Format repository search results for consistent response."""
        formatted = []
        for item in items:
            formatted.append({
                "name": item.get("full_name"),
                "url": item.get("html_url"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "updated_at": item.get("updated_at"),
                "topics": item.get("topics", []),
                "score": item.get("score", 0)
            })
        return formatted
