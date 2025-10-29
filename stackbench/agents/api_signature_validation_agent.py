"""
API Signature Validation Agent - Validates documented API signatures against actual library implementations.

This agent uses Claude Code to:
1. Install the library with the exact version from docs
2. Use Python introspection (inspect module) to get actual signatures
3. Compare documented vs actual signatures
4. Report mismatches with actionable suggestions

Built from first principles following the extraction_agent pattern.
"""

import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Import centralized schemas
from stackbench.schemas import (
    APISignatureValidationOutput,
    SignatureValidation,
    DocumentedSignature,
    ActualSignature,
    ValidationIssue,
    ValidationSummary,
    EnvironmentInfo
)


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

VALIDATION_SYSTEM_PROMPT = """You are an expert code introspection specialist for Python, JavaScript, and TypeScript.

Your task is to validate documented API signatures against actual library implementations using language-specific introspection tools.

Core capabilities:
1. **Python**: Use `inspect.signature()` and `inspect.getfullargspec()` for introspection
2. **JavaScript/TypeScript**: Use runtime imports, JSDoc parsing, or TypeScript compiler API for type info
3. Handle method chains by introspecting return types
4. Compare documented vs actual parameters, types, defaults
5. Categorize issues by severity (critical, warning, info)

Validation approach and status determination:
- **Status = "valid"**: Documentation shows all required parameters correctly, even if optional parameters are omitted (this is acceptable for introductory/example docs)
- **Status = "invalid"**: Documentation has critical errors that would prevent the code from working
- **Status = "not_found"**: API doesn't exist in the library

Issue severity guidelines:
- **Critical**: Missing required parameters, wrong parameter names, incorrect required param types, API doesn't exist
- **Warning**: Type mismatches in optional parameters, outdated default values for documented params
- **Info**: Optional parameters not shown in docs (acceptable for simplified examples/tutorials)

IMPORTANT: Missing optional parameters in documentation is NOT a reason to mark status as "invalid".
Documentation can be simplified for educational purposes. Only mark as "invalid" if there are critical issues.

Always be thorough and precise. Use language-specific introspection as the source of truth."""

