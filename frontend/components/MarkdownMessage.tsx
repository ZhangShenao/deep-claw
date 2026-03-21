"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { PrismAsyncLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";

type MarkdownMessageProps = {
  content: string;
  className?: string;
};

type CodeBlockProps = {
  code: string;
  language?: string;
};

const LANGUAGE_ALIASES: Record<string, string> = {
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  bash: "bash",
  py: "python",
  yml: "yaml",
  md: "markdown",
  plaintext: "text",
  text: "text",
};

function normalizeLanguage(language?: string) {
  if (!language) return { label: "text", syntax: "text" };

  const label = language.toLowerCase();
  return {
    label,
    syntax: LANGUAGE_ALIASES[label] ?? label,
  };
}

function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const { label, syntax } = normalizeLanguage(language);

  useEffect(() => {
    if (!copied) return;
    const timeout = window.setTimeout(() => setCopied(false), 1500);
    return () => window.clearTimeout(timeout);
  }, [copied]);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="chat-code-block">
      <div className="chat-code-toolbar">
        <span className="chat-code-language">{label}</span>
        <button type="button" onClick={() => void onCopy()} className="chat-code-copy">
          {copied ? "已复制" : "复制"}
        </button>
      </div>
      <SyntaxHighlighter
        language={syntax === "text" ? undefined : syntax}
        style={oneDark}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: 0,
          padding: "0.95rem 1rem 1rem",
          background: "transparent",
          fontSize: "0.92rem",
          lineHeight: "1.7",
        }}
        codeTagProps={{
          style: {
            fontFamily: "var(--font-geist-mono), monospace",
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

export default function MarkdownMessage({ content, className }: MarkdownMessageProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const match = /language-([\w-]+)/.exec(className || "");
            const isBlock = Boolean(match) || text.includes("\n");

            if (!isBlock) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            }

            return <CodeBlock code={text} language={match?.[1]} />;
          },
          a({ href, children, ...props }) {
            const isExternal = typeof href === "string" && /^https?:\/\//.test(href);
            return (
              <a
                href={href}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noreferrer noopener" : undefined}
                {...props}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
