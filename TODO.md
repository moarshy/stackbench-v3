# Stackbench TODO List

## Priority 1: Critical UI & Data Directory Issues ✅ COMPLETED

### 1.1 Configuration UI Fixes ✅
- [x] **Analyze UI configuration issues** - Investigate hardcoded Base Data Directory and readability problems
  - ✅ Current issue: Configuration section has poor readability
  - ✅ Current issue: Base Data Directory is hardcoded
  - ✅ Goal: Make UI readable and dynamic

- [x] **Design solution for dynamic base directory inference from repo URL**
  - ✅ Input: Git URL (e.g., `https://github.com/lancedb/lancedb`)
  - ✅ Output: Intelligently inferred base directory structure
  - ✅ Consider: `data/<run_id>/` vs custom paths

- [x] **Implement base directory inference logic in backend**
  - ✅ Location: `frontend/vite-plugin-local-fs.ts` (added `/api/config` endpoint)
  - ✅ Backend auto-detects path using `process.cwd()` and resolves `../data`

- [x] **Update frontend Configuration component to use dynamic base directory**
  - ✅ Location: `frontend/src/services/api.ts`
  - ✅ Added `fetchBaseDataDirFromBackend()` and `configInitialized` Promise
  - ✅ localStorage persistence for user overrides

- [x] **Fix UI readability issues in Configuration section**
  - ✅ Added 370+ lines of modern CSS to `frontend/src/index.css`
  - ✅ Removed all inline styles from `Settings.tsx` and `RunInfo.tsx`
  - ✅ Modern design with animations, gradients, better typography
  - ✅ Dark mode support built-in

**Implementation Summary:**
- Backend auto-detection via `/api/config` endpoint
- Frontend async initialization with `configInitialized` Promise
- Modern UI with animations, gradients, improved readability
- Tested with Playwright - all features working correctly

## Priority 2: Code Example Validation - False Positives ✅ COMPLETED

### 2.1 Core Problem

**Issue:** Code examples sometimes fail due to validation environment issues (dependency conflicts, version mismatches) rather than actual documentation errors. These should not be marked as hard failures.

**Example from LanceDB docs:**
```
Example 9 (Line 186): ldf.first().collect()
Error: TypeError: _scan_pyarrow_dataset_impl() got multiple values for argument 'batch_size'
Status: FAILURE (but it's actually an environment compatibility issue between polars/lancedb versions)
```

**Goal:** Distinguish between documentation errors vs environment issues without over-engineering.

### 2.2 Tasks

- [x] **Analyze current code example validation agent behavior**
  - Read: `stackbench/agents/code_example_validation_agent.py`
  - Understand: How are errors currently caught and classified?
  - Identify: What error information is available (exception type, message, traceback)?

- [x] **Add simple error severity classification**
  - Keep it simple: Just add a `severity` field to validation results
  - Categories:
    - `"error"` - Clear documentation mistake (syntax error, wrong API, missing import)
    - `"warning"` - Might be environment issue (internal lib errors, dependency conflicts)
    - `"info"` - Example ran but with warnings/deprecations

- [x] **Implement basic heuristics for classification**
  - Simple pattern matching on error messages:
    - Contains library name in internal stacktrace → `"warning"`
    - `SyntaxError`, `NameError`, `ImportError` from user code → `"error"`
    - `AttributeError` with documented API → `"error"`
  - Don't over-engineer: No ML, no complex dependency resolution

- [x] **Update output schema to include severity**
  - Location: `stackbench/schemas.py` - Update `CodeExampleValidationResult`
  - Add field: `severity: Literal["error", "warning", "info"]`
  - Update validation hooks to allow this field

- [x] **Update UI to display severity appropriately**
  - Show errors prominently (red)
  - Show warnings less prominently (yellow) with context
  - Allow filtering by severity in frontend

**Implementation Summary:**
- Backend: Added `severity` field to schemas, updated agent prompt with classification guidelines
- Frontend: Added severity badges, color-coded borders, 4-column validation tab layout
- Total changes: 9 files modified, 132 lines of CSS added

