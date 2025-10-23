import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import type { CCCodeExampleValidationOutput } from '../types';
import { CodeBlockWithValidation } from './CodeBlockWithValidation';

interface MarkdownViewerProps {
  content: string;
  baseImagePath?: string;
  codeValidation?: CCCodeExampleValidationOutput | null;
  onExampleClick?: (exampleIndex: number) => void;
  onViewInValidationTab?: (exampleIndex: number) => void;
}

/**
 * Normalize code string for comparison by removing extra whitespace
 * and normalizing line endings.
 */
function normalizeCode(code: string): string {
  return code
    .trim()
    .replace(/\r\n/g, '\n')
    .replace(/^\s+/gm, '') // Remove leading whitespace from each line
    .replace(/\s+$/gm, '') // Remove trailing whitespace from each line
    .replace(/\n+/g, '\n'); // Normalize multiple newlines to single
}

/**
 * Preprocess markdown to remove MkDocs Material syntax and fix indentation issues
 * This handles tab markers like === "Sync API" and normalizes code block indentation
 */
function preprocessMarkdown(content: string): string {
  const lines = content.split('\n');
  const result: string[] = [];
  let inCodeBlock = false;
  let codeBlockIndent = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Skip MkDocs Material tab markers (=== "Tab Name")
    if (line.match(/^===\s+"[^"]+"\s*$/)) {
      continue;
    }

    // Detect code fence
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;

      if (inCodeBlock) {
        // Starting code block - detect indentation level
        codeBlockIndent = line.search(/\S/);
        // Remove indentation from fence and add it without indentation
        result.push(line.trim());
      } else {
        // Ending code block
        result.push('```');
        codeBlockIndent = 0;
      }
      continue;
    }

    // Process code block content
    if (inCodeBlock) {
      // Remove the base indentation level from code block
      if (line.startsWith(' '.repeat(codeBlockIndent))) {
        result.push(line.substring(codeBlockIndent));
      } else {
        result.push(line);
      }
    } else {
      // Regular content - keep as-is
      result.push(line);
    }
  }

  return result.join('\n');
}

export function MarkdownViewer({
  content,
  baseImagePath,
  codeValidation,
  onExampleClick,
  onViewInValidationTab
}: MarkdownViewerProps) {
  // Preprocess markdown to remove MkDocs syntax and fix indentation
  const processedContent = useMemo(() => preprocessMarkdown(content), [content]);

  // Build a map: normalized code -> validation result for fast lookup
  const validationMap = useMemo(() => {
    const map = new Map();
    codeValidation?.results.forEach(result => {
      if (result.code) {
        const normalized = normalizeCode(result.code);
        map.set(normalized, result);
      }
    });
    return map;
  }, [codeValidation]);

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSanitize]}
        components={{
          // Custom image rendering to handle relative paths
          img: ({ src, alt, ...props }) => {
            const imageSrc = src?.startsWith('http')
              ? src
              : baseImagePath
                ? `/api/file?path=${encodeURIComponent(baseImagePath + '/' + src)}`
                : src;
            return (
              <img
                src={imageSrc}
                alt={alt}
                className="max-w-full h-auto rounded-lg border border-border"
                {...props}
              />
            );
          },
          // Enhanced code block rendering with validation
          code: ({ node, className, children, ...props }) => {
            // Check if this is an inline code element by checking if it's inside a paragraph
            const isInline = !className || !className.startsWith('language-');

            if (isInline) {
              return <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>{children}</code>;
            }

            // Get code content
            const codeString = String(children).replace(/\n$/, '');

            // Normalize the code for matching
            const normalizedCode = normalizeCode(codeString);

            // Look up validation by normalized code
            const validation = validationMap.get(normalizedCode);

            if (validation) {
              // Has validation - render with annotation
              return (
                <CodeBlockWithValidation
                  code={codeString}
                  className={className}
                  validation={validation}
                  onDependencyClick={onExampleClick}
                  onViewInTab={onViewInValidationTab}
                />
              );
            }

            // No validation - render normally
            const match = /language-(\w+)/.exec(className || '');
            return match ? (
              <code className={`${className} block bg-muted p-3 rounded-md overflow-x-auto`} {...props}>
                {children}
              </code>
            ) : (
              <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          },
          // Style links
          a: ({ href, children, ...props }) => (
            <a
              href={href}
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            >
              {children}
            </a>
          ),
          // Style tables
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border" {...props}>
                {children}
              </table>
            </div>
          ),
          th: ({ children, ...props }) => (
            <th className="px-4 py-2 bg-muted font-semibold text-left" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-4 py-2 border-t border-border" {...props}>
              {children}
            </td>
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
