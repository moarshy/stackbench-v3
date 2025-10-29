import type { Plugin } from 'vite';
import fs from 'fs/promises';
import path from 'path';

/**
 * Extract content between include markers in a file
 * Format: # --8<-- [start:marker-name] ... # --8<-- [end:marker-name]
 */
async function extractInclude(filePath: string, markerName: string): Promise<string | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n');

    const startMarker = `[start:${markerName}]`;
    const endMarker = `[end:${markerName}]`;

    let startIdx = -1;
    let endIdx = -1;

    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(startMarker)) {
        startIdx = i;
      } else if (lines[i].includes(endMarker)) {
        endIdx = i;
        break;
      }
    }

    if (startIdx >= 0 && endIdx > startIdx) {
      // Extract lines between markers (excluding the marker lines themselves)
      return lines.slice(startIdx + 1, endIdx).join('\n');
    }

    return null;
  } catch (error) {
    console.error(`Error extracting include from ${filePath}:`, error);
    return null;
  }
}

/**
 * Resolve --8<-- include markers in markdown content
 * Format: --8<-- "path/to/file.py:marker-name"
 */
async function resolveIncludes(content: string, baseDir: string): Promise<string> {
  const includeRegex = /--8<--\s+"([^"]+)"/g;
  let result = content;

  const matches = [...content.matchAll(includeRegex)];

  for (const match of matches) {
    const [fullMatch, includePath] = match;
    const [filePath, markerName] = includePath.split(':');

    if (filePath && markerName) {
      // Resolve file path relative to base directory
      const fullFilePath = path.join(baseDir, filePath);
      const extracted = await extractInclude(fullFilePath, markerName);

      if (extracted) {
        result = result.replace(fullMatch, extracted);
      }
    }
  }

  return result;
}

/**
 * Vite plugin to serve local file system files via API endpoints
 * This allows the frontend to read extraction output, validation output, and documentation files
 */
export function localFileSystemPlugin(): Plugin {
  return {
    name: 'local-fs-api',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        // API endpoint to get configuration (base data directory path)
        if (req.url === '/api/config') {
          try {
            // Resolve absolute path to data directory
            // Since Vite runs from the frontend folder, we need to go up one level to get to project root
            const frontendDir = process.cwd();
            const projectRoot = path.resolve(frontendDir, '..');
            const dataDir = path.resolve(projectRoot, 'data');

            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({
              baseDataDir: dataDir,
              projectRoot: projectRoot,
              frontendDir: frontendDir
            }));
          } catch (error) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: 'Failed to get config' }));
          }
          return;
        }

        // API endpoint to list files in a directory
        if (req.url?.startsWith('/api/files?')) {
          const url = new URL(req.url, 'http://localhost');
          const dirPath = url.searchParams.get('path');
          const type = url.searchParams.get('type'); // 'dirs' or 'files' (default: both)

          if (!dirPath) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Missing path parameter' }));
            return;
          }

          try {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });

            let results: string[];
            if (type === 'dirs') {
              // Only return directories (for run IDs in data directory)
              results = entries
                .filter(entry => entry.isDirectory())
                .map(entry => entry.name);
            } else if (type === 'files') {
              // Only return files (for extraction results, etc.)
              results = entries
                .filter(entry => entry.isFile())
                .map(entry => entry.name);
            } else {
              // Return both files and directories (default behavior for backward compatibility)
              results = entries.map(entry => entry.name);
            }

            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify(results));
          } catch (error: any) {
            // If directory doesn't exist (ENOENT), return empty array instead of error
            if (error.code === 'ENOENT') {
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify([]));
            } else {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: 'Failed to read directory' }));
            }
          }
          return;
        }

        // API endpoint to read a file
        if (req.url?.startsWith('/api/file?')) {
          const url = new URL(req.url, 'http://localhost');
          const filePath = url.searchParams.get('path');

          if (!filePath) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Missing path parameter' }));
            return;
          }

          try {
            let content = await fs.readFile(filePath, 'utf-8');
            const ext = path.extname(filePath).toLowerCase();

            // Resolve includes for markdown files
            if (ext === '.md') {
              const baseDir = path.dirname(filePath);
              // Go up to repo root (assuming docs are in repo/docs/src/...)
              const repoRoot = path.resolve(baseDir, '../../..');
              content = await resolveIncludes(content, repoRoot);
            }

            // Set appropriate content type
            if (ext === '.json') {
              res.setHeader('Content-Type', 'application/json');
            } else if (ext === '.md') {
              res.setHeader('Content-Type', 'text/markdown');
            } else {
              res.setHeader('Content-Type', 'text/plain');
            }

            res.end(content);
          } catch (error) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: 'File not found' }));
          }
          return;
        }

        next();
      });
    },
  };
}
