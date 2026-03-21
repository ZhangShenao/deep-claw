"use client";

import { useState } from "react";

import type { EmailAccount, EmailAccountCreateInput } from "@/lib/api";

type EmailAccountsPanelProps = {
  accounts: EmailAccount[];
  creating: boolean;
  checkingAccountId: string | null;
  onCreate: (input: EmailAccountCreateInput) => Promise<void>;
  onCheckNow: (accountId: string) => Promise<void>;
};

const initialForm = {
  email_address: "",
  provider_label: "",
  imap_host: "",
  imap_port: 993,
  credential: "",
  poll_interval_minutes: 15,
};

export default function EmailAccountsPanel({
  accounts,
  creating,
  checkingAccountId,
  onCreate,
  onCheckNow,
}: EmailAccountsPanelProps) {
  const [form, setForm] = useState(initialForm);

  return (
    <section className="rounded-[26px] border border-white/8 bg-white/5 p-4">
      <div className="mb-3">
        <div className="text-[11px] font-medium uppercase tracking-[0.28em] text-neutral-500">Mailbox</div>
        <h3 className="mt-1 text-base font-semibold text-white">邮箱接入</h3>
      </div>

      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate({
            ...form,
            imap_port: Number(form.imap_port),
            poll_interval_minutes: Number(form.poll_interval_minutes),
          }).then(() => setForm(initialForm));
        }}
      >
        <input
          value={form.email_address}
          onChange={(event) => setForm((current) => ({ ...current, email_address: event.target.value }))}
          placeholder="邮箱地址"
          className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
        />
        <input
          value={form.provider_label}
          onChange={(event) => setForm((current) => ({ ...current, provider_label: event.target.value }))}
          placeholder="邮箱标识（如 Gmail / Outlook）"
          className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
        />
        <div className="grid gap-3 md:grid-cols-[1fr_110px]">
          <input
            value={form.imap_host}
            onChange={(event) => setForm((current) => ({ ...current, imap_host: event.target.value }))}
            placeholder="IMAP Host"
            className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
          />
          <input
            type="number"
            value={form.imap_port}
            onChange={(event) => setForm((current) => ({ ...current, imap_port: Number(event.target.value) }))}
            className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
          />
        </div>
        <div className="grid gap-3 md:grid-cols-[1fr_110px]">
          <input
            value={form.credential}
            onChange={(event) => setForm((current) => ({ ...current, credential: event.target.value }))}
            placeholder="App Password / Token"
            className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
          />
          <input
            type="number"
            value={form.poll_interval_minutes}
            onChange={(event) =>
              setForm((current) => ({ ...current, poll_interval_minutes: Number(event.target.value) }))
            }
            className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3 text-sm text-white placeholder:text-neutral-500 focus:border-emerald-300/30 focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={
            creating ||
            !form.email_address.trim() ||
            !form.imap_host.trim() ||
            !form.credential.trim()
          }
          className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-medium text-[#082018] transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:bg-white/12 disabled:text-neutral-500"
        >
          {creating ? "添加中" : "添加邮箱"}
        </button>
      </form>

      <div className="mt-4 space-y-2">
        {accounts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 px-3 py-4 text-sm leading-6 text-neutral-500">
            还没有接入邮箱。添加一个 IMAP 账户后，可以在这里手动触发检查。
          </div>
        ) : (
          accounts.map((account) => (
            <div key={account.id} className="rounded-2xl border border-white/8 bg-black/12 px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{account.email_address}</div>
                  <div className="mt-1 text-xs text-neutral-500">
                    {account.imap_host}:{account.imap_port} · 每 {account.poll_interval_minutes} 分钟
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onCheckNow(account.id)}
                  disabled={checkingAccountId === account.id}
                  className="rounded-full border border-white/8 bg-white/5 px-3 py-1.5 text-xs text-neutral-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:text-neutral-500"
                >
                  {checkingAccountId === account.id ? "检查中" : "Check Now"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
