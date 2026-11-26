import { useEffect, useRef } from "react";
import { markdownToHtml } from "../utils/markdown";
import { safeSetHTML } from "../utils/sanitize";

interface SafeMarkdownProps {
  content: string;
  className?: string;
}

export function SafeMarkdown({ content, className = "" }: SafeMarkdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let cancelled = false;
    const html = markdownToHtml(content);
    void safeSetHTML(el, html).catch(() => {
      if (!cancelled) {
        el.textContent = content;
      }
    });
    return () => {
      cancelled = true;
    };
  }, [content]);

  return <div ref={containerRef} className={`md-content ${className}`.trim()} />;
}
