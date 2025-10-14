# StackBench Frontend

A React-based web interface for viewing Stackbench documentation validation results.

## Overview

The frontend provides an intuitive interface to:
- Browse multiple validation runs by UUID
- View documentation files and their validation results
- Inspect API signature accuracy
- Review code example validation
- Compare validation metrics across runs

## Features

- **Run Selection**: Choose from available validation runs in your data directory
- **Real-time Filtering**: Search and filter documentation files
- **Multi-tab Results**: View extraction, API validation, and code validation in separate tabs
- **Run Metadata**: See run details including repository, timestamps, and status
- **Deep Linking**: Share direct links to specific runs and documents via URL parameters
- **Responsive UI**: Built with TailwindCSS for a clean, modern interface

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Stackbench CLI (run at least one validation first)

### Installation

```bash
cd frontend
bun install  # or npm install
```

### Configuration

The frontend needs to know where your stackbench data directory is located.

1. Click the Settings icon (⚙️) in the header
2. Set the **Base Data Directory** to your stackbench data folder
   - Default: `/Users/arshath/play/naptha/stackbench-v2/stackbench-v3/data`
3. Click "Save & Reload"

### Running the Development Server

```bash
bun run dev  # or npm run dev
```

The frontend will start at `http://localhost:5173`

## Usage

### 1. Run Stackbench CLI

First, generate validation results:

```bash
cd ../  # Go to stackbench-v3 root
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --include-folders docs/src/python \
  --library lancedb \
  --version 0.25.2
```

This creates a run in `data/{run-uuid}/` with all results.

### 2. View Results in Frontend

1. Open `http://localhost:5173`
2. Select your run from the dropdown (it shows repo name and timestamp)
3. Browse documentation files in the sidebar
4. Click a file to see:
   - **Documentation**: Original markdown content
   - **Extraction**: Extracted API signatures and code examples
   - **CC API Signature**: Claude Code validation of API signatures
   - **CC Code Examples**: Claude Code validation of code examples

### 3. Share Results

Copy the URL with query parameters to share specific views:

```
# Link to a specific run
http://localhost:5173?run=api_signature_lancedb_20250114_123456

# Link to a specific document in a run
http://localhost:5173?run=api_signature_lancedb_20250114_123456&doc=basic.md

# Link with a specific tab open
http://localhost:5173?run=api_signature_lancedb_20250114_123456&doc=basic.md&tab=cc-api-sig
```

## Architecture

### Components

- **RunSelector**: Dropdown to select validation runs
- **RunInfo**: Displays current run metadata (repo, status, timestamps)
- **Settings**: Configure base data directory
- **MarkdownViewer**: Renders documentation with syntax highlighting
- **Tabs**: Tab navigation for different result types

### Services

- **APIService**: Handles all file system API calls via Vite plugin
  - Automatically resolves paths based on selected run UUID
  - Loads extraction, validation, and documentation files

### Vite Plugin

A custom Vite plugin (`vite-plugin-local-fs.ts`) provides REST API endpoints:
- `/api/files?path=...` - List files in a directory
- `/api/file?path=...` - Read file contents

This allows the frontend to access local file system during development.

## Data Structure

The frontend expects this directory structure:

```
data/
└── {run-uuid}/
    ├── metadata.json              # Run metadata
    ├── repository/                # Cloned repository
    │   └── docs/                  # Documentation files
    └── results/
        ├── extraction/            # Extracted signatures and examples
        │   └── {doc}_analysis.json
        ├── api_validation/        # API signature validation
        │   └── {doc}_analysis_validation.json
        └── code_validation/       # Code example validation
            └── {doc}_validation.json
```

## Development

### Build for Production

```bash
bun run build
```

### Type Checking

```bash
bunx tsc --noEmit
```

### Linting

```bash
bun run lint
```

## Technologies

- **React 19**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **TailwindCSS**: Styling
- **Lucide React**: Icons
- **React Markdown**: Markdown rendering
- **Bun**: Fast package manager and runtime

## Troubleshooting

### No runs showing up

1. Make sure you've run `stackbench run` at least once
2. Check that Settings → Base Data Directory points to the correct location
3. Verify the data directory contains subdirectories with `metadata.json` files

### Documentation not loading

1. Check browser console for errors
2. Verify the repository was cloned in `data/{run-uuid}/repository/`
3. Ensure extraction files exist in `data/{run-uuid}/results/extraction/`

### Validation results not showing

1. Verify the pipeline completed successfully
2. Check for validation output files in:
   - `results/api_validation/`
   - `results/code_validation/`
3. Look at the run status in the sidebar (should be "completed")

## License

MIT

---

**StackBench Frontend** - View and analyze documentation validation results
