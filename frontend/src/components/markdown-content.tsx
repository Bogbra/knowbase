"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const CITATION_PREFIX = "Quelle:";

const components: Components = {
  // Headings
  h1: ({ children }) => <h1 className="mt-4 mb-2 text-base font-bold first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-3 mb-1.5 text-sm font-bold first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-2 mb-1 text-sm font-semibold first:mt-0">{children}</h3>,

  // Paragraphs
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,

  // Citations — italic text starting with "Quelle:" gets special styling
  em: ({ children }) => {
    const text = typeof children === "string" ? children : "";
    if (text.startsWith(CITATION_PREFIX)) {
      return (
        <span className="mt-1 inline-flex items-center gap-1 rounded border border-border bg-muted/60 px-2 py-0.5 text-xs text-muted-foreground not-italic">
          📎 {text}
        </span>
      );
    }
    return <em className="italic">{children}</em>;
  },

  // Bold
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,

  // Lists
  ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-0.5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,

  // Inline code
  code: ({ children, className }) => {
    const isBlock = !!className;
    if (isBlock) {
      return (
        <pre className="my-2 overflow-x-auto rounded-md bg-muted p-3 text-xs">
          <code>{children}</code>
        </pre>
      );
    }
    return <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{children}</code>;
  },

  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-border pl-3 text-muted-foreground">
      {children}
    </blockquote>
  ),

  // Horizontal rule
  hr: () => <hr className="my-3 border-border" />,

  // Tables
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border bg-muted px-3 py-1.5 text-left font-medium">{children}</th>
  ),
  td: ({ children }) => <td className="border border-border px-3 py-1.5">{children}</td>,

  // Links — open in new tab
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline underline-offset-2 hover:no-underline"
    >
      {children}
    </a>
  ),
};

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
