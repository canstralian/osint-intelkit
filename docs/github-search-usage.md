# GitHub Search Feature - Usage Examples

This document provides practical examples of using the GitHub repository search feature in OSINT IntelKit.

## Quick Start

The GitHub search feature allows you to search across public GitHub repositories for code snippets, documentation, and past implementations.

### Prerequisites

1. (Optional) Generate a GitHub Personal Access Token for higher rate limits:
   - Visit https://github.com/settings/tokens
   - Generate a new token with `public_repo` scope
   - Add to `.env`: `GITHUB_TOKEN=your_token_here`

**Rate Limits:**
- Without token: 10 requests/minute
- With token: 30 requests/minute

## API Endpoints

### 1. Search Code Snippets

Find specific code implementations across repositories.

```bash
# Search for authentication implementations in Python
curl "http://localhost:8000/github/search/code?query=authentication&language=python"

# Find FastAPI routing examples
curl "http://localhost:8000/github/search/code?query=fastapi+router&language=python&per_page=10"

# Search in a specific repository
curl "http://localhost:8000/github/search/code?query=api&repo=fastapi/fastapi"

# Search in a specific organization
curl "http://localhost:8000/github/search/code?query=security&org=OWASP&language=python"
```

**Response Example:**
```json
{
  "status": "success",
  "search_type": "code",
  "query": "authentication",
  "filters": {
    "language": "python",
    "repo": null,
    "org": null
  },
  "results": {
    "total_count": 1234,
    "incomplete_results": false,
    "items": [
      {
        "name": "auth.py",
        "path": "src/auth.py",
        "url": "https://github.com/owner/repo/blob/main/src/auth.py",
        "repository": {
          "name": "owner/repo",
          "url": "https://github.com/owner/repo",
          "description": "Authentication library",
          "stars": 500
        },
        "score": 1.0
      }
    ],
    "rate_limit_remaining": "29",
    "rate_limit_reset": "1704812400"
  }
}
```

### 2. Search Repositories

Find repositories related to specific topics or technologies.

```bash
# Find OSINT tools
curl "http://localhost:8000/github/search/repositories?query=osint&language=python&sort=stars"

# Search for threat intelligence projects
curl "http://localhost:8000/github/search/repositories?query=threat+intelligence&sort=updated&order=desc"

# Find machine learning repositories
curl "http://localhost:8000/github/search/repositories?query=machine+learning&language=python&per_page=20"
```

**Response Example:**
```json
{
  "status": "success",
  "search_type": "repositories",
  "query": "osint",
  "filters": {
    "language": "python",
    "sort": "stars",
    "order": "desc"
  },
  "results": {
    "total_count": 450,
    "items": [
      {
        "name": "owner/osint-toolkit",
        "url": "https://github.com/owner/osint-toolkit",
        "description": "Open source intelligence gathering toolkit",
        "language": "Python",
        "stars": 1500,
        "forks": 300,
        "updated_at": "2024-01-01T00:00:00Z",
        "topics": ["osint", "security", "intelligence"],
        "score": 1.0
      }
    ]
  }
}
```

### 3. Search Documentation

Find documentation, guides, and README files.

```bash
# Find installation guides
curl "http://localhost:8000/github/search/documentation?query=installation+guide"

# Search API documentation in a specific repo
curl "http://localhost:8000/github/search/documentation?query=api+authentication&repo=owner/repo"

# Find setup documentation
curl "http://localhost:8000/github/search/documentation?query=setup+docker&per_page=15"
```

**Note:** This searches in `.md`, `.rst`, and `.txt` files.

### 4. Find Similar Implementations

Discover how other projects implement specific features.

```bash
# Find JWT authentication implementations
curl "http://localhost:8000/github/search/similar-implementations?feature=jwt+authentication&language=python"

# Search for rate limiting patterns
curl "http://localhost:8000/github/search/similar-implementations?feature=rate+limiting+fastapi"

# Find OAuth implementations
curl "http://localhost:8000/github/search/similar-implementations?feature=oauth2&language=python&per_page=10"
```

**Response Example:**
```json
{
  "status": "success",
  "search_type": "similar_implementations",
  "feature": "jwt authentication",
  "language": "python",
  "code_snippets": {
    "total_count": 850,
    "items": [
      {
        "name": "jwt_auth.py",
        "path": "app/security/jwt_auth.py",
        "url": "https://github.com/...",
        "repository": { ... }
      }
    ]
  },
  "example_repositories": {
    "total_count": 120,
    "items": [
      {
        "name": "owner/jwt-example",
        "url": "https://github.com/owner/jwt-example",
        "stars": 300,
        ...
      }
    ]
  },
  "rate_limit_remaining": "28"
}
```

## Python SDK Example

Use the GitHub client directly in your Python code:

```python
import asyncio
from app.clients.github_client import GitHubClient

async def search_examples():
    # Initialize client (uses GITHUB_TOKEN env var if available)
    client = GitHubClient()
    
    # Search for code
    results = await client.search_code(
        query="fastapi authentication",
        language="python",
        per_page=10
    )
    
    print(f"Found {results['total_count']} results")
    for item in results['items']:
        print(f"- {item['repository']['name']}: {item['path']}")
    
    # Search repositories
    repos = await client.search_repositories(
        query="osint tools",
        language="python",
        sort="stars"
    )
    
    print(f"\nTop repositories:")
    for repo in repos['items'][:5]:
        print(f"- {repo['name']} ({repo['stars']} stars)")

# Run async function
asyncio.run(search_examples())
```

## Use Cases

### 1. Research Similar OSINT Tools
```bash
curl "http://localhost:8000/github/search/repositories?query=osint+reconnaissance&language=python&sort=stars&per_page=20"
```

### 2. Find Security Best Practices
```bash
curl "http://localhost:8000/github/search/code?query=input+sanitization&language=python"
```

### 3. Discover API Integration Examples
```bash
curl "http://localhost:8000/github/search/similar-implementations?feature=virustotal+api&language=python"
```

### 4. Learn from Documentation
```bash
curl "http://localhost:8000/github/search/documentation?query=security+best+practices"
```

## Tips

1. **Specific Queries**: Use specific terms for better results
   - Good: `fastapi jwt authentication`
   - Less specific: `authentication`

2. **Language Filters**: Always specify language when possible
   ```bash
   &language=python
   ```

3. **Pagination**: Use `per_page` and `page` for large result sets
   ```bash
   &per_page=50&page=2
   ```

4. **Repository Scope**: Search in specific repos for focused results
   ```bash
   &repo=owner/repository
   ```

5. **Organization Scope**: Find all code from a specific org
   ```bash
   &org=OWASP
   ```

## Rate Limit Handling

The API automatically handles rate limits:
- Returns rate limit info in responses
- Retries with exponential backoff
- Logs rate limit warnings

Check rate limits in response:
```json
{
  "rate_limit_remaining": "25",
  "rate_limit_reset": "1704812400"
}
```

## Security Notes

1. **Never commit GitHub tokens** to version control
2. **Use environment variables** for API keys
3. **Respect GitHub's Terms of Service**
4. **Monitor your rate limit usage**

## Troubleshooting

### Rate Limit Exceeded
```
Solution: Wait until reset time or add GITHUB_TOKEN for higher limits
```

### No Results
```
Solution: Try broader search terms or check language filter
```

### Connection Errors
```
Solution: Verify internet connectivity and GitHub API status
```

## Further Reading

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitHub Search Syntax](https://docs.github.com/en/search-github/searching-on-github)
- [GitHub Rate Limits](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
