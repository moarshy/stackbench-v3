# Stackbench Development Roadmap

## Status Legend
- ✅ **Completed** - Fully implemented and tested
- 🚧 **In Progress** - Actively being worked on
- 📋 **Planned** - Not yet started
- 🔄 **Deferred** - Lower priority, revisit later

---

## Priority 1: Core Infrastructure ✅ COMPLETED

### 1. Extraction Agent ✅
- [x] Parse markdown documentation
- [x] Extract API signatures (function names, parameters, types, defaults)
- [x] Extract code examples
- [x] Handle MkDocs Material snippet includes (`--8<--`)
- [x] Pydantic schema validation
- [x] Parallel processing with worker pools

### 2. API Signature Validation Agent ✅
- [x] Install library in isolated environment
- [x] Dynamic introspection via `inspect.signature()`
- [x] Compare documented vs actual signatures
- [x] Report parameter mismatches, wrong defaults, missing APIs
- [x] Confidence scoring

### 3. Code Example Validation Agent ✅
- [x] Execute code examples in isolated environments
- [x] Catch syntax errors, runtime errors, import issues
- [x] Dependency tracking between examples
- [x] Severity classification (error/warning/info)

### 4. Documentation Clarity Agent ✅
- [x] LLM-as-judge scoring system
- [x] 5-dimensional scoring (instruction clarity, logical flow, completeness, consistency, prerequisites)
- [x] Issue detection with precise line numbers
- [x] MkDocs Material snippet preprocessing
- [x] Integration with API/code validation results
- [x] Parallel processing with worker pools
- [x] **NEW:** Ignore rendering artifacts (indentation from test files)
- [x] **NEW:** Cross-section variable reference handling

### 5. Hooks System ✅
- [x] PreToolUse validation hooks (block invalid JSON)
- [x] PostToolUse logging hooks (capture execution trace)
- [x] Per-agent validation schemas
- [x] Human-readable `.log` + machine-readable `.jsonl`

---

## Priority 2: Repository Management & Caching ✅ COMPLETED

### 6. Repository Manager Enhancements ✅
- [x] Clone repositories with branch/commit support
- [x] Automatic commit hash resolution from branch HEAD
- [x] Find markdown files in specified directories
- [x] **NEW:** API reference page detection and filtering
- [x] **NEW:** Document discovery metrics tracking

### 7. Smart Caching System ✅
- [x] JSON-based cache (`data/runs.json`)
- [x] Cache key: `{repo}:{commit}:{docs_path}:{library}:{version}`
- [x] Instant cache hits for identical runs
- [x] `--force` flag to bypass cache
- [x] Cache status tracking

### 8. Versioning System ✅
- [x] Track documentation version (git commit hash)
- [x] Track library version (pip install version)
- [x] Two independent versioning dimensions
- [x] CLI parameters: `--commit`, `--docs-path`, `--include-folders`
- [x] Metadata persistence

### 9. Document Filtering Metrics ✅
- [x] Track total markdown files in repository
- [x] Track files in include folders
- [x] Track files filtered as API reference
- [x] Track files actually validated
- [x] Persist metrics in metadata.json
- [x] Enhanced console output

---

## Priority 3: Walkthrough Validation System ✅ COMPLETED

### 10. Walkthrough Generation Agent ✅
- [x] Convert tutorial docs to structured walkthroughs
- [x] Extract step-by-step instructions
- [x] 4 content fields per step (contentForUser, contextForAgent, operationsForAgent, introductionForAgent)
- [x] Validation hooks for output quality

### 11. MCP Server for Walkthroughs ✅
- [x] stdio-based Model Context Protocol server
- [x] Step-by-step delivery (prevent skipping ahead)
- [x] Tools: `start_walkthrough()`, `next_step()`, `walkthrough_status()`, `report_gap()`
- [x] State tracking (current step, completed steps)

### 12. Walkthrough Audit Agent ✅
- [x] Execute walkthroughs like a real developer
- [x] MCP integration for controlled pacing
- [x] Gap detection across 6 categories:
  - Clarity gaps
  - Prerequisite gaps
  - Logical flow gaps
  - Execution gaps
  - Completeness gaps
  - Cross-reference gaps
- [x] Structured gap reporting with severity levels

### 13. Walkthrough CLI Commands ✅
- [x] `stackbench walkthrough generate` - Create walkthroughs
- [x] `stackbench walkthrough audit` - Execute and validate
- [x] `stackbench walkthrough run` - Full pipeline
- [x] Support for `--from-run` (reuse cloned repos)

---

## Priority 4: Web Interface & Visualization 🚧 IN PROGRESS

