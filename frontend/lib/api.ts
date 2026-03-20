const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export async function fetchConversations(): Promise<Conversation[]> {
  const r = await fetch(`${API_BASE}/api/conversations`);
  if (!r.ok) throw new Error(`list conversations: ${r.status}`);
  return r.json();
}

export async function createConversation(title?: string): Promise<Conversation> {
  const r = await fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title ?? null }),
  });
  if (!r.ok) throw new Error(`create conversation: ${r.status}`);
  return r.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/conversations/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`delete conversation: ${r.status}`);
}

export type HistoryMessage = { role: "user" | "assistant" | string; content: string };

export async function fetchMessages(conversationId: string): Promise<HistoryMessage[]> {
  const r = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`);
  if (!r.ok) throw new Error(`messages: ${r.status}`);
  return r.json();
}

export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "tool_start"; name: string; input: unknown }
  | { type: "tool_end"; name: string; output: unknown }
  | { type: "subagent"; phase: "start" | "end"; name: unknown }
  | { type: "message"; role: string; content: unknown }
  | { type: "done"; thread_id: string }
  | { type: "error"; message: string };

export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (ev: StreamEvent) => void,
): Promise<void> {
  const r = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`chat stream ${r.status}: ${t}`);
  }
  const reader = r.body?.getReader();
  if (!reader) throw new Error("no response body");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const ev = JSON.parse(raw) as StreamEvent;
        onEvent(ev);
      } catch {
        // ignore malformed
      }
    }
  }
}
