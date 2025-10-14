import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';

interface MarkdownViewerProps {
  content: string;
  baseImagePath?: string;
}

export function MarkdownViewer({ content, baseImagePath }: MarkdownViewerProps) {
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
          // Style code blocks
          code: ({ className, children, ...props }) => {
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
