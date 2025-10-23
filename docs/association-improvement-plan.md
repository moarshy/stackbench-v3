# Plan: Better Association Between Validation Results & Documentation

## Goal
Make it **immediately visible** which code examples passed/failed validation, **directly in the documentation viewer**, with click-to-navigate for details.

## Problem Statement

### Current Issues
1. **No visual link between docs and validation**: User has to mentally map "Example 2 at line 32" to the actual code block in the documentation
2. **Tab switching required**: Must switch between Documentation tab and Validation tabs to understand what failed
3. **Ambiguous line numbers**: Line numbers refer to rendered output, not source markdown
4. **Hidden dependencies**: Can see `depends_on_previous: true` but not WHICH examples it depends on
5. **No quick scan**: Can't quickly see "9 out of 10 examples passed" at a glance

### What We Have Now
Looking at current data structure:

**Extraction Output** (`polars_arrow_analysis.json`):
```json
{
  "signatures": [{
    "function": "connect",
    "line": 50,
    "context": "Create & Query LanceDB Table - From Polars DataFrame - Sync API"
  }],
  "examples": [{
    "code": "import lancedb\ndb = lancedb.connect(uri)",
    "line": 15,
    "context": "Create & Query LanceDB Table - From Polars DataFrame - Sync API"
  }]
}
```

**Code Validation Output** (`polars_arrow_validation.json`):
```json
{
  "results": [{
    "example_index": 2,
    "line": 32,
    "code": "...",
    "status": "success",
    "depends_on_previous": true  // ← boolean, not specific indices
  }]
}
```

**API Validation Output** (`polars_arrow_analysis_validation.json`):
```json
{
  "validations": [{
    "function": "connect",
    "documented": {
      "line": 50,
      "context": "Create & Query LanceDB Table - From Polars DataFrame - Sync API"
    }
  }]
}
```

### What's Missing
1. **Section hierarchy**: Just "context" string, not structured breadcrumbs
2. **Dependency indices**: Only boolean `depends_on_previous`, not `[0, 2]`
3. **Executable code tracking**: Don't save what was actually executed (merged dependencies)
4. **Markdown anchors**: No `#section-id` for URL linking
5. **Code block index**: Don't know if this is the 1st, 2nd, or 3rd code block in a section

## Proposed Solution: Inline Annotations + Click-to-Navigate

### Visual Design - Before & After

#### BEFORE (Current UI)
```
┌─────────────────────────┬─────────────────────────┐
│ Documentation           │ Validation Results      │
├─────────────────────────┼─────────────────────────┤
│ ## Polars               │ ✅ Example 0 - Line 15  │
│                         │    Status: success      │
│ ```py                   │                         │
│ import lancedb          │ ✅ Example 2 - Line 32  │
│ db = lancedb.connect()  │    Status: success      │
│ ```                     │    Depends on: previous │
│                         │                         │
│ ```py                   │ ❌ Example 9 - Line 124 │
│ table = db.create_...   │    Status: failure      │
│ ```                     │    Error: TypeError...  │
│                         │                         │
│ User must mentally map  │                         │
│ "Example 2, line 32" ←→ │                         │
│ to the actual code block│                         │
└─────────────────────────┴─────────────────────────┘
```

