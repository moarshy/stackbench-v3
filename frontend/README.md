# StackBench Documentation Validator Frontend

A React + TypeScript frontend for viewing and validating API documentation against source code.

## Features

- 📄 **Documentation Viewer**: Browse markdown documentation files
- 🔍 **Extraction Results**: View API signatures and code examples extracted from docs
- ✅ **AST Validation**: See validation results comparing docs against actual source code
- 🎨 **Beautiful UI**: Built with Tailwind CSS and shadcn/ui components
- ⚡ **Fast**: Powered by Vite and Bun

## Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Bun** - Runtime and package manager
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Bun installed (`curl -fsSL https://bun.sh/install | bash`)

### Installation

```bash
bun install
```

### Development

```bash
bun dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Build

```bash
bun run build
```

### Preview Production Build

```bash
bun preview
```

## Project Structure

```
src/
├── components/     # React components
├── lib/            # Utility functions
├── types/          # TypeScript type definitions
├── App.tsx         # Main application component
├── main.tsx        # Application entry point
└── index.css       # Global styles
```

## Data Structure

The frontend expects data from two sources:

1. **Extraction Output** (`../cc-agents/extraction_output/*.json`)
   - API signatures extracted from documentation
   - Code examples
   - Metadata

2. **Validation Output** (`../cc-agents/ast_validation_output/*.json`)
   - AST-based validation results
   - Parameter mismatches
   - Accuracy scores
   - Suggested fixes

## Future Enhancements

- [ ] Real-time data loading from file system or API
- [ ] Markdown rendering for documentation
- [ ] Syntax highlighting for code examples
- [ ] Filtering and search functionality
- [ ] Export validation reports
- [ ] Dark mode toggle
- [ ] Interactive signature comparison view

## License

MIT