## Priority 3: Clarity Agent Improvements

### 3.1 Analysis Phase

- [ ] **Read and analyze all clarity validation results**
  - Location: `/Users/arshath/play/naptha/stackbench-v2/stackbench-v3/data/cda6a873-9c5d-4d6c-91eb-8325f805acb9/results/clarity_validation/`
  - Files: `*_clarity.json`
  - Create summary document of issues found

- [ ] **Document specific clarity agent issues**
  - Focus: Indentation rendering problems
  - Focus: False positives in clarity scoring
  - Focus: Missing context in suggestions
  - Focus: Line number accuracy

- [ ] **Root cause analysis - indentation errors**
  - Question: Why do indentation errors occur?
  - Hypothesis 1: Markdown code blocks not preserved correctly
  - Hypothesis 2: JSON serialization strips whitespace
  - Hypothesis 3: Agent prompt doesn't emphasize preserving formatting
  - Action: Test each hypothesis

### 3.2 Implementation Phase

- [ ] **Design improved markdown rendering approach**
  - Option 1: Pre-process markdown to normalize indentation before sending to agent
  - Option 2: Use markdown AST parser (e.g., `markdown-it`, `mistune`)
  - Option 3: Instruct agent to preserve code block formatting explicitly
  - Option 4: Post-process agent output to fix indentation

- [ ] **Implement clarity agent improvements**
  - Location: `stackbench/agents/clarity_agent.py`
  - Update system prompt if needed
  - Update markdown preprocessing logic
  - Update validation hooks if output schema changes

- [ ] **Test clarity agent with improved rendering**
  - Test documents: Select 3-5 docs from previous run
  - Compare: Old results vs new results
  - Metrics: Indentation preservation, line number accuracy, suggestion quality

### 3.3 Additional Clarity Improvements

- [ ] **Improve clarity scoring rubric** (if needed based on analysis)
  - Current: 5 dimensions (instruction_clarity, logical_flow, completeness, consistency, prerequisite_coverage)
  - Consider: Add dimension for "code example quality"
  - Consider: Weight dimensions differently

- [ ] **Add context from API/code validation to clarity agent**
  - Already partially implemented (IMPLEMENTATION_STATUS.md mentions this)
  - Verify it's working: Does clarity agent know when code examples failed?
  - Improve correlation: "This code example has unclear instructions AND failed validation"

## Priority 4: Versioning & Workflow Improvements

### 4.1 Input Format Changes

**Current:**
```bash
stackbench run --repo <url> --branch main --include-folders docs/
```

**Proposed:**
```bash
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --commit fe25922449cfaf2ae34ae6969ae6cdea37b53b61 \  # Optional - defaults to latest commit on branch
  --docs-path docs/src \                                  # Base docs directory
  --include-folders python,javascript                     # Relative to docs-path
```

**Examples:**
```bash
# Use latest commit on main branch, analyze all markdown in docs/src/python/
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --include-folders python

# Pin to specific commit (for version comparison)
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --commit fe25922449cfaf2ae34ae6969ae6cdea37b53b61 \
  --docs-path docs/src \
  --include-folders python

# Analyze multiple folders
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs \
  --include-folders guides,api,tutorials
```

**Key Design Decisions:**
- `--commit` is **optional** - if not provided, use latest commit from `--branch` (or HEAD)
- Resolved commit hash is **stored in metadata.json** for reproducibility
- `--docs-path` is the **base directory** (e.g., `docs/src`)
- `--include-folders` is **relative to docs-path** (e.g., `python` → `docs/src/python/`)
- This supports versioned docs structures like: `docs/v1/`, `docs/v2/`, etc.

**Tasks:**
- [ ] **Design versioning system**
  - Support: git URL + branch + optional commit hash
  - Support: docs-path (base) + include-folders (relative)
  - Resolve commit: If `--commit` not provided, resolve branch HEAD
  - Store in metadata: Always save resolved commit hash