#### AFTER (New UI with Inline Annotations)
```
┌──────────────────────────────────────────────────────┐
│ Documentation Viewer with Inline Validation Status   │
├──────────────────────────────────────────────────────┤
│ ## Polars                                            │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ ✅ CODE VALIDATED                              │  │ ← Green border
│ │ ```py                                          │  │
│ │ import lancedb                                 │  │
│ │ db = lancedb.connect(uri)                      │  │
│ │ ```                                            │  │
│ │                                                │  │
│ │ 📊 Validation: SUCCESS  📍 Line 15             │  │
│ │ 💚 9/10 examples passed in this doc            │  │
│ │ [View Details →]  [View in Validation Tab →]  │  │ ← Clickable
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ ✅ CODE VALIDATED (depends on example above)   │  │
│ │ ```py                                          │  │
│ │ table = db.create_table("pl_table", data)     │  │
│ │ ```                                            │  │
│ │                                                │  │
│ │ 📊 Validation: SUCCESS  📍 Line 32             │  │
│ │ 🔗 Depends on: Example 0 ↑                     │  │ ← Clickable link
│ │ [View Details →]                               │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ...                                                  │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ ❌ VALIDATION FAILED                           │  │ ← Red border
│ │ ```py                                          │  │
│ │ print(ldf.first().collect())                   │  │
│ │ ```                                            │  │
│ │                                                │  │
│ │ 📊 Validation: FAILED  📍 Line 124             │  │
│ │ 🔗 Depends on: Example 8 ↑                     │  │
│ │ ⚠️ TypeError: _scan_pyarrow_dataset_impl()     │  │
│ │    got multiple values for argument...         │  │
│ │ [View Full Error →]  [View Fix Suggestion →]  │  │ ← Expandable
│ └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### User Flow
1. **User opens a document** → See all code blocks color-coded (green/red/gray borders)
2. **User sees failed example** → Red border immediately visible inline
3. **User clicks "View Details"** → Expandable section shows:
   - Full error message
   - Which examples it depends on (clickable links to scroll to them)
   - Fix suggestions from Claude
   - Link to switch to full validation tab
4. **User clicks "Depends on: Example 0"** → Auto-scrolls to Example 0 and highlights it
5. **User clicks "View in Validation Tab"** → Switches to Code Examples tab, scrolls to that result

## Implementation Plan

### Phase 1: Backend - Capture Richer Metadata

#### 1.1 Update Extraction Agent (`stackbench/agents/extraction_agent.py`)

**Update the extraction prompt to capture:**

```python
ENHANCED_EXTRACTION_PROMPT = """
...

For each API signature, capture:
- function: Function name
- params: Parameter names
- line: Line number in the markdown file
- context: Section context
- section_hierarchy: Array of heading hierarchy, e.g., ["Create & Query LanceDB Table", "From Polars DataFrame", "Sync API"]
- markdown_anchor: The heading ID/anchor, e.g., "#from-polars-dataframe"
- code_block_index: Which code block within this section (0, 1, 2...)

For each code example, capture:
- code: The code text
- line: Line number in markdown
- context: Section context
- section_hierarchy: Array of heading hierarchy
- markdown_anchor: The heading ID/anchor
- code_block_index: Which code block within this section
- snippet_source: If this came from --8<-- snippet, note the source like "test_python.py:import-lancedb"

Response format:
{
  "signatures": [{
    "function": "connect",
    "params": ["uri"],
    "line": 50,
    "context": "Create & Query LanceDB Table - From Polars DataFrame - Sync API",
    "section_hierarchy": ["Create & Query LanceDB Table", "From Polars DataFrame", "Sync API"],
    "markdown_anchor": "#from-polars-dataframe",
    "code_block_index": 0
  }],
  "examples": [{
    "code": "import lancedb...",
    "line": 15,
    "context": "...",
    "section_hierarchy": ["Create & Query LanceDB Table", "From Polars DataFrame", "Sync API"],
    "markdown_anchor": "#from-polars-dataframe",
    "code_block_index": 1,
    "snippet_source": null
  }]
}
"""
```

#### 1.2 Update Code Validation Agent (`stackbench/agents/code_example_validation_agent.py`)

**Update the validation prompt to capture dependency details:**

```python
ENHANCED_VALIDATION_PROMPT = """
Validate the following code examples from documentation.

Examples to validate:
{examples_json}

For each example, determine:
1. Whether it can run standalone or depends on previous examples
2. If dependent, WHICH example indices it depends on (e.g., [0, 2])
3. Generate the FULL EXECUTABLE CODE (with all dependencies merged if needed)

Response format:
[
  {
    "example_index": 0,
    "status": "success",
    "error_message": null,
    "execution_output": "...",
    "depends_on_previous": false,
    "depends_on_example_indices": [],
    "actual_code_executed": "import lancedb\ndb = lancedb.connect(uri)"
  },
  {
    "example_index": 2,
    "status": "success",
    "depends_on_previous": true,
    "depends_on_example_indices": [0],
    "actual_code_executed": "import lancedb\ndb = lancedb.connect(uri)\nimport polars as pl\ndata = pl.DataFrame(...)\ntable = db.create_table('pl_table', data=data)"
  }
]
```

#### 1.3 Update Schemas (`stackbench/schemas/extraction.py` and `stackbench/schemas/validation.py`)

**Add to `APISignature`:**
```python
class APISignature(BaseModel):
    # ... existing fields ...
    line: int
    context: str

    # NEW FIELDS
    section_hierarchy: List[str] = Field(default_factory=list)
    markdown_anchor: Optional[str] = None
    code_block_index: int = 0
```

**Add to `CodeExample`:**
```python
class CodeExample(BaseModel):
    # ... existing fields ...
    line: int
    context: str

    # NEW FIELDS
    section_hierarchy: List[str] = Field(default_factory=list)
    markdown_anchor: Optional[str] = None
    code_block_index: int = 0
    snippet_source: Optional[str] = None
```

**Add to `ExampleValidationResult`:**
```python
class ExampleValidationResult(BaseModel):
    # ... existing fields ...
    depends_on_previous: bool = False

    # NEW FIELDS
    depends_on_example_indices: List[int] = Field(default_factory=list)
    actual_code_executed: Optional[str] = None
```

### Phase 2: Frontend - Render Inline Annotations

#### 2.1 Enhanced MarkdownViewer Component (`frontend/src/components/MarkdownViewer.tsx`)

**Key Changes:**
1. Accept validation data as props
2. Match code blocks to validation results by line number
3. Wrap code blocks in annotated containers
4. Add status badges, borders, and expandable details

**New Component Structure:**
```tsx
interface MarkdownViewerProps {
  content: string;
  baseImagePath?: string;

  // NEW PROPS
  apiValidation?: CCAPISignatureValidationOutput | null;
  codeValidation?: CCCodeExampleValidationOutput | null;
  onExampleClick?: (exampleIndex: number) => void; // For scrolling between examples
  onViewInValidationTab?: (exampleIndex: number) => void; // Switch to validation tab
}

export function MarkdownViewer({
  content,
  baseImagePath,
  apiValidation,
  codeValidation,
  onExampleClick,
  onViewInValidationTab
}: MarkdownViewerProps) {

  // Build a map: line number -> validation result
  const validationMap = useMemo(() => {
    const map = new Map();
    codeValidation?.results.forEach(result => {
      map.set(result.line, result);
    });
    return map;
  }, [codeValidation]);

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown
        components={{
          // Enhanced code block renderer
          code: ({ node, inline, className, children, ...props }) => {
            if (inline) {
              return <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>{children}</code>;
            }

            // Get line number from position
            const lineNumber = getLineNumber(node);
            const validation = validationMap.get(lineNumber);

            if (!validation) {
              // No validation data - render normally
              return (
                <code className={`${className} block bg-muted p-3 rounded-md overflow-x-auto`} {...props}>
                  {children}
                </code>
              );
            }

            // Has validation - render with annotation
            return (
              <CodeBlockWithValidation
                code={String(children)}
                className={className}
                validation={validation}
                onDependencyClick={onExampleClick}
                onViewInTab={onViewInValidationTab}
              />
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

#### 2.2 New CodeBlockWithValidation Component

```tsx
interface CodeBlockWithValidationProps {
  code: string;
  className?: string;
  validation: CCExampleValidationResult;
  onDependencyClick?: (exampleIndex: number) => void;
  onViewInTab?: (exampleIndex: number) => void;
}

function CodeBlockWithValidation({
  code,
  className,
  validation,
  onDependencyClick,
  onViewInTab
}: CodeBlockWithValidationProps) {
  const [expanded, setExpanded] = useState(false);

  const borderColor =
    validation.status === 'success' ? 'border-green-500' :
    validation.status === 'failure' ? 'border-red-500' :
    'border-gray-400';

  const bgColor =
    validation.status === 'success' ? 'bg-green-50/30' :
    validation.status === 'failure' ? 'bg-red-50/30' :
    'bg-gray-50/30';

  return (
    <div className={`rounded-lg border-2 ${borderColor} ${bgColor} p-4 my-4`}>
      {/* Status Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {validation.status === 'success' ? (
            <CheckCircle2 className="h-5 w-5 text-green-600" />
          ) : (
            <XCircle className="h-5 w-5 text-red-600" />
          )}
          <span className="font-semibold">
            {validation.status === 'success' ? 'CODE VALIDATED' : 'VALIDATION FAILED'}
          </span>
          {validation.depends_on_previous && (
            <span className="text-xs text-muted-foreground">
              (depends on example above)
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          📍 Line {validation.line}
        </span>
      </div>

      {/* Code Block */}
      <pre className={`${className} bg-muted p-3 rounded-md overflow-x-auto mb-3`}>
        <code>{code}</code>
      </pre>

      {/* Validation Info */}
      <div className="space-y-2">
        <div className="flex items-center gap-4 text-sm">
          <span className={`font-medium ${validation.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
            📊 Validation: {validation.status.toUpperCase()}
          </span>

          {/* Dependency Links */}
          {validation.depends_on_example_indices && validation.depends_on_example_indices.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">🔗 Depends on:</span>
              {validation.depends_on_example_indices.map(idx => (
                <button
                  key={idx}
                  onClick={() => onDependencyClick?.(idx)}
                  className="text-xs text-primary hover:underline"
                >
                  Example {idx} ↑
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Error Preview (if failed) */}
        {validation.status === 'failure' && validation.error_message && (
          <div className="bg-red-100 border border-red-300 rounded p-2 text-sm">
            <div className="font-medium text-red-900">⚠️ Error:</div>
            <div className="text-red-800 font-mono text-xs mt-1">
              {validation.error_message.split('\n').slice(0, 2).join('\n')}
              {validation.error_message.split('\n').length > 2 && '...'}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-3 py-1 bg-background border rounded hover:bg-accent"
          >
            {expanded ? 'Hide' : 'View'} Details →
          </button>

          <button
            onClick={() => onViewInTab?.(validation.example_index)}
            className="text-xs px-3 py-1 bg-background border rounded hover:bg-accent"
          >
            View in Validation Tab →
          </button>
        </div>

        {/* Expandable Details */}
        {expanded && (
          <div className="mt-3 space-y-2 bg-background p-3 rounded border">
            {/* Full Error */}
            {validation.error_message && (
              <div>
                <div className="text-xs font-medium mb-1">Full Error:</div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                  {validation.error_message}
                </pre>
              </div>
            )}

            {/* Execution Output */}
            {validation.execution_output && (
              <div>
                <div className="text-xs font-medium mb-1">Output:</div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                  {validation.execution_output}
                </pre>
              </div>
            )}

            {/* Suggestions */}
            {validation.suggestions && (
              <div>
                <div className="text-xs font-medium mb-1">💡 Suggestions:</div>
                <div className="text-xs">{validation.suggestions}</div>
              </div>
            )}

            {/* Actual Code Executed (if different) */}
            {validation.actual_code_executed && validation.actual_code_executed !== code && (
              <div>
                <div className="text-xs font-medium mb-1">
                  ⚙️ Actual Code Executed (with dependencies):
                </div>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                  <code>{validation.actual_code_executed}</code>
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

#### 2.3 Update App.tsx to Wire Everything Together

```tsx
// In App.tsx - Pass validation data to MarkdownViewer

const handleExampleClick = (exampleIndex: number) => {
  // Scroll to the example with this index
  const element = document.querySelector(`[data-example-index="${exampleIndex}"]`);
  element?.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Highlight briefly
  element?.classList.add('ring-2', 'ring-primary');
  setTimeout(() => element?.classList.remove('ring-2', 'ring-primary'), 2000);
};

const handleViewInValidationTab = (exampleIndex: number) => {
  // Switch to code validation tab
  setActiveTab('cc-code-ex');

  // Scroll to result
  setTimeout(() => {
    const element = document.querySelector(`[data-result-index="${exampleIndex}"]`);
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);
};

// Update the MarkdownViewer usage:
<MarkdownViewer
  content={docContent}
  baseImagePath={...}
  apiValidation={ccApiSigValidation}
  codeValidation={ccCodeExValidation}
  onExampleClick={handleExampleClick}
  onViewInValidationTab={handleViewInValidationTab}
/>
```

### Phase 3: Additional Enhancements

#### 3.1 Document Summary Badge

Add at top of document viewer:

```tsx
// Show overall validation health
{ccCodeExValidation && (
  <div className="mb-4 p-3 bg-muted rounded-lg flex items-center gap-3">
    <div className="flex items-center gap-2">
      {ccCodeExValidation.successful > 0 && (
        <span className="text-green-600 font-semibold">
          ✅ {ccCodeExValidation.successful} passed
        </span>
      )}
      {ccCodeExValidation.failed > 0 && (
        <span className="text-red-600 font-semibold">
          ❌ {ccCodeExValidation.failed} failed
        </span>
      )}
      {ccCodeExValidation.skipped > 0 && (
        <span className="text-gray-600">
          ⏭️ {ccCodeExValidation.skipped} skipped
        </span>
      )}
    </div>
    <div className="text-xs text-muted-foreground">
      {ccCodeExValidation.total_examples} total examples
    </div>
  </div>
)}
```

#### 3.2 Dependency Graph Visualization (Optional - Future Enhancement)

For documents with many dependent examples, show a flow diagram:

```
Example 0 (connect) ──→ Example 2 (create_table) ──→ Example 4 (search)
                                                  └──→ Example 6 (pydantic)
```

## Implementation Order

1. ✅ **Phase 1.3**: Update schemas first (add new fields)
2. ✅ **Phase 1.1**: Update extraction agent prompt (capture metadata)
3. ✅ **Phase 1.2**: Update code validation agent prompt (capture dependencies)
4. ✅ **Phase 2.1 & 2.2**: Create CodeBlockWithValidation component
5. ✅ **Phase 2.3**: Wire up in App.tsx
6. ✅ **Phase 3.1**: Add document summary badge
7. 🔮 **Phase 3.2**: (Optional) Dependency graph visualization

## Testing Plan

1. **Backend Testing**:
   - Run extraction on `polars_arrow.md` → verify `section_hierarchy`, `markdown_anchor`, `code_block_index` are populated
   - Run code validation → verify `depends_on_example_indices` and `actual_code_executed` are captured

2. **Frontend Testing**:
   - Load document with validation data
   - Verify green/red borders appear on code blocks
   - Click "View Details" → verify expansion works
   - Click "Depends on Example 0" → verify scroll to Example 0
   - Click "View in Validation Tab" → verify tab switch and scroll

3. **Edge Cases**:
   - Document with no code examples
   - Document with all passing examples
   - Document with all failing examples
   - Code block with no validation data (should render normally)

## Expected Result

After implementation, users will:

✅ **See validation status immediately** - Green/red borders on code blocks
✅ **Understand dependencies** - "Depends on Example 0" with clickable link
✅ **View errors inline** - No tab switching needed to see what failed
✅ **Get actionable feedback** - Suggestions and fix recommendations
✅ **Navigate efficiently** - Click to scroll between related examples
✅ **Track progress** - "9/10 examples passed" badge at top

## Files to Modify

### Backend (Python)
- `stackbench/schemas/extraction.py` - Add new fields to APISignature, CodeExample
- `stackbench/schemas/validation.py` - Add new fields to ExampleValidationResult
- `stackbench/agents/extraction_agent.py` - Update prompt for metadata capture
- `stackbench/agents/code_example_validation_agent.py` - Update prompt for dependency tracking

### Frontend (React/TypeScript)
- `frontend/src/types/index.ts` - Update interfaces to match new schema fields
- `frontend/src/components/MarkdownViewer.tsx` - Accept validation props, render annotations
- `frontend/src/components/CodeBlockWithValidation.tsx` - **NEW FILE** - Annotated code block component
- `frontend/src/App.tsx` - Wire up click handlers, pass validation data

## Estimated Effort

- Backend changes: **2-3 hours** (schema updates, prompt engineering, testing)
- Frontend component: **3-4 hours** (CodeBlockWithValidation, styling, interactions)
- Integration & testing: **1-2 hours** (wire up App.tsx, test flows)

**Total: 6-9 hours**

## Success Metrics

After implementation:
- ✅ User can see validation status without switching tabs
- ✅ User can click to navigate between dependent examples
- ✅ User can expand/collapse error details inline
- ✅ User can see overall validation health (X/Y passed)
- ✅ All validation metadata is preserved and accessible
