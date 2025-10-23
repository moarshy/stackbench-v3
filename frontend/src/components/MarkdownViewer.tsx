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

export function MarkdownViewer({
  content,
  baseImagePath,
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

  // Track line numbers for code blocks
  let currentLine = 1;

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
          code: ({ node, inline, className, children, ...props }) => {
            if (inline) {
              return <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>{children}</code>;
            }

            // Get code content
            const codeString = String(children).replace(/\n$/, '');

            // Try to get validation data for this code block
            // Note: This is a simplified approach - we're matching by code content
            // In a real implementation, you might need to track line numbers more precisely
            const validation = Array.from(validationMap.values()).find(
              v => v.code && codeString.includes(v.code.substring(0, 50))
            );

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
        {content}
      </ReactMarkdown>
    </div>
  );
}