### 14. Frontend Dashboard (Partially Complete)
- [x] React 19 + TypeScript + Vite
- [x] Tailwind CSS styling
- [x] Basic results viewing
- [ ] 🔄 Run listing and comparison UI (deferred)
- [ ] 🔄 Version comparison page (deferred)
- [ ] 🔄 Interactive clarity score visualization (deferred)
- [ ] 🔄 Gap detection results viewer (deferred)

### 15. API Endpoints 🔄 DEFERRED
- [ ] List all runs
- [ ] Get run details
- [ ] Compare runs (version A vs version B)
- [ ] Filter by library/version

---

## Priority 5: Advanced Features 🚧 IN PROGRESS

### 16-17. API Completeness & Deprecation Agent 🚧 (Combined)
**Status:** Implemented, needs testing
- [x] Discover all public APIs via library introspection (inspect module)
- [x] Detect deprecated APIs (@deprecated decorators, DeprecationWarning patterns)
- [x] Aggregate documentation coverage across all pages
- [x] Calculate tiered coverage (mentioned, has example, dedicated section)
- [x] Identify undocumented APIs ranked by importance
- [x] Flag documentation still using deprecated APIs
- [x] Suggest migration to new APIs
- [x] Coverage percentage metrics
- [x] Integration into main pipeline (runs after extraction)
- [x] Pydantic schemas for output validation
- [x] Validation hooks for JSON quality
- [ ] End-to-end testing on real library (e.g., LanceDB)
- [ ] Refinement of importance scoring heuristics
- [ ] CLI output formatting and summary display

**Implementation Details:**
- Takes entire doc folder as input (not individual docs)
- Runs after all extraction complete
- Combines deprecation detection + coverage analysis in single agent
- Uses pip install + introspection (like API validation agent)
- Outputs to `results/api_completeness/completeness_analysis.json`

### 18. Real-World Integration Gaps Agent 📋
- [ ] Detect missing error handling in examples
- [ ] Flag missing security considerations
- [ ] Check for production best practices
- [ ] Validate resource cleanup (connections, files, etc.)

### 19. Multi-Language Support 📋
- [ ] TypeScript/JavaScript validation
- [ ] Go code execution
- [ ] Rust example validation
- [ ] Language-agnostic extraction

### 20. Auto-Fix Mode 📋
- [ ] AI-powered documentation fixes
- [ ] Generate pull requests with corrections
- [ ] Interactive fix approval workflow

---

## Priority 6: CI/CD Integration 📋 PLANNED

### 21. GitHub Actions Integration 📋
- [ ] Automated PR checks
- [ ] Fail builds on accuracy threshold
- [ ] Comment validation results on PRs
- [ ] Track quality trends over time

### 22. Quality Thresholds 📋
- [ ] Configurable minimum accuracy scores
- [ ] Block merges below threshold
- [ ] Warning vs error distinction
- [ ] Per-document exemptions

---

## Priority 7: Bug Fixes & Quality Improvements 🚧 IN PROGRESS

### 23. Clarity Scoring Inconsistency ✅ FIXED
- [x] Investigate scoring calculation bug
- [x] Issue: High individual dimension scores (7.3-10.0) result in low overall scores (4.6)
- [x] Example: `pandas_and_pyarrow.md` has dimensions [9.8, 8.0, 7.3, 10.0, 9.5] but overall 4.6
- [x] Root cause: Dimension scores calculated per-dimension, overall score calculated globally
- [x] Fix: Changed overall score to be average of dimension scores (clarity_scoring_server.py:734-788)
- [x] Test: Verified fix on all 5 documents - all now show consistent scoring
- **Results:** pandas_and_pyarrow.md now 8.9 (Tier A) instead of 4.6 (Tier C)

### 24. Code Example Executability Detection ✅ FIXED
- [x] Improve async code detection in extraction agent
- [x] Issue: Code with `await` marked as `is_executable: false` (technically correct but misleading)
- [x] Examples: `async_db = await lancedb.connect_async(uri)`, `result = await table.search(...)`
- [x] Old behavior: Agent marks as non-executable because it can't run in sync context
- [x] New behavior: Distinguishes "not executable standalone" vs "executable in async context"
- [x] Added new field: `execution_context` with values: "sync", "async", "not_executable"
- [x] Updated extraction agent to detect async patterns (async def, await keywords)
- [x] Updated code validation agent to handle async examples with asyncio wrapping
- [x] Tested: Detection logic validates correctly for all patterns
- **Implementation:**
  - Schema: Added `execution_context` field with default "sync" (schemas.py:50-58)
  - Extraction agent: Added async detection instructions (extraction_agent.py:171-203)
  - Code validation: Added async wrapping template (code_example_validation_agent.py:83-114)
- **Results:** Future extractions will properly categorize async code

---

## Recent Improvements

