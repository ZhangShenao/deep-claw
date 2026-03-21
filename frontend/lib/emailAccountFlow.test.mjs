import test from "node:test";
import assert from "node:assert/strict";

import { createEmailAccountFlow } from "./emailAccountFlow.js";

test("createEmailAccountFlow returns ok when create and reload both succeed", async () => {
  const calls = [];
  const result = await createEmailAccountFlow(
    { email_address: "user@example.com" },
    {
      create: async (input) => {
        calls.push(["create", input.email_address]);
      },
      reload: async () => {
        calls.push(["reload"]);
      },
    },
  );

  assert.deepEqual(calls, [["create", "user@example.com"], ["reload"]]);
  assert.deepEqual(result, { ok: true, error: null });
});

test("createEmailAccountFlow returns error when create fails", async () => {
  const result = await createEmailAccountFlow(
    { email_address: "user@example.com" },
    {
      create: async () => {
        throw new Error("create failed");
      },
      reload: async () => {
        throw new Error("should not run");
      },
    },
  );

  assert.equal(result.ok, false);
  assert.match(result.error ?? "", /create failed/);
});
