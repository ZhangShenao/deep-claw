"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import MarkdownMessage from "@/components/MarkdownMessage";
import {
  createConversation,
  deleteConversation,
  fetchConversations,
  fetchMessages,
  streamChat,
  type Conversation,
  type StreamEvent,
} from "@/lib/api";

type ChatMessage = { role: "user" | "assistant"; content: string };
type LogLine = { id: string; text: string; tone: "active" | "done" };

function id() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function clipText(value: unknown, limit = 160) {
  if (value == null) return "";

  let text = "";
  if (typeof value === "string") {
    text = value;
  } else {
    try {
      text = JSON.stringify(value);
    } catch {
      text = String(value);
    }
  }

  const compact = text.replace(/\s+/g, " ").trim();
  if (!compact || compact === "{}" || compact === "[]") return "";
  return compact.length > limit ? `${compact.slice(0, Math.max(0, limit - 3))}...` : compact;
}

function isNearBottom(node: HTMLDivElement, threshold = 120) {
  return node.scrollHeight - node.scrollTop - node.clientHeight <= threshold;
}

export default function ChatApp() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [steps, setSteps] = useState<LogLine[]>([]);
  const [showSteps, setShowSteps] = useState(true);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const activeIdRef = useRef<string | null>(null);
  const shouldStickToBottomRef = useRef(true);
  const streamRef = useRef<{
    requestId: string;
    conversationId: string;
    controller: AbortController;
  } | null>(null);

  const loadList = useCallback(async () => {
    const list = await fetchConversations();
    setConversations(list);
    setActiveId((prev) => prev ?? (list[0]?.id ?? null));
  }, []);

  useEffect(() => {
    loadList().catch((e) => setError(String(e)));
  }, [loadList]);

  useEffect(() => {
    if (!activeId) return;
    fetchMessages(activeId)
      .then((rows) => {
        setMessages(
          rows
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({
              role: m.role as "user" | "assistant",
              content: m.content,
            })),
        );
        setSteps([]);
      })
      .catch((e) => setError(String(e)));
  }, [activeId]);

  useEffect(() => {
    activeIdRef.current = activeId;
    shouldStickToBottomRef.current = true;
  }, [activeId]);

  const cancelCurrentStream = useCallback((resetLoading = true) => {
    const current = streamRef.current;
    if (!current) return;
    streamRef.current = null;
    current.controller.abort();
    if (resetLoading) {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    return () => cancelCurrentStream(false);
  }, [cancelCurrentStream]);

  useEffect(() => {
    const current = streamRef.current;
    if (!current) return;
    if (current.conversationId !== activeId) {
      cancelCurrentStream();
    }
  }, [activeId, cancelCurrentStream]);

  useEffect(() => {
    if (!shouldStickToBottomRef.current) return;
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, steps, loading]);

  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "0px";
    node.style.height = `${Math.min(node.scrollHeight, 200)}px`;
  }, [input]);

  const activeConv = conversations.find((c) => c.id === activeId);

  const appendStep = useCallback((text: string, tone: LogLine["tone"]) => {
    setSteps((prev) => [...prev, { id: id(), text, tone }]);
  }, []);

  const isCurrentStream = useCallback((requestId: string, conversationId: string) => {
    const current = streamRef.current;
    return (
      current?.requestId === requestId &&
      current.conversationId === conversationId &&
      activeIdRef.current === conversationId
    );
  }, []);

  const handleEvent = useCallback((ev: StreamEvent, requestId: string, conversationId: string) => {
    if (!isCurrentStream(requestId, conversationId)) return;

    if (ev.type === "token") {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = { ...last, content: last.content + ev.content };
        } else {
          next.push({ role: "assistant", content: ev.content });
        }
        return next;
      });
      return;
    }
    if (ev.type === "tool_start") {
      const summary = clipText(ev.input, 120);
      appendStep(summary ? `调用 ${ev.name} · ${summary}` : `调用 ${ev.name}`, "active");
      return;
    }
    if (ev.type === "tool_end") {
      const summary = clipText(ev.output, 180);
      appendStep(summary ? `${ev.name} 已返回 · ${summary}` : `${ev.name} 已返回`, "done");
      return;
    }
    if (ev.type === "subagent") {
      if (ev.phase === "start") {
        const summary = clipText(ev.name, 150);
        appendStep(summary ? `启动深度调研 · ${summary}` : "启动深度调研", "active");
        return;
      }

      const summary = clipText(ev.output ?? ev.name, 180);
      appendStep(summary ? `深度调研完成 · ${summary}` : "深度调研完成", "done");
      return;
    }
    if (ev.type === "error") {
      setError(ev.message);
    }
  }, [appendStep, isCurrentStream]);

  async function onSend() {
    if (!input.trim() || !activeId || loading) return;
    const text = input.trim();
    const conversationId = activeId;
    const requestId = id();
    const controller = new AbortController();

    cancelCurrentStream();
    streamRef.current = { requestId, conversationId, controller };
    shouldStickToBottomRef.current = true;
    setInput("");
    setError(null);
    setSteps([]);
    setShowSteps(true);
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setLoading(true);
    try {
      await streamChat(
        conversationId,
        text,
        (ev) => handleEvent(ev, requestId, conversationId),
        { signal: controller.signal },
      );
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError") && isCurrentStream(requestId, conversationId)) {
        setError(String(e));
        setMessages((prev) => {
          const next = [...prev];
          if (next[next.length - 1]?.role === "assistant" && next[next.length - 1].content === "") {
            next.pop();
          }
          return next;
        });
      }
    } finally {
      if (streamRef.current?.requestId === requestId) {
        streamRef.current = null;
        setLoading(false);
      }
      await loadList();
    }
  }

  async function onNewChat() {
    cancelCurrentStream();
    shouldStickToBottomRef.current = true;
    setError(null);
    const c = await createConversation();
    setConversations((list) => [c, ...list]);
    setActiveId(c.id);
    setMessages([]);
    setSteps([]);
  }

  async function onDelete(id: string) {
    if (streamRef.current?.conversationId === id) {
      cancelCurrentStream();
    }
    await deleteConversation(id);
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
      setSteps([]);
    }
    await loadList();
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[var(--app-bg)] text-[var(--foreground)] md:h-[100dvh] md:flex-row">
      <aside className="m-3 mb-0 flex shrink-0 flex-col rounded-[28px] border border-white/8 bg-white/6 p-3 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl md:m-4 md:mr-0 md:w-[18.5rem]">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.3em] text-emerald-200/70">Deep-Claw</div>
            <h1 className="mt-2 text-lg font-semibold tracking-tight text-white">智能对话工作台</h1>
          </div>
          <button
            type="button"
            onClick={() => onNewChat().catch((e) => setError(String(e)))}
            className="rounded-full border border-emerald-300/30 bg-emerald-300/12 px-3 py-1.5 text-xs font-medium text-emerald-100 transition hover:border-emerald-200/40 hover:bg-emerald-300/18"
          >
            新对话
          </button>
        </div>

        <div className="mb-3 rounded-2xl border border-white/8 bg-black/12 px-3 py-2 text-xs leading-5 text-neutral-400">
          单用户模式。对话输出与 Agent 执行轨迹会在当前窗口实时更新。
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1 md:flex-1 md:flex-col md:overflow-y-auto md:pb-0">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex min-w-56 items-center gap-2 rounded-2xl border px-3 py-3 transition md:min-w-0 ${
                c.id === activeId
                  ? "border-white/14 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                  : "border-transparent bg-transparent hover:border-white/8 hover:bg-white/5"
              }`}
            >
              <button
                type="button"
                onClick={() => {
                  setActiveId(c.id);
                  setMessages([]);
                  setSteps([]);
                }}
                className="min-w-0 flex-1 text-left"
              >
                <div className="truncate text-sm font-medium text-white">{c.title}</div>
                <div className="mt-1 truncate text-xs text-neutral-500">
                  {c.id === activeId ? "当前对话" : "切换到此会话"}
                </div>
              </button>
              <button
                type="button"
                className="rounded-full p-1 text-xs text-neutral-500 transition hover:bg-red-500/10 hover:text-red-200"
                onClick={() => onDelete(c.id).catch((e) => setError(String(e)))}
                aria-label="删除"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <main className="flex min-h-0 flex-1 flex-col p-3 pt-3 md:p-4">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(18,23,31,0.96),rgba(10,14,20,0.92))] shadow-[0_30px_120px_rgba(0,0,0,0.34)] backdrop-blur-xl">
          <header className="border-b border-white/8 px-5 py-4 md:px-7">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.32em] text-neutral-500">Conversation</div>
                <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">
                  {activeConv?.title ?? "请选择或创建会话"}
                </h2>
              </div>
              <div className="rounded-full border border-white/8 bg-white/4 px-3 py-1 text-xs text-neutral-400">
                {loading ? "Agent 正在处理..." : "等待输入"}
              </div>
            </div>
          </header>

          {error && (
            <div className="mx-5 mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100 md:mx-7">
              {error}
            </div>
          )}

          <div
            ref={scrollRef}
            onScroll={(e) => {
              shouldStickToBottomRef.current = isNearBottom(e.currentTarget);
            }}
            className="flex-1 overflow-y-auto px-4 py-6 md:px-7"
          >
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
              {messages.length === 0 && !loading && (
                <section className="rounded-[28px] border border-white/8 bg-white/4 px-6 py-8 text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-300/12 text-lg text-emerald-100">
                    DC
                  </div>
                  <h3 className="text-2xl font-semibold tracking-tight text-white">开始一段新的对话</h3>
                  <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-neutral-400">
                    这里会按聊天流展示用户消息、助手回答，以及 Agent 当前回合的执行思考过程。
                  </p>
                </section>
              )}

              {messages.map((m, i) => {
                const isStreamingAssistant =
                  loading && m.role === "assistant" && i === messages.length - 1;

                if (m.role === "user") {
                  return (
                    <div key={i} className="flex justify-end">
                      <div className="max-w-[min(88%,42rem)] rounded-[28px] bg-[linear-gradient(135deg,#1c2430,#121922)] px-5 py-4 text-sm leading-7 text-neutral-100 shadow-[0_12px_44px_rgba(0,0,0,0.26)] ring-1 ring-white/10">
                        <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.28em] text-neutral-500">
                          你
                        </div>
                        <MarkdownMessage content={m.content} className="chat-markdown break-words text-sm leading-7" />
                      </div>
                    </div>
                  );
                }

                return (
                  <section key={i} className="rounded-[30px] border border-white/8 bg-white/4 px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
                    <div className="mb-3 flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-emerald-300/12 text-sm font-semibold text-emerald-100">
                        AI
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">Deep-Claw</div>
                        <div className="text-xs text-neutral-500">实时回复中</div>
                      </div>
                    </div>
                    <div className="break-words text-[15px] leading-8 text-neutral-100">
                      <MarkdownMessage content={m.content} className="chat-markdown" />
                      {isStreamingAssistant && (
                        <span className="ml-1 inline-block h-4 w-2 rounded-full bg-emerald-200/70 align-middle animate-pulse" />
                      )}
                    </div>
                  </section>
                );
              })}

              {(steps.length > 0 || loading) && (
                <section className="rounded-[26px] border border-white/8 bg-black/14 px-5 py-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="text-[11px] font-medium uppercase tracking-[0.32em] text-neutral-500">
                        思考过程
                      </div>
                      <div className="rounded-full border border-white/8 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-neutral-500">
                        {loading ? "streaming" : "complete"}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-[11px] text-neutral-500">{steps.length} 条</div>
                      <button
                        type="button"
                        onClick={() => setShowSteps((prev) => !prev)}
                        className="rounded-full border border-white/8 bg-white/5 px-3 py-1 text-[11px] text-neutral-300 transition hover:bg-white/10"
                        aria-expanded={showSteps}
                      >
                        {showSteps ? "收起" : "展开"}
                      </button>
                    </div>
                  </div>
                  {showSteps ? (
                    <div className="space-y-2 text-xs leading-6 text-neutral-400">
                      {steps.map((s) => (
                        <div key={s.id} className="flex gap-3">
                          <div
                            className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${
                              s.tone === "done" ? "bg-emerald-200/80" : "bg-sky-200/80"
                            }`}
                          />
                          <div className="min-w-0 break-words font-mono">{s.text}</div>
                        </div>
                      ))}
                      {loading && (
                        <div className="flex gap-3 text-neutral-500">
                          <div className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-500 animate-pulse" />
                          <div className="font-mono">等待更多执行事件...</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs leading-6 text-neutral-500">
                      {loading ? "思考过程已折叠，仍在实时更新。" : "思考过程已折叠。"}
                    </div>
                  )}
                </section>
              )}

              <div ref={endRef} />
            </div>
          </div>

          <div className="border-t border-white/8 px-4 py-4 md:px-6 md:py-5">
            <div className="mx-auto max-w-3xl">
              <div className="rounded-[30px] border border-white/10 bg-white/6 p-2 shadow-[0_16px_52px_rgba(0,0,0,0.24)]">
                <div className="flex flex-col gap-3 md:flex-row md:items-end">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        onSend();
                      }
                    }}
                    placeholder={activeId ? "输入消息，按 Enter 发送，Shift + Enter 换行" : "请先创建会话"}
                    disabled={!activeId || loading}
                    rows={1}
                    className="max-h-[200px] min-h-[56px] flex-1 resize-none bg-transparent px-4 py-3 text-sm leading-7 text-white placeholder:text-neutral-500 focus:outline-none disabled:cursor-not-allowed"
                  />
                  <div className="flex items-center justify-between gap-3 px-2 pb-2 md:justify-end">
                    <div className="text-xs text-neutral-500">Enter 发送</div>
                    <button
                      type="button"
                      onClick={() => onSend()}
                      disabled={!activeId || loading || !input.trim()}
                      className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-medium text-[#082018] transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:bg-white/12 disabled:text-neutral-500"
                    >
                      {loading ? "发送中" : "发送"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
