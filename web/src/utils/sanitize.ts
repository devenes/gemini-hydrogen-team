/**
 * Safe HTML sanitization helper following modern-web-guidance `sanitize-untrusted-html`:
 * Uses native `Element.prototype.setHTML()` when available, and lazily code-splits
 * DOMPurify with matching strict options only when native Sanitizer API is absent.
 */

type DOMPurifyModule = typeof import("dompurify").default;

let domPurifyPromise: Promise<DOMPurifyModule> | null = null;

function loadDOMPurify(): Promise<DOMPurifyModule> {
  domPurifyPromise ??= import("dompurify").then((mod) => mod.default ?? (mod as unknown as DOMPurifyModule));
  return domPurifyPromise;
}

const ALLOWED_ELEMENTS = [
  "p",
  "br",
  "h1",
  "h2",
  "h3",
  "h4",
  "strong",
  "em",
  "code",
  "pre",
  "ul",
  "ol",
  "li",
  "blockquote",
  "hr",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "a",
  "span",
];

const ALLOWED_ATTRIBUTES = ["class", "href", "rel", "target"];

export async function safeSetHTML(el: Element, html: string): Promise<void> {
  if ("setHTML" in Element.prototype) {
    (el as Element & { setHTML: (input: string, opts?: unknown) => void }).setHTML(html, {
      sanitizer: {
        elements: ALLOWED_ELEMENTS,
        attributes: ALLOWED_ATTRIBUTES,
      },
    });
    return;
  }

  const DOMPurify = await loadDOMPurify();
  el.innerHTML = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [...ALLOWED_ELEMENTS, "#text"],
    ALLOWED_ATTR: ALLOWED_ATTRIBUTES,
    ALLOW_ARIA_ATTR: false,
    ALLOW_DATA_ATTR: false,
    KEEP_CONTENT: false,
  });
}