### Async Code Detection ✅ (2025-10-28)
- **Fixed:** Async code examples now properly categorized instead of marked as non-executable
  - Old behavior: `await lancedb.connect_async(uri)` → is_executable: false (misleading)
  - New behavior: Adds `execution_context` field ("sync", "async", "not_executable")
  - Impact: Async code can now be properly validated by wrapping in asyncio context
- **Implementation:** Three-part fix
  - Schema: Added `execution_context` field with default "sync"
  - Extraction agent: Detects await/async def/async with/async for patterns
  - Code validation: Wraps async code in `async def main()` + `asyncio.run()`
- **Patterns detected:**
  - `async`: Code with `await`, `async def`, `async with`, `async for`
  - `sync`: Regular synchronous Python code
  - `not_executable`: Incomplete snippets with `...` or placeholders
- **Backwards compatible:** `is_executable` field retained for compatibility

### Clarity Scoring Fix ✅ (2025-10-28)
- **Fixed:** Massive scoring inconsistency between dimensions and overall score
  - Root cause: Dimension scores calculated per-dimension, overall calculated globally
  - Old behavior: pandas_and_pyarrow.md had dimensions avg 8.9 but overall 4.6 (Tier C)
  - New behavior: Overall score = average of dimension scores (consistent)
  - Impact: All 5 LanceDB docs moved from B/C tier to A tier (8.9-9.5 range)
- **Implementation:** Modified clarity_scoring_server.py tool handler
  - Calculate dimension scores first (per-dimension penalties)
  - Average dimensions to get overall score
  - Keep breakdown for transparency
- **Validation:** Tested on all 5 documents, all show consistent scoring

### Clarity Agent Enhancements ✅ (Previous Session)
- **Fixed:** Indentation false positives from test-sourced code
  - Aggressive whitespace normalization in snippet preprocessing
  - Updated prompt to ignore rendering artifacts entirely
- **Added:** Cross-section variable reference handling
  - Checks entire document before flagging as "undefined"
  - Uses `info` severity instead of `critical` for cross-section refs
- **Focus:** Content clarity over formatting issues

### API Reference Page Filtering ✅
- **Detected by:** 3 heuristics (title, file size + directive count, directive density)
- **Results:** `saas-python.md` (39 sigs from 24 lines) → filtered
- **Results:** `python.md` (45 directives, 27% density) → filtered
- **Kept:** 5 tutorial pages (datafusion, duckdb, pandas_and_pyarrow, polars_arrow, pydantic)

### Document Discovery Metrics ✅
- **New metadata fields:**
  - `total_markdown_files` - All .md/.mdx in repo
  - `markdown_in_include_folders` - After path filtering
  - `filtered_api_reference_count` - API ref pages filtered
  - `validated_document_count` - Actual files validated
- **Enhanced output:** Console now shows discovery funnel
- **Persistence:** All metrics saved to metadata.json

---

## Testing & Quality Assurance

### Current Test Coverage
- ✅ Unit tests for schemas
- ✅ Integration tests for agents
- ✅ End-to-end pipeline tests
- ✅ Real-world validation (LanceDB docs)

### Known Issues
- ~~**Clarity scoring inconsistency**~~ - ✅ FIXED (see Priority 7, #23)
- ~~**Async code executability**~~ - ✅ FIXED (see Priority 7, #24)

---

## Performance Metrics (Latest Run)

- **Repository:** LanceDB (https://github.com/lancedb/lancedb)
- **Total markdown files:** ~156 in entire repo
- **In include folders:** 7 (docs/src/python)
- **Filtered (API ref):** 2 (python.md, saas-python.md)
- **Validated:** 5 tutorial pages
- **Processing time:** ~3-5 minutes with 5 workers

---

## Documentation

- ✅ `README.md` - User-facing documentation with versioning examples
- ✅ `CLAUDE.md` - Comprehensive architecture and design docs
- ✅ `stackbench/hooks/README.md` - Hook system details
- ✅ `stackbench/walkthroughs/README.md` - Walkthrough module guide
- ✅ `local-docs/walkthrough-validation-plan.md` - Architecture design
- ✅ `local-docs/demo-nextjs-walkthrough.json` - Real example

---

## Next Steps

1. **Test Latest Improvements**
   - Run full pipeline with new clarity agent improvements
   - Verify API reference filtering works correctly
   - Check metadata.json contains all new metrics

2. **Frontend Work** (Deferred for now)
   - Version comparison UI
   - Run listing and filtering
   - Interactive visualizations

3. **Advanced Features** (Future)
   - Deprecated API detection
   - Missing coverage analysis
   - Multi-language support

---

Last Updated: 2025-10-28 (Fixed clarity scoring + async code detection - Priority 7, #23 & #24)
