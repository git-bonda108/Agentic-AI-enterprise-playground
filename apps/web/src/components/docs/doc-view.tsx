"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Clock, ExternalLink, SquareArrowOutUpRight } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import type { DocGuide } from "@/lib/playground-types";

/** Mirrors app.docs_hub.slugify so the table of contents and the rendered headings agree. */
export function slugify(text: string): string {
  return text.toLowerCase().replace(/[`*_]/g, "").replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-").replace(/^-+|-+$/g, "");
}

function textOf(node: React.ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) return textOf((node as { props: { children?: React.ReactNode } }).props.children);
  return "";
}

function rewriteHref(href: string, files: Record<string, string>): { href: string; external: boolean } {
  if (/^https?:\/\//.test(href)) return { href, external: true };
  const m = href.match(/^\.?\/?([A-Z_]+\.md)(#.*)?$/);
  if (m) {
    const slug = files[m[1]];
    return { href: slug ? `/docs/${slug}${m[2] ?? ""}` : href, external: false };
  }
  return { href, external: false };
}

export function DocView({ guide }: { guide: DocGuide }) {
  const files = guide.files;
  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground"><Link href="/docs" className="hover:underline">Documentation</Link> · {guide.section}</p>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{guide.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{guide.summary}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 text-muted-foreground"><Clock className="size-3.5" /> {guide.minutes} min read</span>
          <Link href={guide.page} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground" data-testid="doc-open-page"><SquareArrowOutUpRight className="size-3.5" /> Open {guide.page_label}</Link>
        </div>
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="lg:sticky lg:top-4 lg:self-start" aria-label="On this page">
          <p className="text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">On this page</p>
          <ol className="mt-2 space-y-1 text-xs" data-testid="doc-toc">
            {guide.headings.map((h) => <li key={h.id}><a href={`#${h.id}`} className="block truncate rounded px-1.5 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground">{h.text}</a></li>)}
          </ol>
        </nav>
        <article className="min-w-0 rounded-2xl border bg-card p-5 text-[14.5px] leading-7 [&_blockquote]:border-l-2 [&_blockquote]:border-brand-violet/40 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] [&_h1]:hidden [&_h2]:mt-8 [&_h2]:scroll-mt-4 [&_h2]:border-b [&_h2]:pb-1 [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:mt-5 [&_h3]:font-semibold [&_img]:my-3 [&_img]:rounded-xl [&_img]:border [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_table]:my-3 [&_table]:w-full [&_table]:text-[13px] [&_td]:border [&_td]:px-2 [&_td]:py-1 [&_td]:align-top [&_th]:border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_ul]:list-disc [&_ul]:pl-5" data-testid="doc-body">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h2: ({ children }) => <h2 id={slugify(textOf(children))}>{children}</h2>,
              h3: ({ children }) => <h3 id={slugify(textOf(children))}>{children}</h3>,
              a: ({ href, children }) => {
                const r = rewriteHref(href ?? "", files);
                if (r.external) return <a href={r.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-brand-violet-soft underline">{children}<ExternalLink className="size-3" /></a>;
                return <Link href={r.href} className="text-brand-violet-soft underline">{children}</Link>;
              },
              img: ({ src, alt }) => {
                const s = typeof src === "string" ? src : "";
                const name = s.replace(/^\.?\/?images\//, "");
                // eslint-disable-next-line @next/next/no-img-element
                return <img src={s.startsWith("http") ? s : `/api/pg/v1/docs/images/${name}`} alt={alt ?? ""} loading="lazy" />;
              },
              pre: ({ children }) => {
                const raw = textOf(children);
                return (
                  <div className="group relative my-3">
                    <pre className="overflow-x-auto rounded-xl border bg-[#0d0d18] p-3 font-mono text-[12.5px] leading-6 text-slate-100 [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-inherit">{children}</pre>
                    <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"><CopyButton text={raw} /></div>
                  </div>
                );
              },
            }}
          >
            {guide.markdown}
          </ReactMarkdown>
          <div className="mt-8 flex items-center justify-between gap-3 border-t pt-4 text-xs">
            {guide.prev ? <Link href={`/docs/${guide.prev.slug}`} className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline"><ArrowLeft className="size-3.5" /> {guide.prev.title}</Link> : <span />}
            {guide.next ? <Link href={`/docs/${guide.next.slug}`} className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{guide.next.title} <ArrowRight className="size-3.5" /></Link> : <span />}
          </div>
        </article>
      </div>
    </div>
  );
}
