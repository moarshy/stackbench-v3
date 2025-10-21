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
        // API endpoint to list files in a directory
        if (req.url?.startsWith('/api/files?')) {
          const url = new URL(req.url, 'http://localhost');
          const dirPath = url.searchParams.get('path');

          if (!dirPath) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Missing path parameter' }));
            return;
          }

          try {
            const files = await fs.readdir(dirPath);
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify(files));
          } catch (error) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: 'Failed to read directory' }));
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
