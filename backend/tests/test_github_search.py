"""Tests for GitHub search functionality."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.clients.github_client import GitHubClient
from app.routers.github_search import (
    CodeSearchRequest,
    RepoSearchRequest,
    DocumentationSearchRequest
)


class TestGitHubClient:
    """Test GitHub API client."""

    def test_client_initialization_with_token(self):
        """Test client initialization with token."""
        client = GitHubClient(token="test_token")
        assert client.token == "test_token"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "token test_token"

    def test_client_initialization_without_token(self):
        """Test client initialization without token."""
        with patch.dict('os.environ', {}, clear=True):
            client = GitHubClient()
            assert client.token is None
            assert "Authorization" not in client.headers

    @pytest.mark.asyncio
    async def test_search_code_success(self):
        """Test successful code search."""
        client = GitHubClient(token="test_token")
        
        mock_response = {
            "total_count": 10,
            "incomplete_results": False,
            "items": [
                {
                    "name": "test.py",
                    "path": "src/test.py",
                    "html_url": "https://github.com/owner/repo/blob/main/src/test.py",
                    "repository": {
                        "full_name": "owner/repo",
                        "html_url": "https://github.com/owner/repo",
                        "description": "Test repo",
                        "stargazers_count": 100
                    },
                    "score": 1.0
                }
            ]
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.status = 200
            mock_context.__aenter__.return_value.headers = {
                "X-RateLimit-Remaining": "60",
                "X-RateLimit-Reset": "1234567890"
            }
            mock_context.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_context.__aenter__.return_value.raise_for_status = MagicMock()
            mock_get.return_value = mock_context

            result = await client.search_code("test query", language="python")

            assert result["total_count"] == 10
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "test.py"
            assert result["rate_limit_remaining"] == "60"

    @pytest.mark.asyncio
    async def test_search_code_rate_limit(self):
        """Test code search rate limit handling."""
        client = GitHubClient(token="test_token")

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.status = 403
            mock_context.__aenter__.return_value.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890"
            }
            mock_get.return_value = mock_context

            with pytest.raises(Exception):  # Will be wrapped in RetryError
                await client.search_code("test query")

    @pytest.mark.asyncio
    async def test_search_repositories_success(self):
        """Test successful repository search."""
        client = GitHubClient(token="test_token")
        
        mock_response = {
            "total_count": 5,
            "incomplete_results": False,
            "items": [
                {
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "description": "Test repository",
                    "language": "Python",
                    "stargazers_count": 200,
                    "forks_count": 50,
                    "updated_at": "2024-01-01T00:00:00Z",
                    "topics": ["osint", "security"],
                    "score": 1.0
                }
            ]
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.status = 200
            mock_context.__aenter__.return_value.headers = {
                "X-RateLimit-Remaining": "60",
                "X-RateLimit-Reset": "1234567890"
            }
            mock_context.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_context.__aenter__.return_value.raise_for_status = MagicMock()
            mock_get.return_value = mock_context

            result = await client.search_repositories("osint", language="python")

            assert result["total_count"] == 5
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "owner/repo"
            assert result["items"][0]["language"] == "Python"

    @pytest.mark.asyncio
    async def test_search_documentation(self):
        """Test documentation search."""
        client = GitHubClient(token="test_token")
        
        with patch.object(client, 'search_code', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"total_count": 3, "items": []}
            
            await client.search_documentation("api docs", repo="owner/repo")
            
            # Verify that search_code was called with documentation extensions
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert "extension:md OR extension:rst OR extension:txt" in call_args.kwargs['query']


class TestSearchRequestModels:
    """Test Pydantic models for search requests."""

    def test_code_search_request_valid(self):
        """Test valid code search request."""
        request = CodeSearchRequest(
            query="fastapi authentication",
            language="python",
            per_page=50,
            page=1
        )
        assert request.query == "fastapi authentication"
        assert request.language == "python"
        assert request.per_page == 50

    def test_code_search_request_invalid_query(self):
        """Test code search request with invalid characters."""
        with pytest.raises(ValueError, match="invalid characters"):
            CodeSearchRequest(query='test<script>')

    def test_code_search_request_invalid_language(self):
        """Test code search request with invalid language format."""
        with pytest.raises(ValueError, match="Invalid language format"):
            CodeSearchRequest(query="test", language="python; DROP TABLE")

    def test_code_search_request_invalid_repo(self):
        """Test code search request with invalid repo format."""
        with pytest.raises(ValueError, match='format "owner/repo"'):
            CodeSearchRequest(query="test", repo="invalid_repo_format")

    def test_repo_search_request_valid(self):
        """Test valid repository search request."""
        request = RepoSearchRequest(
            query="osint tools",
            language="python",
            sort="stars",
            order="desc"
        )
        assert request.query == "osint tools"
        assert request.sort == "stars"
        assert request.order == "desc"

    def test_repo_search_request_invalid_sort(self):
        """Test repository search request with invalid sort field."""
        with pytest.raises(ValueError, match="Sort must be one of"):
            RepoSearchRequest(query="test", sort="invalid")

    def test_repo_search_request_invalid_order(self):
        """Test repository search request with invalid order."""
        with pytest.raises(ValueError, match='Order must be "asc" or "desc"'):
            RepoSearchRequest(query="test", order="invalid")

    def test_documentation_search_request_valid(self):
        """Test valid documentation search request."""
        request = DocumentationSearchRequest(
            query="installation guide",
            repo="owner/repo",
            per_page=20
        )
        assert request.query == "installation guide"
        assert request.repo == "owner/repo"
        assert request.per_page == 20


@pytest.mark.asyncio
class TestGitHubSearchEndpoints:
    """Test GitHub search router endpoints."""
    async def test_format_code_results(self):
        """Test formatting of code search results."""
        client = GitHubClient()
        
        items = [
            {
                "name": "test.py",
                "path": "src/test.py",
                "html_url": "https://github.com/owner/repo/blob/main/test.py",
                "repository": {
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "description": "Test",
                    "stargazers_count": 50
                },
                "score": 1.0
            }
        ]
        
        formatted = client._format_code_results(items)
        
        assert len(formatted) == 1
        assert formatted[0]["name"] == "test.py"
        assert formatted[0]["repository"]["name"] == "owner/repo"
        assert formatted[0]["repository"]["stars"] == 50

    @pytest.mark.asyncio
    async def test_format_repo_results(self):
        """Test formatting of repository search results."""
        client = GitHubClient()
        
        items = [
            {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "description": "Test repo",
                "language": "Python",
                "stargazers_count": 100,
                "forks_count": 25,
                "updated_at": "2024-01-01T00:00:00Z",
                "topics": ["test"],
                "score": 1.0
            }
        ]
        
        formatted = client._format_repo_results(items)
        
        assert len(formatted) == 1
        assert formatted[0]["name"] == "owner/repo"
        assert formatted[0]["stars"] == 100
        assert formatted[0]["forks"] == 25
        assert formatted[0]["language"] == "Python"