- [ ] **Update CLI arguments**
  - Location: `stackbench/cli.py`
  - Keep: `--branch` (default: `main`)
  - Add: `--commit` (optional, overrides branch if provided)
  - Add: `--docs-path` (base directory for docs, default: `docs/`)
  - Keep: `--include-folders` (now relative to docs-path, default: `.` = all)

- [ ] **Update metadata.json schema**
  - Add fields:
    ```json
    {
      "run_id": "uuid",
      "repo_url": "https://github.com/lancedb/lancedb",
      "branch": "main",
      "commit_hash": "fe259224..." ,  // Always resolved and stored
      "docs_path": "docs/src",
      "include_folders": ["python", "javascript"],
      "timestamp": "2025-01-15T10:30:00Z"
    }
    ```

- [ ] **Implement commit resolution logic**
  - Location: `stackbench/repository/manager.py`
  - Logic:
    ```python
    if commit_hash:
        resolved_commit = commit_hash
    else:
        # Resolve branch to commit hash
        resolved_commit = git.rev_parse(f"origin/{branch}")
    ```

- [ ] **Update documentation path resolution**
  - Logic: `full_path = os.path.join(docs_path, include_folder)`
  - Example: `docs/src` + `python` → `docs/src/python/`
  - Support glob patterns in include-folders (e.g., `v*` → `v1/`, `v2/`)

### 4.2 Run Deduplication & Caching

- [ ] **Implement run deduplication logic**
  - Before running pipeline: Check if commit hash + docs path already processed
  - Storage: `data/runs.db` (SQLite) or `data/runs.json`
  - Schema:
    ```json
    {
      "run_id": "uuid",
      "repo_url": "https://github.com/...",
      "commit_hash": "fe259224...",
      "docs_path": "docs/src/python",
      "timestamp": "2025-01-15T10:30:00Z",
      "status": "completed"
    }
    ```

- [ ] **Design result caching strategy**
  - Key: `{repo_url}:{commit_hash}:{docs_path}`
  - Value: Run ID (UUID)
  - Cache hit: Serve results from existing run
  - Cache miss: Run new analysis
  - Add `--force` flag to bypass cache

- [ ] **Implement result caching system**
  - Location: New module `stackbench/cache/` or extend `stackbench/repository/`
  - Functions:
    - `get_cached_run(repo_url, commit_hash, docs_path) -> Optional[UUID]`
    - `cache_run(repo_url, commit_hash, docs_path, run_id) -> None`
    - `invalidate_cache(run_id) -> None`

### 4.3 Version Comparison UI

- [ ] **Add version comparison UI**
  - Location: `frontend/src/pages/VersionComparison.tsx` (new page)
  - Input: Two run IDs (v1 vs v1.1)
  - Output:
    - Side-by-side comparison
    - Metrics: API validation pass rate, code example pass rate, clarity scores
    - Diff view: New issues, resolved issues, unchanged issues

- [ ] **Update frontend to display version history**
  - Location: `frontend/src/pages/Dashboard.tsx` (or similar)
  - Show: Timeline of all runs for a repository
  - Show: Trend lines (quality improving/declining over time)

## Priority 5: Recommendation-Focused Output (Human-in-the-Loop)

### 5.1 Philosophy Shift

**Current approach:** Some outputs suggest fixes, but not consistently focused on recommendations.

**Target approach:** All outputs emphasize actionable recommendations; no automatic fixes; human reviews and approves changes.

**Tasks:**
- [ ] **Design recommendation-focused output format**
  - Structure:
    ```json
    {
      "issue": "Example 9 has compatibility error",
      "severity": "warning",
      "location": "Line 186",
      "recommendation": {
        "title": "Update code example to avoid polars compatibility issue",
        "description": "Replace ldf.first().collect() with ldf.limit(1).collect()",
        "diff_suggestion": "- ldf.first().collect()\n+ ldf.limit(1).collect()",
        "rationale": "Avoids known compatibility issue between polars and lancedb 0.25.2"
      }
    }
    ```