VALIDATION_PROMPT = """Validate all API signatures from this documentation against the actual library.

Library: {library}
Version: {version}
Language: {language}
Document: {document_page}

Signatures to validate:
{signatures_json}

TASK:
1. Install the library using the appropriate package manager:
   - **Python**: `pip install {library}=={version}`
   - **JavaScript/TypeScript**: `npm install {library}@{version}` or `yarn add {library}@{version}`

2. For each signature:
   a. Import the library and locate the function/method
   b. For method chains (e.g., "client.connect"):
      - First get the object type returned by the parent method
      - Then introspect the method on that type

   c. Use language-specific introspection:

   **Python**:
   ```python
   import inspect
   sig = inspect.signature(function_or_method)
   spec = inspect.getfullargspec(function_or_method)
   # Get params, types, defaults, required vs optional
   ```

   **JavaScript/TypeScript**:
   ```javascript
   // Runtime introspection
   const func = require('{library}').functionName;
   console.log(func.length); // number of parameters
   console.log(func.toString()); // function source

   // For TypeScript: parse .d.ts files or use ts compiler API
   ```

   d. Compare documented vs actual:
      - Parameter names (order matters for positional)
      - Parameter types (if documented)
      - Default values (for params shown in docs)
      - Required vs optional parameters

   e. Determine status:
      **STATUS = "valid"** if:
      - All required parameters are documented correctly
      - All documented parameters exist and match (names, types, defaults)
      - Optional parameters may be omitted from docs (this is acceptable)

      **STATUS = "invalid"** if:
      - Missing required parameters
      - Wrong parameter names
      - Incorrect types/defaults for documented parameters
      - Has critical severity issues

      **STATUS = "not_found"** if:
      - API doesn't exist in the library

   f. Identify issues with appropriate severity:
      - **CRITICAL**: API not found, missing required params, wrong param names for required params, incorrect required param types
      - **WARNING**: Type hint differences for optional params, incorrect default values for documented params
      - **INFO**: Optional parameters not shown in docs (note: this is acceptable and should NOT make status "invalid")

3. Also get environment info based on language:
   - **Python**: `pip show {library}` + `python --version`
   - **JavaScript/TypeScript**: `npm list {library}` + `node --version`

IMPORTANT STATUS RULES:
- Missing optional parameters in docs should be "info" severity and status should still be "valid"
- Only mark as "invalid" if there are critical errors that would break user code
- Documentation can be simplified for tutorials/examples - this is acceptable practice

CRITICAL: Respond with ONLY the JSON object below. No explanatory text before or after. Just the JSON.

RESPONSE FORMAT - JSON ONLY:

```json
{{
  "environment": {{
    "library_installed": "{library}",
    "version_installed": "x.y.z",
    "version_requested": "{version}",
    "version_match": true,
    "runtime_version": "Python 3.x.y OR Node.js vX.Y.Z",
    "installation_output": "Installation command output..."
  }},
  "validations": [
    {{
      "signature_id": "{library}.function_name",
      "function": "function_name",
      "method_chain": "object.method" or null,
      "status": "valid|invalid|not_found|error",
      "actual": {{
        "params": ["param1", "param2"],
        "param_types": {{"param1": "str|string", "param2": "Optional[int]|number|undefined"}},
        "defaults": {{"param2": "None|null|undefined"}},
        "required_params": ["param1"],
        "optional_params": ["param2"],
        "return_type": "Database|Promise<Database>|object",
        "is_async": false,
        "is_method": false,
        "verified_by": "inspect.signature|runtime|typescript-compiler"
      }},
      "issues": [
        {{
          "type": "missing_param_in_docs",
          "severity": "warning",
          "message": "Documented signature missing optional parameter 'param2'",
          "suggested_fix": "Python: function(param1, param2=None) | JS/TS: function(param1, param2 = null)"
        }}
      ],
      "confidence": 0.9
    }}
  ]
}}
```

IMPORTANT:
- Use language-specific introspection (Python: inspect module | JS/TS: runtime/compiler API)
- Be thorough - check every parameter, type, and default
- Provide clear, actionable suggestions for fixing documentation
- Handle edge cases: async functions, class methods, properties, method chains, Promises
- If a signature is correct, status="valid" with empty issues array
"""


# ============================================================================
# VALIDATION AGENT
# ============================================================================

