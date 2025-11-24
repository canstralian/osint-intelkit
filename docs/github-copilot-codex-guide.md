# GitHub Copilot & Codex Configuration Guide for the Trading Bot Swarm

## Purpose and Scope
- **Objective:** Standardize how GitHub Copilot and Codex contribute to the Trading Bot Swarm so every change improves reliability, performance, and safety.
- **Pair-programmer role:** Treat Copilot as an assistant that proposes code under strict behavioral rules—no unchecked secrets, follow project style, prefer small iterative patches, and never skip reviews.
- **Coverage:** Applies to backend services, automation workflows, infrastructure-as-code, and operational scripts supporting the trading system.

## Configuration Overview
| Area | Expectations |
| --- | --- |
| Testing | Prefer `pytest` with coverage ≥90%. Require unit + integration tests for features. Mock external markets; use replay fixtures for deterministic results. |
| Linting | Run `ruff` and `black` for Python, `eslint` + `prettier` for TS/JS. Fail fast on warnings; no auto-fix commits without review. |
| Code style | Enforce typed Python (PEP 484), favor dataclasses/pydantic for DTOs, avoid wildcard imports, ensure docstrings for public APIs. |
| Async patterns | Use `asyncio`-native clients for exchange calls, wrap blocking IO with executors, and propagate cancellations. |
| Security defaults | Secrets via environment or vault. No plaintext keys, enforce least privilege IAM, verify TLS certs, sanitize inputs, and log auth attempts. |
| Logging & Observability | Use structured JSON logs, add trace IDs via OpenTelemetry, expose Prometheus metrics for fills, latency, and error counts. |
| CI/CD integration | Pull requests must pass lint/test workflow, security scan, and artifact build before merge. Require signed commits for deployment branches. |
| Version control | Trunk-based with short-lived feature branches. Use Conventional Commits, rebase before merge, tag releases with `vMAJOR.MINOR.PATCH`. |

## Custom Instruction Behavior
### Example Rules for Copilot
1. Suggest changes only within files marked safe by `.copilot-allow`.  
2. Prefer incremental diffs; cite rationale referencing style or spec.  
3. Never insert credentials or hard-coded endpoints.  
4. When tests or linters exist, generate commands to run them.  
5. Flag missing docs/tests as TODO comments if not immediately implemented.

### Example Rules for Codex
1. Treat user prompts as high-level specs; request clarifications when ambiguous.  
2. Output deterministic, idempotent code without side effects outside the described scope.  
3. Provide verification hints (e.g., commands, expected logs) after every patch.  
4. Default to secure patterns: parameterized queries, prepared statements, safe serialization.  
5. Respect project async rules—never mix sync/async DB drivers in the same flow.

### Conceptual Custom Instructions (YAML)
```yaml
copilot:
  persona: "Strict trading bot pair programmer"
  priorities:
    - security_first
    - follow_project_style_guides
    - prefer_small_patches
  required_actions:
    - run_tests_when_code_changes
    - suggest_linters_and_observability
  ignore_changes:
    - documentation_only
  guardrails:
    secrets: forbid
    network_calls: require_approval
    dependencies: use_locked_versions
codex:
  persona: "Trading automation architect"
  response_policy:
    detail_level: exhaustive
    include_commands: true
  validation:
    - ensure_async_consistency
    - require_logging_for_new_endpoints
  release_notes:
    conventional_commits: true
```

## Emphasis on Automated Quality Gates
- Every code change must run tests and linters locally and in CI; docs-only changes are exempt but should note "[skip quality gate]" in the PR description.
- Coverage diffs must not decrease unless accompanied by a risk memo approved by maintainers.
- Blocking criteria: failing tests, lint errors, dropped security controls, or unreviewed migrations.

## GitHub Workflow: Lint & Test Automation
Trigger on pull requests to `main`, `develop`, and release branches, excluding markdown-only changes:
```yaml
name: lint-and-test
on:
  pull_request:
    branches: [main, develop, 'release/**']
    paths-ignore:
      - '**/*.md'
jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install tools
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Lint
        run: |
          ruff check .
          black --check .
      - name: Tests
        env:
          PYTEST_ADDOPTS: "--maxfail=1 --disable-warnings"
        run: pytest --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
```

## Semantic Release & Version Tagging Workflow
- Use Conventional Commits to drive `semantic-release` for automated versioning and changelog generation.
- Tags follow `vMAJOR.MINOR.PATCH`; release assets include Docker images and infrastructure manifests.
```yaml
name: semantic-release
on:
  push:
    branches: [main]
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run build --if-present
      - name: Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: npx semantic-release
```

## Security & Dependency Scanning Workflow
- Integrate daily scans plus PR gating for dependency and container images.
```yaml
name: security-scan
on:
  schedule:
    - cron: '0 3 * * *'
  pull_request:
    branches: [main, develop]
jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Scan dependencies
        uses: aquasecurity/trivy-action@v0.13.1
        with:
          scan-type: fs
          ignore-unfixed: true
          severity: 'CRITICAL,HIGH'
  codeql:
    uses: github/codeql-action/analyze@v3
    with:
      category: '/language:python'
```

## Contributor Guidelines
1. **Proposing changes:** Open an issue describing motivation, risk, and rollout plan. For automation updates, attach the expected CI output.
2. **Review criteria:** reviewers verify test coverage, lint cleanliness, security posture, and adherence to async/logging conventions.
3. **Validation:** merge only after CI green, manual smoke tests recorded, and release checklist signed.
4. **Documentation:** update this guide when introducing new tools, workflows, or standards affecting Copilot/Codex behavior.

## Troubleshooting & Optimization Tips
- **Copilot drift:** If suggestions violate style, regenerate context by trimming files and re-running linting to provide fresh cues.
- **Flaky tests:** Capture flaky markers, run with `pytest -n auto --reruns 2`, and attach logs to PRs.
- **Long CI queues:** Use matrix builds with dependency caching (pip cache, Docker layer cache) and limit optional jobs on doc-only PRs.
- **Credential warnings:** Validate `.env.example` against secrets manager; ensure CI uses OIDC to fetch temporary tokens instead of storing long-lived secrets.

## Maintenance Schedule
- **Quarterly:** Review testing/linting stacks, Copilot/Codex instruction YAML, and workflow runners. Update versions to match supported runtimes.
- **Monthly:** Audit security scanning outputs and dependency reports; refresh ignored CVE lists with business justification.
- **Release windows:** Before each semantic release, verify version tags, changelog accuracy, and Copilot/Codex behavior alignment.

## Closing Note
Standardizing these practices strengthens the trading ecosystem’s reliability, performance, and safety—delivering consistent excellence across automation, analytics, and operations.
