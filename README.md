# Stackbench

**Documentation Quality Validation Tool**

Stackbench is a command-line tool that validates the quality of software documentation by:

1. 📝 **Extracting API signatures** and code examples from documentation
2. 🔍 **Validating API signatures** against actual library implementations  
3. ✅ **Testing code examples** by executing them in isolated environments

## Features

- **Automated Validation**: Clone a repository, analyze documentation, and get comprehensive quality reports
- **API Signature Accuracy**: Ensures documented function signatures match the actual library implementation
- **Code Example Testing**: Verifies that code examples in documentation actually work
- **Rich CLI**: Beautiful terminal output with progress bars and formatted results
- **UUID-based Runs**: Each validation run gets a unique identifier for tracking

## Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd stackbench-v3

# Install dependencies with UV
uv sync

# Run stackbench
uv run stackbench --help
```

### Using pip

```bash
# Clone the repository
git clone <your-repo-url>
cd stackbench-v3

# Install in development mode
pip install -e .

# Run stackbench
stackbench --help
```

## Usage

### Basic Example

```bash
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --include-folders docs/src/python \
  --library lancedb \
  --version 0.25.2 \
  --output ./validation-results
```

### Command Options

- `--repo, -r`: Git repository URL (required)
- `--branch, -b`: Git branch to clone (default: main)
- `--include-folders, -i`: Comma-separated list of documentation folders to analyze
- `--library, -l`: Primary library name being documented (required)
- `--version, -v`: Library version to validate against (required)
- `--output, -o`: Output directory (default: ./data)

### Output Structure

Each validation run creates a unique directory structure:

```
data/
└── {run-uuid}/
    ├── repository/           # Cloned repository
    ├── results/
    │   ├── extraction/       # Extracted API signatures and examples
    │   ├── api_validation/   # API signature validation results
    │   └── code_validation/  # Code example validation results
    └── metadata.json         # Run metadata
```

## What It Validates

### 1. API Signature Accuracy

Checks if documented function signatures match the actual implementation:

- ✅ All required parameters documented correctly
- ✅ Parameter types match actual implementation
- ✅ Default values are accurate
- ℹ️  Optional parameters may be omitted from introductory docs (acceptable)

### 2. Code Example Validation

Tests if code examples actually run:

- ✅ Syntax is valid
- ✅ Code executes without errors
- ✅ Dependencies are properly specified
- ✅ Examples work as documented

## Example Output

```
📊 Extraction Results
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Documents          │    15 │
│ API Signatures     │    42 │
│ Code Examples      │    28 │
└────────────────────┴───────┘

🔍 API Signature Validation
┏━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Status   ┃ Count ┃ Percentage ┃
┡━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ Valid    │    40 │      95.2% │
│ Invalid  │     2 │       4.8% │
│ NotFound │     0 │       0.0% │
└──────────┴───────┴────────────┘

📝 Code Example Validation
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Status     ┃ Count ┃ Percentage ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ Successful │    26 │      92.9% │
│ Failed     │     2 │       7.1% │
└────────────┴───────┴────────────┘
```

## Requirements

- Python 3.11+
- UV or pip
- Claude Code CLI (for agent execution)
- Git

## Development

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Format code
uv run ruff format

# Lint code
uv run ruff check
```

## Architecture

Stackbench uses a pipeline architecture with three specialized agents:

1. **Extraction Agent**: Analyzes markdown documentation to extract API signatures and code examples
2. **API Validation Agent**: Uses Python introspection to compare documented vs. actual signatures
3. **Code Validation Agent**: Executes code examples in isolated environments to verify they work

All agents use Claude Code for intelligent analysis and validation.

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
