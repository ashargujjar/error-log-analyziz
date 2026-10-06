import assert from "node:assert/strict";
import test from "node:test";

import { ErrorLogClient, createClient, formatException } from "../src/index.js";

function response({ ok = true, status = 202, json = {}, text = "" } = {}) {
  return {
    ok,
    status,
    json: async () => json,
    text: async () => text,
  };
}

test("capture sends raw log to the configured endpoint", async () => {
  const requests = [];
  const client = new ErrorLogClient({
    apiKey: "test-api-key",
    endpoint: "http://backend.test/errors",
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      return response({
        json: { status: "pending", error_id: "error_123" },
      });
    },
  });

  const result = await client.capture("server crashed");

  assert.equal(result.ok, true);
  assert.equal(result.status, "pending");
  assert.equal(result.errorId, "error_123");
  assert.equal(requests[0].url, "http://backend.test/errors");
  assert.equal(requests[0].init.method, "POST");
  assert.equal(requests[0].init.headers.Authorization, "Bearer test-api-key");
  assert.equal(requests[0].init.headers["Content-Type"], "text/plain");
  assert.equal(requests[0].init.body, "server crashed");
});

test("captureException sends stack data", async () => {
  let sentBody = "";
  const client = createClient({
    apiKey: "test-api-key",
    fetchImpl: async (_url, init) => {
      sentBody = init.body;
      return response({ json: { status: "pending" } });
    },
  });

  await client.captureException(new Error("database failed"));

  assert.match(sentBody, /Error: database failed/);
});

test("capture retries retryable HTTP failures", async () => {
  let attempts = 0;
  const client = new ErrorLogClient({
    apiKey: "test-api-key",
    retryDelayMs: 0,
    fetchImpl: async () => {
      attempts += 1;
      if (attempts === 1) {
        return response({ ok: false, status: 500, text: "temporary failure" });
      }
      return response({ json: { status: "pending", error_id: "retry_ok" } });
    },
  });

  const result = await client.capture("retry me");

  assert.equal(attempts, 2);
  assert.equal(result.ok, true);
  assert.equal(result.errorId, "retry_ok");
});

test("capture returns failure result by default", async () => {
  const client = new ErrorLogClient({
    apiKey: "test-api-key",
    retries: 0,
    fetchImpl: async () =>
      response({ ok: false, status: 401, text: "invalid api key" }),
  });

  const result = await client.capture("auth fail");

  assert.equal(result.ok, false);
  assert.match(result.error, /HTTP 401/);
});

test("throwOnFailure throws for failed sends", async () => {
  const client = new ErrorLogClient({
    apiKey: "test-api-key",
    retries: 0,
    throwOnFailure: true,
    fetchImpl: async () => response({ ok: false, status: 401 }),
  });

  await assert.rejects(() => client.capture("auth fail"), /HTTP 401/);
});

test("formatException handles strings and plain objects", () => {
  assert.equal(formatException("raw log"), "raw log");
  assert.equal(formatException({ message: "plain object" }), '{\n  "message": "plain object"\n}');
});
