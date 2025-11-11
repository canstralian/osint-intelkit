# OSINT IntelKit Documentation

This directory contains the Sphinx documentation for OSINT IntelKit.

## Building Documentation

### Prerequisites

Install Sphinx and dependencies:

```bash
pip install -r backend/requirements-dev.txt
```

### Build HTML Documentation

```bash
cd docs
make html
```

The built documentation will be in `docs/_build/html/`.

### View Documentation

```bash
# Open the main page
open _build/html/index.html

# Or start a simple HTTP server
cd _build/html
python -m http.server 8080
# Then visit: http://localhost:8080
```

## Documentation Structure

```
docs/
├── index.md              # Main documentation page
├── getting-started.md    # Installation and quickstart
├── development.md        # Development guide
├── security.md           # Security best practices
├── api/                  # API reference
│   ├── index.md          # API overview
│   ├── main.rst          # Main application
│   ├── security.rst      # Security module
│   ├── routers.rst       # API routers
│   ├── workers.rst       # Background workers
│   ├── flows.rst         # Prefect flows
│   └── database.rst      # Database modules
├── conf.py               # Sphinx configuration
├── Makefile              # Build commands
└── _static/              # Static assets (CSS, images)
```

## Updating Documentation

### Auto-generate API Docs

The API reference is automatically generated from Python docstrings using `sphinx.ext.autodoc`.

**Update when you:**
- Add new modules
- Change function signatures
- Update docstrings

**Rebuild:**
```bash
cd docs
make clean
make html
```

### Write New Pages

1. Create a new `.md` or `.rst` file
2. Add it to the `toctree` in `index.md`
3. Rebuild documentation

### Docstring Format

Use Google-style docstrings:

```python
def normalize_domain(value: str) -> str:
    """
    Normalize domain name for consistent hashing and comparison.

    Performs the following transformations:
    - Converts to lowercase
    - Strips whitespace
    - Applies IDNA encoding for international domains

    Args:
        value: Raw domain name to normalize.

    Returns:
        Normalized domain name in lowercase ASCII.

    Example:
        >>> normalize_domain("  EXAMPLE.COM  ")
        'example.com'
    """
    ...
```

## Publishing Documentation

### GitHub Pages

1. Build documentation:
```bash
cd docs
make html
```

2. Copy to gh-pages branch:
```bash
git checkout gh-pages
cp -r docs/_build/html/* .
git add .
git commit -m "Update documentation"
git push origin gh-pages
```

3. Enable GitHub Pages in repository settings

### ReadTheDocs

1. Create account at https://readthedocs.org
2. Import repository
3. Set Python version to 3.11+
4. Build automatically on commits

## Troubleshooting

### ModuleNotFoundError

Ensure backend modules are in Python path:

```python
# In conf.py
sys.path.insert(0, os.path.abspath("../backend"))
```

### Missing Dependencies

Install all documentation dependencies:

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

### Build Warnings

Clean build directory:

```bash
cd docs
make clean
make html
```

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [MyST Parser (Markdown)](https://myst-parser.readthedocs.io/)
- [ReadTheDocs Theme](https://sphinx-rtd-theme.readthedocs.io/)
