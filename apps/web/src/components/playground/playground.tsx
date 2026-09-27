"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Columns3, MessageSquare, NotebookPen, Send, SlidersHorizontal, Sparkles, Square } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ConversationList } from "@/components/playground/conversation-list";
import { MessageBubble } from "@/components/playground/message-bubble";
import { ModelPicker } from "@/components/playground/model-picker";
import { ParamsPanel } from "@/components/playground/params-panel";
import { CodeDialog } from "@/components/playground/code-dialog";
import { CompareGrid, type CompareColumn } from "@/components/playground/compare-grid";
import { readSse } from "@/lib/sse";
import {
  DEFAULT_PARAMS, formatUsd, type CatalogModel, type ChatMessage, type ChatParams, type ConversationDetail, type ConversationSummary, type RouteDecision, type Usage,
} from "@/lib/playground-types";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/shell/brand-mark";

const uid = () => Math.random().toString(36).slice(2);

type Meta = { conversation_id: string | null; title: string | null; model: string; routed: boolean; routed_tier: string | null; route_reason: string | null; budget_warnings: string[]; user_spend_usd: number; user_cap_usd: number };

type StreamHandlers = {
  onMeta?: (d: Meta) => void;
  onDelta: (text: string) => void;
  onUsage: (u: Usage) => void;
  onError: (message: string) => void;
};

async function streamChat(body: object, handlers: StreamHandlers, signal: AbortSignal) {
  const res = await fetch("/api/pg/v1/chat/stream", {
    method: "POST", headers: { "content-type": "application/json", accept: "text/event-stream" }, body: JSON.stringify(body), signal,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not json */ }
    handlers.onError(detail);
    return;
  }
  for await (const ev of readSse(res)) {
    const data = ev.data ? JSON.parse(ev.data) : {};
    if (ev.event === "meta") handlers.onMeta?.(data);
    else if (ev.event === "delta") handlers.onDelta(data.text);
    else if (ev.event === "usage") handlers.onUsage(data as Usage);
    else if (ev.event === "error") handlers.onError(data.message);
  }
}

