"use client";

import type { NotificationRecord } from "@/lib/api";

type NotificationTrayProps = {
  notifications: NotificationRecord[];
  onOpen: (notification: NotificationRecord) => void;
};

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function NotificationTray({ notifications, onOpen }: NotificationTrayProps) {
  return (
    <section className="rounded-[26px] border border-white/8 bg-white/5 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.28em] text-neutral-500">Notifications</div>
          <h3 className="mt-1 text-base font-semibold text-white">邮件提醒</h3>
        </div>
        <div className="rounded-full border border-white/8 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.22em] text-neutral-500">
          {notifications.length}
        </div>
      </div>

      <div className="space-y-2">
        {notifications.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 px-3 py-4 text-sm leading-6 text-neutral-500">
            暂无站内通知。新的邮件摘要会通过 SSE 主动推送到这里。
          </div>
        ) : (
          notifications.slice(0, 6).map((notification) => (
            <button
              key={notification.id}
              type="button"
              onClick={() => onOpen(notification)}
              className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                notification.is_read
                  ? "border-white/8 bg-black/10 text-neutral-400 hover:bg-white/5"
                  : "border-emerald-300/22 bg-emerald-300/10 text-neutral-100 hover:bg-emerald-300/14"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{notification.title}</div>
                  <div className="mt-1 text-xs leading-5 text-neutral-400">{notification.body}</div>
                </div>
                <div className="shrink-0 text-[11px] text-neutral-500">{formatTime(notification.created_at)}</div>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