class APISignatureValidationAgent:
    """Agent that validates API signatures using Claude Code and Python introspection."""

    def __init__(
        self,
        extraction_folder: Path,
        output_folder: Path,
        num_workers: int = 5,
        validation_log_dir: Optional[Path] = None
    ):
        """
        Initialize the validation agent.

        Args:
            extraction_folder: Path to extraction output folder
            output_folder: Path to save validation results
            num_workers: Number of parallel workers for validation (default: 5)
            validation_log_dir: Optional directory for validation hook tracking logs
        """
        self.extraction_folder = Path(extraction_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.num_workers = num_workers
        self.validation_log_dir = Path(validation_log_dir) if validation_log_dir else None

        print(f"👷 API Validation Workers: {self.num_workers}")

        # Note: We don't create a global logger here anymore - we create one per document
        # This allows us to have separate log files for each document
        if self.validation_log_dir:
            print(f"📋 Per-document logging enabled")
            print(f"   Logs will be saved to: {self.validation_log_dir}/api_signature_logs/")

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Claude's response, handling markdown code blocks and explanatory text."""
        try:
            # Strategy 1: Try to find JSON in markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
                return json.loads(json_text)
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
                return json.loads(json_text)

            # Strategy 2: Look for JSON object markers { }
            # Find the first { and try to parse from there
            start_idx = response_text.find('{')
            if start_idx != -1:
                # Try to parse from this point
                try:
                    # Find matching closing brace by counting
                    brace_count = 0
                    in_string = False
                    escape_next = False

                    for i in range(start_idx, len(response_text)):
                        char = response_text[i]

                        if escape_next:
                            escape_next = False
                            continue

                        if char == '\\':
                            escape_next = True
                            continue

                        if char == '"':
                            in_string = not in_string
                            continue

                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    # Found complete JSON object
                                    json_text = response_text[start_idx:i+1]
                                    return json.loads(json_text)

                except Exception:
                    pass

            # Strategy 3: Try parsing the whole response
            return json.loads(response_text.strip())

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            # Try to show where the JSON might be
            if '{' in response_text:
                json_start = response_text.find('{')
                print(f"   Found '{{' at position {json_start}")
                print(f"   Context: ...{response_text[max(0, json_start-50):json_start+100]}...")
            return None

    async def get_claude_response(self, client: ClaudeSDKClient, prompt: str, logger=None, messages_log_file=None) -> str:
        """Send prompt to Claude and get text response, logging all messages."""
        # Log the user prompt
        if messages_log_file:
            user_message_entry = {
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": prompt
            }
            with open(messages_log_file, 'a') as f:
                f.write(json.dumps(user_message_entry) + '\n')

        await client.query(prompt)

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                # Log the full assistant message
                if messages_log_file:
                    # Convert message blocks to serializable format
                    message_content = []
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            message_content.append({
                                "type": "text",
                                "text": block.text
                            })
                            response_text += block.text
                        else:
                            # Handle other block types
                            message_content.append({
                                "type": type(block).__name__,
                                "data": str(block)
                            })

                    assistant_message_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "role": "assistant",
                        "content": message_content
                    }
                    with open(messages_log_file, 'a') as f:
                        f.write(json.dumps(assistant_message_entry) + '\n')
                else:
                    # Original behavior when no logger
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

        return response_text

    def format_signatures_for_prompt(self, signatures: List[Dict]) -> str:
        """Format signatures as JSON for the prompt."""
        formatted = []
        for sig in signatures:
            formatted.append({
                "function": sig.get("function", ""),
                "method_chain": sig.get("method_chain"),
                "params": sig.get("params", []),
                "param_types": sig.get("param_types", {}),
                "defaults": sig.get("defaults", {}),
                "imports": sig.get("imports", ""),
                "raw_code": sig.get("raw_code", ""),
                "line": sig.get("line", 0),
                "context": sig.get("context", "")
            })
        return json.dumps(formatted, indent=2)

    async def validate_document(self, extraction_file: Path) -> APISignatureValidationOutput:
        """
        Validate all signatures in a document.

        Args:
            extraction_file: Path to extraction JSON file

        Returns:
            APISignatureValidationOutput with all validation results
        """
        start_time = datetime.now()

        # Read extraction data
        with open(extraction_file, 'r', encoding='utf-8') as f:
            extraction_data = json.load(f)

        document_page = extraction_data.get("page", "unknown")
        library = extraction_data.get("library", "unknown")
        version = extraction_data.get("version", "latest")
        language = extraction_data.get("language", "python")
        signatures = extraction_data.get("signatures", [])

        warnings = []

        # Create per-document logger with new directory structure
        from stackbench.hooks import create_agent_hooks, AgentLogger

        messages_log_file = None
        if self.validation_log_dir:
            doc_stem = extraction_file.stem.replace('_analysis', '')
            # New structure: logs/api_signature_logs/<doc_name>/
            api_logs_dir = self.validation_log_dir / "api_signature_logs" / doc_stem
            api_logs_dir.mkdir(parents=True, exist_ok=True)

            agent_log = api_logs_dir / "agent.log"
            tools_log = api_logs_dir / "tools.jsonl"
            messages_log_file = api_logs_dir / "messages.jsonl"
            logger = AgentLogger(agent_log, tools_log)
        else:
            logger = None

        # Create hooks for this document
        hooks = create_agent_hooks(
            agent_type="api_validation",
            logger=logger,
            output_dir=self.output_folder,
            validation_log_dir=self.validation_log_dir
        )

        # Create options with per-document hooks
        options = ClaudeAgentOptions(
            system_prompt=VALIDATION_SYSTEM_PROMPT,
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode="acceptEdits",
            hooks=hooks,
            cwd=str(Path.cwd())
        )

        if not signatures:
            # Log early return decision
            if messages_log_file:
                early_return_message = {
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "content": [{
                        "type": "text",
                        "text": f"Document '{document_page}' has 0 API signatures. Skipping Claude invocation and returning empty validation result."
                    }]
                }
                with open(messages_log_file, 'w') as f:
                    f.write(json.dumps(early_return_message) + '\n')

            # Return empty result
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return APISignatureValidationOutput(
                validation_id=str(uuid.uuid4()),
                validated_at=datetime.now().isoformat(),
                source_file=extraction_file.name,
                document_page=document_page,
                library=library,
                version=version,
                language=language,
                summary=ValidationSummary(
                    total_signatures=0,
                    valid=0,
                    invalid=0,
                    not_found=0,
                    error=0,
                    accuracy_score=0.0,
                    critical_issues=0,
                    warnings=0
                ),
                validations=[],
                environment=EnvironmentInfo(
                    library_installed=library,
                    version_installed="unknown",
                    version_requested=version,
                    version_match=False,
                    runtime_version="unknown"
                ),
                processing_time_ms=processing_time,
                warnings=["No signatures to validate"]
            )

        # Ask Claude to validate all signatures
        async with ClaudeSDKClient(options=options) as client:
            signatures_json = self.format_signatures_for_prompt(signatures)
            prompt = VALIDATION_PROMPT.format(
                library=library,
                version=version,
                language=language,
                document_page=document_page,
                signatures_json=signatures_json
            )

            response_text = await self.get_claude_response(client, prompt, logger, messages_log_file)
            validation_data = self.extract_json_from_response(response_text)

            if not validation_data:
                warnings.append("Failed to parse validation response from Claude")
                # Return error result
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return APISignatureValidationOutput(
                    validation_id=str(uuid.uuid4()),
                    validated_at=datetime.now().isoformat(),
                    source_file=extraction_file.name,
                    document_page=document_page,
                    library=library,
                    version=version,
                    language=language,
                    summary=ValidationSummary(
                        total_signatures=len(signatures),
                        valid=0,
                        invalid=0,
                        not_found=0,
                        error=len(signatures),
                        accuracy_score=0.0,
                        critical_issues=0,
                        warnings=0
                    ),
                    validations=[],
                    environment=EnvironmentInfo(
                        library_installed=library,
                        version_installed="unknown",
                        version_requested=version,
                        version_match=False,
                        runtime_version="unknown"
                    ),
                    processing_time_ms=processing_time,
                    warnings=warnings
                )

            # Parse environment info
            env_data = validation_data.get("environment", {})
            environment = EnvironmentInfo(
                library_installed=env_data.get("library_installed", library),
                version_installed=env_data.get("version_installed", "unknown"),
                version_requested=env_data.get("version_requested", version),
                version_match=env_data.get("version_match", False),
                runtime_version=env_data.get("runtime_version", "unknown"),
                installation_output=env_data.get("installation_output")
            )

            # Parse validations
            validations = []
            for i, val_data in enumerate(validation_data.get("validations", [])):
                sig = signatures[i] if i < len(signatures) else {}

                # Create DocumentedSignature
                documented = DocumentedSignature(
                    params=sig.get("params", []),
                    param_types=sig.get("param_types", {}),
                    defaults=sig.get("defaults", {}),
                    imports=sig.get("imports") or "",
                    raw_code=sig.get("raw_code") or "",
                    line=sig.get("line", 0),
                    context=sig.get("context") or ""
                )

                # Create ActualSignature if available
                actual = None
                if val_data.get("actual"):
                    actual_data = val_data["actual"]
                    actual = ActualSignature(
                        params=actual_data.get("params", []),
                        param_types=actual_data.get("param_types", {}),
                        defaults=actual_data.get("defaults", {}),
                        required_params=actual_data.get("required_params", []),
                        optional_params=actual_data.get("optional_params", []),
                        return_type=actual_data.get("return_type"),
                        is_async=actual_data.get("is_async", False),
                        is_method=actual_data.get("is_method", False),
                        verified_by=actual_data.get("verified_by", "inspect.signature")
                    )

                # Parse issues
                issues = [
                    ValidationIssue(
                        type=issue.get("type", "unknown"),
                        severity=issue.get("severity", "warning"),
                        message=issue.get("message", ""),
                        suggested_fix=issue.get("suggested_fix")
                    )
                    for issue in val_data.get("issues", [])
                ]

                validation = SignatureValidation(
                    signature_id=val_data.get("signature_id", f"{library}.{sig.get('function', 'unknown')}"),
                    function=val_data.get("function", sig.get("function", "unknown")),
                    method_chain=val_data.get("method_chain"),
                    library=library,
                    status=val_data.get("status", "error"),
                    documented=documented,
                    actual=actual,
                    issues=issues,
                    confidence=val_data.get("confidence", 1.0)
                )
                validations.append(validation)

            # Calculate summary statistics
            total = len(validations)
            valid = sum(1 for v in validations if v.status == "valid")
            invalid = sum(1 for v in validations if v.status == "invalid")
            not_found = sum(1 for v in validations if v.status == "not_found")
            error = sum(1 for v in validations if v.status == "error")
            accuracy = valid / total if total > 0 else 0.0
            critical_issues = sum(len([i for i in v.issues if i.severity == "critical"]) for v in validations)
            warning_count = sum(len([i for i in v.issues if i.severity == "warning"]) for v in validations)

            summary = ValidationSummary(
                total_signatures=total,
                valid=valid,
                invalid=invalid,
                not_found=not_found,
                error=error,
                accuracy_score=round(accuracy, 3),
                critical_issues=critical_issues,
                warnings=warning_count
            )

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            validation_output = APISignatureValidationOutput(
                validation_id=str(uuid.uuid4()),
                validated_at=datetime.now().isoformat(),
                source_file=extraction_file.name,
                document_page=document_page,
                library=library,
                version=version,
                language=language,
                summary=summary,
                validations=validations,
                environment=environment,
                processing_time_ms=processing_time,
                warnings=warnings
            )

            # Validate JSON before saving
            from stackbench.hooks import validate_validation_output_json

            validation_dict = json.loads(validation_output.model_dump_json())
            filename = f"{extraction_file.stem}_validation.json"

            passed, errors = validate_validation_output_json(
                validation_dict,
                filename,
                self.validation_log_dir,
                validation_type="api_signature_validation"
            )

            if not passed:
                print(f"⚠️  {extraction_file.stem.replace('_analysis', '')} - API validation failed: {errors[:2] if errors else 'Unknown error'}")

            # Save validation output
            output_file = self.output_folder / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(validation_output.model_dump_json(indent=2))

            return validation_output

    async def _validate_document_with_save(
        self,
        extraction_file: Path,
        semaphore: asyncio.Semaphore,
        progress: Dict[str, int]
    ) -> Optional[APISignatureValidationOutput]:
        """Validate a single document with semaphore control and save results."""
        async with semaphore:
            try:
                validation_output = await self.validate_document(extraction_file)

                # Validate JSON before saving
                from stackbench.hooks import validate_validation_output_json

                validation_dict = json.loads(validation_output.model_dump_json())
                filename = f"{extraction_file.stem}_validation.json"

                passed, errors = validate_validation_output_json(
                    validation_dict,
                    filename,
                    self.validation_log_dir,
                    validation_type="api_signature_validation"
                )

                if not passed:
                    print(f"⚠️  [{progress['completed']+1}/{progress['total']}] {extraction_file.stem.replace('_analysis', '')} - Validation failed: {errors[:2]}")

                # Save validation output
                output_file = self.output_folder / filename
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(validation_output.model_dump_json(indent=2))

                progress['completed'] += 1
                # Show meaningful stats: valid/invalid/not_found
                v = validation_output.summary.valid
                i = validation_output.summary.invalid
                nf = validation_output.summary.not_found
                print(f"✅ [{progress['completed']}/{progress['total']}] {extraction_file.stem.replace('_analysis', '')} - {v} valid, {i} invalid, {nf} not found")

                return validation_output

            except Exception as e:
                progress['completed'] += 1
                print(f"   ❌ [{progress['completed']}/{progress['total']}] Error processing {extraction_file.name}: {e}")
                import traceback
                traceback.print_exc()
                return None

    async def validate_all_documents(self):
        """Validate all extraction files using parallel workers."""
        # Track overall validation time
        validation_start_time = datetime.now()

        # Find all extraction analysis files
        extraction_files = list(self.extraction_folder.glob("*_analysis.json"))
        extraction_files = [f for f in extraction_files if f.name != "extraction_summary.json"]

        if not extraction_files:
            print(f"❌ No extraction files found in {self.extraction_folder}")
            return

        print(f"🔍 Validating API signatures for {len(extraction_files)} documents ({self.num_workers} workers)")

        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.num_workers)

        # Progress tracking
        progress = {'completed': 0, 'total': len(extraction_files)}
        tasks = [
            self._validate_document_with_save(extraction_file, semaphore, progress)
            for extraction_file in extraction_files
        ]

        results = await asyncio.gather(*tasks)

        # Filter out None results (failed validations)
        results = [r for r in results if r is not None]

        # Calculate validation duration
        validation_end_time = datetime.now()
        validation_duration_seconds = (validation_end_time - validation_start_time).total_seconds()

        # Create overall summary
        total_valid = sum(r.summary.valid for r in results)
        total_invalid = sum(r.summary.invalid for r in results)
        total_not_found = sum(r.summary.not_found for r in results)
        print(f"✅ API validation complete: {total_valid} valid, {total_invalid} invalid, {total_not_found} not found ({validation_duration_seconds:.1f}s)")

        # Save overall summary with timing
        overall_summary = {
            "validation_timestamp": datetime.now().isoformat(),
            "total_documents": len(results),
            "total_signatures": sum(r.summary.total_signatures for r in results),
            "total_valid": sum(r.summary.valid for r in results),
            "total_invalid": sum(r.summary.invalid for r in results),
            "total_not_found": sum(r.summary.not_found for r in results),
            "total_critical_issues": sum(r.summary.critical_issues for r in results),
            "total_warnings": sum(r.summary.warnings for r in results),
            "validation_duration_seconds": round(validation_duration_seconds, 2),
            "num_workers": self.num_workers,
            "documents": [
                {
                    "source_file": r.source_file,
                    "document_page": r.document_page,
                    "library": r.library,
                    "version": r.version,
                    "total_signatures": r.summary.total_signatures,
                    "valid": r.summary.valid,
                    "invalid": r.summary.invalid,
                    "accuracy_score": r.summary.accuracy_score
                }
                for r in results
            ]
        }

        summary_file = self.output_folder / "validation_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, indent=2)

        print(f"💾 Summary saved to {summary_file}")

        return overall_summary


# This module is designed to be used as a library.
# For CLI usage, see stackbench.cli module.