export function Playground({ models, initialConversations, defaultModel, smartEnabled = false }: { models: CatalogModel[]; initialConversations: ConversationSummary[]; defaultModel: string; smartEnabled?: boolean }) {
  const [conversations, setConversations] = useState(initialConversations);
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [model, setModel] = useState(defaultModel);
  const [params, setParams] = useState<ChatParams>(DEFAULT_PARAMS);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showParams, setShowParams] = useState(true);
  const [mode, setMode] = useState<"chat" | "compare">("chat");
  const [compareIds, setCompareIds] = useState<string[]>(() => [defaultModel]);
  const [compareCols, setCompareCols] = useState<CompareColumn[]>([]);
  const [comparePrompt, setComparePrompt] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<RouteDecision | null>(null);

  const isSmart = model === "smart";
  const current = models.find((m) => m.id === model);
  const previewModel = preview ? models.find((m) => m.id === preview.model) : undefined;

  useEffect(() => {
    const t = setTimeout(() => {
      if (!isSmart || !input.trim()) { setPreview(null); return; }
      fetch("/api/pg/v1/route/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ prompt: input }) })
        .then((r) => r.json()).then((j) => setPreview(j.decision ?? null)).catch(() => setPreview(null));
    }, 300);
    return () => clearTimeout(t);
  }, [input, isSmart]);
  const sessionCost = messages.reduce((s, m) => s + (m.usage?.cost_usd ?? 0), 0);

  const refreshList = useCallback(async (q = query) => {
    const res = await fetch(`/api/pg/v1/conversations?q=${encodeURIComponent(q)}`);
    if (res.ok) setConversations((await res.json()).conversations);
  }, [query]);

  useEffect(() => {
    const t = setTimeout(() => { void refreshList(query); }, 250);
    return () => clearTimeout(t);
  }, [query, refreshList]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const openConversation = async (id: string) => {
    const res = await fetch(`/api/pg/v1/conversations/${id}`);
    if (!res.ok) return;
    const c = (await res.json()) as ConversationDetail;
    setActiveId(c.id);
    setModel(c.model);
    setParams((p) => ({ ...p, system: c.system_prompt ?? "" }));
    setMode("chat");
    setMessages(c.messages.map((m) => ({
      id: m.id, role: m.role, content: m.content, model: m.model ?? undefined,
      usage: m.role === "assistant" ? { tokens_in: m.tokens_in, tokens_out: m.tokens_out, tokens_cached: 0, cost_usd: m.cost_usd, latency_ms: m.latency_ms, model: m.model ?? c.model, provider: "", message_id: m.id, conversation_id: c.id } : null,
    })));
  };

  const newConversation = () => { setActiveId(null); setMessages([]); setInput(""); setMode("chat"); };

  const stop = () => { abortRef.current?.abort(); abortRef.current = null; setBusy(false); };

  const sendChat = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const userMsg: ChatMessage = { id: uid(), role: "user", content: text };
    const assistantId = uid();
    const history = [...messages, userMsg];
    setMessages([...history, { id: assistantId, role: "assistant", content: "", model, streaming: true }]);
    setInput("");
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    const update = (patch: Partial<ChatMessage>) => setMessages((ms) => ms.map((m) => (m.id === assistantId ? { ...m, ...patch } : m)));
    try {
      await streamChat(
        {
          model, conversation_id: activeId, persist: true, feature: "chat",
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          params: { temperature: params.temperature, max_tokens: params.max_tokens, top_p: params.top_p, system: params.system || null },
        },
        {
          onMeta: (d) => {
            if (!activeId && d.conversation_id) setActiveId(d.conversation_id);
            if (d.routed) update({ model: d.model });
            for (const w of d.budget_warnings ?? []) toast.warning(w);
            if (d.budget_warnings?.length) window.dispatchEvent(new Event("playground:alerts"));
          },
          onDelta: (t) => setMessages((ms) => ms.map((m) => (m.id === assistantId ? { ...m, content: m.content + t } : m))),
          onUsage: (u) => update({ usage: u, streaming: false }),
          onError: (message) => { update({ error: message, streaming: false }); toast.error(message); window.dispatchEvent(new Event("playground:alerts")); },
        },
        controller.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") update({ error: (e as Error).message, streaming: false });
      else update({ streaming: false });
    } finally {
      setBusy(false);
      abortRef.current = null;
      void refreshList();
    }
  };

  const sendCompare = async () => {
    const text = input.trim();
    if (!text || busy || compareIds.length === 0) return;
    setComparePrompt(text);
    setInput("");
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    const cols: CompareColumn[] = compareIds.map((id) => ({ modelId: id, message: { id: uid(), role: "assistant", content: "", model: id, streaming: true } }));
    setCompareCols(cols);
    const patch = (modelId: string, fn: (m: ChatMessage) => ChatMessage) =>
      setCompareCols((cs) => cs.map((c) => (c.modelId === modelId && c.message ? { ...c, message: fn(c.message) } : c)));
    await Promise.all(compareIds.map((id) =>
      streamChat(
        { model: id, persist: false, feature: "compare", messages: [{ role: "user", content: text }], params: { temperature: params.temperature, max_tokens: params.max_tokens, top_p: params.top_p, system: params.system || null } },
        {
          onDelta: (t) => patch(id, (m) => ({ ...m, content: m.content + t })),
          onUsage: (u) => patch(id, (m) => ({ ...m, usage: u, streaming: false })),
          onError: (message) => patch(id, (m) => ({ ...m, error: message, streaming: false })),
        },
        controller.signal,
      ).catch((e: Error) => patch(id, (m) => ({ ...m, error: e.name === "AbortError" ? "Stopped" : e.message, streaming: false }))),
    ));
    setBusy(false);
    abortRef.current = null;
  };

  const toggleCompare = (id: string) =>
    setCompareIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : ids.length >= 4 ? ids : [...ids, id]));

  const pin = async (c: ConversationSummary) => {
    await fetch(`/api/pg/v1/conversations/${c.id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ pinned: !c.pinned }) });
    void refreshList();
  };
  const remove = async (c: ConversationSummary) => {
    await fetch(`/api/pg/v1/conversations/${c.id}`, { method: "DELETE" });
    if (activeId === c.id) newConversation();
    void refreshList();
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void (mode === "chat" ? sendChat() : sendCompare()); }
  };

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100vh-3.5rem)] sm:-mx-6 lg:-mx-8">
      <ConversationList items={conversations} activeId={activeId} query={query} onQuery={setQuery} onSelect={openConversation} onNew={newConversation} onPin={pin} onDelete={remove} />

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
          <h1 className="mr-2 text-sm font-semibold">Playground</h1>
          <ModelPicker models={models} value={model} onChange={setModel} smartEnabled={smartEnabled} />
          <div className="ml-auto flex items-center gap-1.5">
            <div role="tablist" aria-label="Mode" className="flex rounded-lg border bg-card p-0.5 text-xs">
              <button type="button" role="tab" aria-selected={mode === "chat"} onClick={() => setMode("chat")} className={cn("flex h-7 items-center gap-1 rounded-md px-2", mode === "chat" && "bg-secondary text-secondary-foreground")}><MessageSquare className="size-3.5" /> Chat</button>
              <button type="button" role="tab" aria-selected={mode === "compare"} onClick={() => setMode("compare")} className={cn("flex h-7 items-center gap-1 rounded-md px-2", mode === "compare" && "bg-secondary text-secondary-foreground")}><Columns3 className="size-3.5" /> Compare</button>
            </div>
            {activeId && <a href={`/build/notebooks?conversation=${activeId}`} className="inline-flex h-7 items-center gap-1 rounded-lg border bg-card px-2.5 text-xs hover:border-brand-violet/40" aria-label="Open conversation in notebook"><NotebookPen className="size-3.5" /> Notebook</a>}
            <CodeDialog model={current ?? previewModel} prompt={input || messages.findLast?.((m) => m.role === "user")?.content || ""} params={params} />
            <Button variant={showParams ? "secondary" : "outline"} size="sm" aria-label="Toggle parameters" aria-pressed={showParams} onClick={() => setShowParams((s) => !s)}>
              <SlidersHorizontal className="size-3.5" /> Parameters
            </Button>
          </div>
        </header>

        {mode === "compare" && (
          <div className="flex flex-wrap items-center gap-1.5 border-b px-4 py-2 text-xs" aria-label="Models to compare">
            <span className="mr-1 text-muted-foreground">Compare up to four:</span>
            {models.filter((m) => m.available).map((m) => (
              <label key={m.id} className={cn("flex cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1", compareIds.includes(m.id) && "border-brand-violet/60 bg-secondary")}>
                <input type="checkbox" className="accent-[var(--brand-violet)]" checked={compareIds.includes(m.id)} onChange={() => toggleCompare(m.id)} aria-label={`Compare ${m.name}`} />
                {m.name}
              </label>
            ))}
          </div>
        )}

        <div ref={threadRef} className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
          {mode === "chat" ? (
            messages.length === 0 ? (
              <div className="mx-auto mt-16 max-w-lg text-center">
                <div className="mx-auto w-fit"><BrandMark size={48} /></div>
                <h2 className="mt-4 text-lg font-semibold">Ask anything, on any model</h2>
                <p className="mt-1 text-sm text-muted-foreground">Every message is metered to you and visible in Cost. Switch models mid-conversation, compare four at once, or copy the request as code.</p>
                <div className="mt-5 grid gap-2 sm:grid-cols-3">
                  {["Summarize the attached policy in five bullets", "Draft a supplier email disputing an invoice total", "Explain retrieval-augmented generation to a finance analyst"].map((s) => (
                    <button key={s} type="button" onClick={() => setInput(s)} className="card-hover rounded-xl border bg-card p-3 text-left text-xs text-muted-foreground hover:text-foreground">{s}</button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-5">
                {messages.map((m) => <MessageBubble key={m.id} m={m} modelName={models.find((x) => x.id === (m.usage?.model ?? m.model))?.name} />)}
              </div>
            )
          ) : (
            <CompareGrid columns={compareCols.length ? compareCols : compareIds.map((id) => ({ modelId: id, message: null }))} models={models} prompt={comparePrompt} />
          )}
        </div>

        <div className="border-t px-4 py-3 sm:px-6">
          <div className="mx-auto max-w-3xl">
            <div className="beam-border relative rounded-2xl border bg-card">
              {isSmart && (
                <div className="flex flex-wrap items-center gap-2 border-b px-4 py-1.5 text-[11px]" data-testid="route-preview">
                  <Sparkles className="size-3.5 text-brand-violet-soft" />
                  {preview ? (
                    <>
                      <span>Will use <span className="font-medium text-foreground">{previewModel?.name ?? preview.model}</span> <span className="text-muted-foreground">({preview.tier.toLowerCase()})</span></span>
                      <span className="text-muted-foreground">· {preview.reason}</span>
                      <span className="ml-auto rounded-md bg-brand-emerald/15 px-1.5 py-0.5 font-mono text-brand-emerald">est {formatUsd(preview.est_cost_usd)} · saves {preview.est_savings_pct}% vs {models.find((m) => m.id === preview.baseline_model)?.name ?? preview.baseline_model}</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground">Smart routing picks the cheapest model that fits the task. Start typing to see the choice.</span>
                  )}
                </div>
              )}
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKey}
                rows={3}
                placeholder={mode === "chat" ? (isSmart ? "Message any model, Smart picks the cheapest fit…" : `Message ${current?.name ?? "the model"}…`) : "Prompt to send to every selected model…"}
                aria-label="Prompt"
                className="w-full resize-none bg-transparent px-4 pb-10 pt-3 text-sm outline-none"
              />
              <div className="absolute bottom-2 left-3 right-2 flex items-center gap-2 text-[11px] text-muted-foreground">
                <span>Enter to send · Shift+Enter for a new line</span>
                {sessionCost > 0 && <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono">session {formatUsd(sessionCost)}</span>}
                <span className="ml-auto" />
                {busy ? (
                  <Button size="sm" variant="outline" onClick={stop} aria-label="Stop generating"><Square className="size-3.5" /> Stop</Button>
                ) : (
                  <Button size="sm" onClick={() => void (mode === "chat" ? sendChat() : sendCompare())} disabled={!input.trim()} aria-label="Send message" className="glow-violet">
                    <Send className="size-3.5" /> {mode === "chat" ? "Send" : `Run ${compareIds.length}`}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {showParams && <ParamsPanel params={params} onChange={setParams} model={current} />}
    </div>
  );
}
