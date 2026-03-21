"use client";

import type { EmailDigest } from "@/lib/api";

type EmailDigestListProps = {
  digests: EmailDigest[];
  selectedDigestId: string | null;
  onSelect: (digestId: string) => void;
};

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function EmailDigestList({
  digests,
  selectedDigestId,
  onSelect,
}: EmailDigestListProps) {
  const selectedDigest = digests.find((digest) => digest.id === selectedDigestId) ?? digests[0] ?? null;

  return (
    <section className="rounded-[26px] border border-white/8 bg-white/5 p-4">
      <div className="mb-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.28em] text-neutral-500">Digests</div>
        <h3 className="mt-1 text-base font-semibold text-white">邮件摘要</h3>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-2">
          {digests.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 px-3 py-4 text-sm leading-6 text-neutral-500">
              还没有生成邮件摘要。先添加邮箱，或者对某个邮箱执行一次检查。
            </div>
          ) : (
            digests.slice(0, 8).map((digest) => (
              <button
                key={digest.id}
                type="button"
                onClick={() => onSelect(digest.id)}
                className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                  digest.id === selectedDigest?.id
                    ? "border-white/14 bg-white/10"
                    : "border-white/8 bg-black/10 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-white">{digest.trigger_source === "manual" ? "手动检查" : "自动检查"}</div>
                  <div className="text-[11px] text-neutral-500">{formatTime(digest.created_at)}</div>
                </div>
                <div className="mt-2 text-xs leading-5 text-neutral-400">{digest.summary}</div>
              </button>
            ))
          )}
        </div>

        <div className="rounded-2xl border border-white/8 bg-black/12 px-4 py-4">
          {selectedDigest ? (
            <>
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-white">摘要详情</div>
                <div className="rounded-full border border-white/8 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.22em] text-neutral-500">
                  {selectedDigest.priority}
                </div>
              </div>
              <div className="mt-3 text-sm leading-7 text-neutral-200">{selectedDigest.summary}</div>

              <div className="mt-4">
                <div className="text-[11px] font-medium uppercase tracking-[0.24em] text-neutral-500">Next Actions</div>
                <div className="mt-2 space-y-2">
                  {selectedDigest.action_suggestions_json.length === 0 ? (
                    <div className="text-sm text-neutral-500">当前没有建议动作。</div>
                  ) : (
                    selectedDigest.action_suggestions_json.map((item, index) => (
                      <div key={`${selectedDigest.id}-action-${index}`} className="rounded-2xl border border-white/8 bg-white/4 px-3 py-3 text-sm leading-6 text-neutral-300">
                        <div className="font-medium text-white">{String(item.action ?? "待处理事项")}</div>
                        {"reason" in item && item.reason ? (
                          <div className="mt-1 text-xs text-neutral-400">{String(item.reason)}</div>
                        ) : null}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="text-sm leading-6 text-neutral-500">选择一条摘要查看详情。</div>
          )}
        </div>
      </div>
    </section>
  );
}