- [ ] **Update extraction agent output** (if needed)
  - Ensure it provides recommendations, not just detection

- [ ] **Update API validation agent output**
  - For each invalid signature: Provide recommendation
  - Example: "Update documentation to match actual signature: `connect(host, port, timeout=30)`"

- [ ] **Update code example validation agent output**
  - For each failed example: Provide recommendation
  - Example: "Add missing import: `import pandas as pd`"

- [ ] **Update clarity agent output**
  - Already recommendation-focused (has `suggestions` field)
  - Verify: Are suggestions actionable enough?
  - Add: Diff suggestions for structural improvements

- [ ] **Update frontend to display recommendations prominently**
  - Add "Recommended Fixes" section to each validation result
  - Add "Accept" / "Reject" / "Modify" buttons (future feature)
  - Add "Export to PR" button (generates PR description with recommendations)

## Priority 6: Automatic Change Detection & Proactive Alerts

### 6.1 Change Detection System

**Goal:** Detect when documentation changes and automatically trigger re-analysis.

**Use case:** Repository updates docs from v1 to v1.1 → Stackbench detects change → Runs analysis → Notifies doc manager of any new issues.

**Tasks:**
- [ ] **Design automatic change detection system**
  - **Approach 1: Webhook-based (GitHub webhook)**
    - User installs GitHub App or sets up webhook
    - On push to docs folder → Webhook fires → Stackbench runs
    - Pros: Real-time, accurate
    - Cons: Requires server, user setup

  - **Approach 2: Polling-based**
    - Stackbench polls GitHub API every N minutes
    - Check if commit hash changed for watched branch
    - Pros: Simple, no user setup
    - Cons: Delay, API rate limits

  - **Approach 3: GitHub Actions integration**
    - User adds Stackbench action to `.github/workflows/docs.yml`
    - Runs on every PR/push to docs folder
    - Pros: Native GitHub integration, no external server
    - Cons: Requires users to add workflow file

  - **Recommendation:** Start with Approach 3 (GitHub Actions), add Approach 1 (webhooks) later

- [ ] **Implement change detection mechanism**
  - For GitHub Actions approach:
    - Create: `stackbench-action` repository with GitHub Action definition
    - Create: `action.yml` with inputs (repo, docs-path, api-key)
    - Create: Action runner that calls Stackbench CLI
  - For webhook approach (future):
    - Create: `stackbench/server/webhook.py` Flask/FastAPI endpoint
    - Endpoint: Receives GitHub webhook, validates signature, triggers analysis

### 6.2 Automatic Re-analysis

