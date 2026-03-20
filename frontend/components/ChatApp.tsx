"use client";

import { useCallback, useEffect, useState } from "react";
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
type LogLine = { id: string; text: string; kind: "step" | "text" };

function id() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export default function ChatApp() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [steps, setSteps] = useState<LogLine[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const activeConv = conversations.find((c) => c.id === activeId);

  const handleEvent = useCallback((ev: StreamEvent) => {
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
      setSteps((s) => [
        ...s,
        {
          id: id(),
          kind: "step",
          text: `工具开始: ${ev.name} ${JSON.stringify(ev.input).slice(0, 200)}`,
        },
      ]);
      return;
    }
    if (ev.type === "tool_end") {
      setSteps((s) => [
        ...s,
        {
          id: id(),
          kind: "step",
          text: `工具结束: ${ev.name} ${JSON.stringify(ev.output).slice(0, 300)}`,
        },
      ]);
      return;
    }
    if (ev.type === "subagent") {
      setSteps((s) => [
        ...s,
        {
          id: id(),
          kind: "step",
          text: `子代理 ${ev.phase}: ${typeof ev.name === "string" ? ev.name : JSON.stringify(ev.name)}`,
        },
      ]);
    }
    if (ev.type === "error") {
      setError(ev.message);
    }
  }, []);

  async function onSend() {
    if (!input.trim() || !activeId || loading) return;
    const text = input.trim();
    setInput("");
    setError(null);
    setSteps([]);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    try {
      await streamChat(activeId, text, handleEvent);
    } catch (e) {
      setError(String(e));
      setMessages((prev) => {
        const next = [...prev];
        if (next[next.length - 1]?.role === "assistant" && next[next.length - 1].content === "") {
          next.pop();
        }
        return next;
      });
    } finally {
      setLoading(false);
      await loadList();
    }
  }

  async function onNewChat() {
    setError(null);
    const c = await createConversation();
    setConversations((list) => [c, ...list]);
    setActiveId(c.id);
    setMessages([]);
    setSteps([]);
  }

  async function onDelete(id: string) {
    await deleteConversation(id);
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
    await loadList();
  }

  return (
    <div className="flex h-[100dvh] w-full">
      <aside className="flex w-64 flex-col border-r border-neutral-800 bg-neutral-950 p-3">
        <button
          type="button"
          onClick={() => onNewChat().catch((e) => setError(String(e)))}
          className="mb-3 rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-white"
        >
          新对话
        </button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {conversations.map((c) => (
            <div key={c.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => {
                  setActiveId(c.id);
                  setMessages([]);
                  setSteps([]);
                }}
                className={`flex-1 truncate rounded-md px-2 py-2 text-left text-sm ${
                  c.id === activeId ? "bg-neutral-800 text-neutral-100" : "text-neutral-400 hover:bg-neutral-900"
                }`}
              >
                {c.title}
              </button>
              <button
                type="button"
                className="rounded px-1 text-xs text-neutral-500 hover:text-red-400"
                onClick={() => onDelete(c.id).catch((e) => setError(String(e)))}
                aria-label="删除"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-neutral-800 px-6 py-4">
          <h1 className="text-lg font-semibold tracking-tight">Deep-Claw</h1>
          <p className="text-sm text-neutral-500">{activeConv?.title ?? "请选择或创建会话"}</p>
        </header>
        {error && (
          <div className="mx-6 mt-2 rounded-md border border-red-900/50 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
          {steps.length > 0 && (
            <section className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 text-xs text-neutral-400">
              <div className="mb-2 font-medium text-neutral-300">执行步骤</div>
              <ul className="space-y-1 font-mono">
                {steps.map((s) => (
                  <li key={s.id}>{s.text}</li>
                ))}
              </ul>
            </section>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[min(100%,48rem)] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "ml-auto bg-neutral-800 text-neutral-100"
                  : "mr-auto border border-neutral-800 bg-neutral-950/80 text-neutral-200"
              }`}
            >
              <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
                {m.role === "user" ? "你" : "助手"}
              </div>
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          ))}
        </div>
        <div className="border-t border-neutral-800 p-4">
          <div className="mx-auto flex max-w-[48rem] gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              placeholder={activeId ? "输入消息…" : "请先创建会话"}
              disabled={!activeId || loading}
              rows={2}
              className="min-h-[44px] flex-1 resize-none rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => onSend()}
              disabled={!activeId || loading || !input.trim()}
              className="self-end rounded-lg bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-40"
            >
              {loading ? "…" : "发送"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
