const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type EmailAccount = {
  id: string;
  email_address: string;
  provider_label: string;
  imap_host: string;
  imap_port: number;
  imap_security: string;
  auth_type: string;
  poll_interval_minutes: number;
  enabled: boolean;
  last_check_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EmailAccountCreateInput = {
  email_address: string;
  provider_label: string;
  imap_host: string;
  imap_port: number;
  imap_security?: string;
  auth_type?: string;
  credential: string;
  poll_interval_minutes: number;
  enabled?: boolean;
};

export type EmailDigest = {
  id: string;
  account_id: string;
  trigger_source: string;
  digest_scope: string;
  message_ids: string[];
  summary: string;
  key_points_json: Array<Record<string, unknown>>;
  action_suggestions_json: Array<Record<string, unknown>>;
  priority: string;
  created_at: string;
};

export type NotificationRecord = {
  id: string;
  type: string;
  account_id: string | null;
  digest_id: string | null;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

export type EmailCheckResult = {
  digest_id: string;
  account_id: string;
  trigger_source: string;
  new_message_count: number;
  summary: string;
};

export type NotificationStreamEvent =
  | {
      type: "notification";
      id: string;
      notification_type: string;
      title: string;
      body: string;
      created_at: string | null;
      payload: {
        digest_id: string | null;
        account_id: string | null;
      };
    }
  | { type: "heartbeat" }
  | { type: "error"; message: string };

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

export async function fetchEmailAccounts(): Promise<EmailAccount[]> {
  const r = await fetch(`${API_BASE}/api/email/accounts`);
  if (!r.ok) throw new Error(`list email accounts: ${r.status}`);
  return r.json();
}

export async function createEmailAccount(input: EmailAccountCreateInput): Promise<EmailAccount> {
  const r = await fetch(`${API_BASE}/api/email/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      imap_security: "ssl_tls",
      auth_type: "app_password",
      enabled: true,
      ...input,
    }),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`create email account ${r.status}: ${text}`);
  }
  return r.json();
}

export async function fetchEmailDigests(): Promise<EmailDigest[]> {
  const r = await fetch(`${API_BASE}/api/email/digests`);
  if (!r.ok) throw new Error(`list email digests: ${r.status}`);
  return r.json();
}

export async function runEmailCheck(accountId: string): Promise<EmailCheckResult> {
  const r = await fetch(`${API_BASE}/api/email/accounts/${accountId}/check-now`, {
    method: "POST",
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`check email now ${r.status}: ${text}`);
  }
  return r.json();
}

export async function fetchNotifications(): Promise<NotificationRecord[]> {
  const r = await fetch(`${API_BASE}/api/notifications`);
  if (!r.ok) throw new Error(`list notifications: ${r.status}`);
  return r.json();
}

export async function markNotificationRead(notificationId: string): Promise<NotificationRecord> {
  const r = await fetch(`${API_BASE}/api/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`mark notification read ${r.status}: ${text}`);
  }
  return r.json();
}

export function streamNotifications(
  onEvent: (ev: NotificationStreamEvent) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/notifications/stream`);

  source.onmessage = (message) => {
    if (!message.data) return;
    try {
      onEvent(JSON.parse(message.data) as NotificationStreamEvent);
    } catch {
      // ignore malformed events
    }
  };

  source.onerror = () => {
    onEvent({ type: "error", message: "notification stream disconnected" });
  };

  return () => source.close();
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
  | { type: "subagent"; phase: "start" | "end"; name: unknown; output?: unknown }
  | { type: "message"; role: string; content: unknown }
  | { type: "done"; thread_id: string }
  | { type: "error"; message: string };

export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (ev: StreamEvent) => void,
  options?: { signal?: AbortSignal },
): Promise<void> {
  const r = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
    signal: options?.signal,
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