- [ ] **Implement automatic re-analysis trigger**
  - On change detected:
    1. Get new commit hash
    2. Check cache (don't re-run if already analyzed)
    3. Run full pipeline: extract → validate → clarify
    4. Compare with previous run (if exists)
    5. Generate diff report

- [ ] **Add re-analysis queue system** (for high-volume scenarios)
  - Storage: Redis or in-memory queue
  - Handle: Multiple repositories with concurrent changes
  - Priority: Paid users > free users (for SaaS model)

### 6.3 Notification System

- [ ] **Design notification system**
  - **Notification channels:**
    - Email (doc manager)
    - Slack webhook
    - GitHub PR comment
    - Discord webhook
    - In-app notification (frontend)

  - **Notification content:**
    ```
    Subject: Documentation Quality Report for lancedb v0.25.3

    Good news! Your documentation quality improved:
    - API validation: 95% pass rate (↑ 5% from v0.25.2)
    - Code examples: 88% pass rate (↓ 2% from v0.25.2)
    - Clarity score: 8.2/10 (unchanged)

    ⚠️ 2 new issues detected:
    1. Example 12: Missing import statement (Line 243)
    2. Example 15: Deprecated API usage (Line 301)

    View full report: https://stackbench.app/runs/abc123
    ```

- [ ] **Implement notification system**
  - Location: `stackbench/notifications/` (new module)
  - Modules:
    - `base.py` - Abstract notification provider
    - `email.py` - Email notifications (SMTP or SendGrid)
    - `slack.py` - Slack webhooks
    - `github.py` - GitHub PR comments
  - Configuration: `stackbench.config.yml` with notification settings

### 6.4 SaaS Justification Features

**Rationale:** Automatic change detection + proactive alerts justify SaaS pricing (like antivirus: change in filesystem → scan triggered).

- [ ] **Add usage tracking for SaaS model**
  - Track: Number of runs per repository
  - Track: Number of documents analyzed
  - Track: API calls to Claude
  - Track: Storage used

- [ ] **Design pricing tiers**
  - **Free tier:**
    - 5 repositories
    - Manual analysis only
    - 100 documents/month

  - **Pro tier ($29/month):**
    - Unlimited repositories
    - Automatic change detection
    - 1000 documents/month
    - Email + Slack notifications

  - **Enterprise tier (custom pricing):**
    - Self-hosted option
    - SSO/SAML
    - Priority support
    - Custom integrations

- [ ] **Implement usage limits and billing**
  - Location: `stackbench/billing/` (new module)
  - Integration: Stripe or LemonSqueezy
  - Features: Usage metering, overage alerts, upgrade prompts

## Priority 7: Testing & Validation

- [ ] **Test end-to-end versioning workflow**
  - Repository: Use LanceDB docs as test case
  - Scenario 1: Run analysis on commit A → cache hit on re-run
  - Scenario 2: Run analysis on commit A → run on commit B → compare results
  - Scenario 3: Docs unchanged → cache serves results instantly

- [ ] **Test code example validation with new error classification**
  - Test case 1: Real library error (should fail)
  - Test case 2: Environment compatibility error (should warn)
  - Test case 3: System error (should skip)

- [ ] **Test clarity agent improvements**
  - Test case 1: Code block with complex indentation
  - Test case 2: Mixed tabs and spaces
  - Test case 3: Inline code vs code blocks

- [ ] **Load testing for concurrent analysis**
  - Simulate: 10 repositories analyzed simultaneously
  - Measure: Agent worker pool performance
  - Measure: Claude API rate limits handling

- [ ] **Integration tests for change detection**
  - Mock: GitHub webhook payload
  - Test: Webhook triggers analysis
  - Test: Results stored and notification sent

## Priority 8: Documentation & Deployment

- [ ] **Update README.md with new CLI commands**
  - Document: `--commit`, `--docs-path`, `--force`
  - Document: Versioning workflow
  - Document: Caching behavior

- [ ] **Create user guide for recommendation workflow**
  - Location: `docs/user-guide/recommendations.md`
  - Content: How to review recommendations, apply fixes, re-run analysis

- [ ] **Create developer guide for adding new agents**
  - Already exists: `CLAUDE.md` → "Adding a New Agent"
  - Update: Include error classification patterns
  - Update: Include versioning considerations

- [ ] **Deploy GitHub Action to marketplace**
  - Repository: `stackbench-action`
  - README: Setup instructions for users
  - Example workflow file users can copy

- [ ] **Set up demo instance**
  - Deploy: Stackbench web UI to Vercel/Netlify
  - Deploy: Backend API to Railway/Fly.io
  - Use case: Users can try Stackbench without installing

## Summary: Next Immediate Actions

**Week 1-2 Focus (Critical):**
1. Fix UI configuration issues (Priority 1)
2. Fix code example validation false positives (Priority 2)
3. Analyze and improve clarity agent (Priority 3)

**Week 3-4 Focus (High Value):**
4. Implement versioning system (Priority 4.1, 4.2)
5. Build version comparison UI (Priority 4.3)
6. Shift to recommendation-focused output (Priority 5)

**Week 5-6 Focus (SaaS Features):**
7. Implement change detection (Priority 6.1, 6.2)
8. Build notification system (Priority 6.3)
9. Add usage tracking and billing (Priority 6.4)

**Ongoing:**
- Testing (Priority 7)
- Documentation updates (Priority 8)
