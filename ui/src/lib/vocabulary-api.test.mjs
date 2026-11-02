import assert from "node:assert/strict";
import test from "node:test";
import { apiRequest, getRandomWord, getWordPage } from "./vocabulary-api.ts";

test("word queries encode filters and forward cancellation", async (t) => {
  const controller = new AbortController();
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ items: [] }),
  );
  await getWordPage(
    {
      group: "junior",
      page: 2,
      pageSize: 10,
      sortBy: "english",
      sortOrder: "desc",
      search: "中文 & word",
      locateId: 42,
      memberOf: ["junior", "senior"],
      seniorTypes: ["core", "extend"],
    },
    controller.signal,
  );
  const [path, init] = fetch.mock.calls[0].arguments;
  const params = new URL(path, "http://localhost").searchParams;
  assert.deepEqual(Object.fromEntries(params), {
    group: "junior",
    page: "2",
    page_size: "10",
    sort_by: "english",
    sort_order: "desc",
    q: "中文 & word",
    locate_id: "42",
    member_of: "junior,senior",
    senior_types: "core,extend",
  });
  assert.ok(init.signal instanceof AbortSignal);
  assert.equal(init.signal.aborted, false);
  await getWordPage({ group: "all" });
  assert.equal(fetch.mock.calls[1].arguments[0], "/api/words?group=all");
});

test("random selection is one uncached request with previous word exclusion", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ word: null, total: 0 }),
  );
  assert.deepEqual(await getRandomWord("junior", 42), { word: null, total: 0 });
  assert.equal(fetch.mock.calls.length, 1);
  assert.equal(fetch.mock.calls[0].arguments[0], "/api/words/random?group=junior&exclude_id=42");
  assert.equal(fetch.mock.calls[0].arguments[1].cache, "no-store");
});

test("concurrent identical API reads merge, but headers and writes stay distinct", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ total: 1 }));
  await Promise.all([apiRequest("/groups"), apiRequest("/groups")]);
  assert.equal(fetch.mock.calls.length, 1);
  await Promise.all([
    apiRequest("/groups", { headers: { "X-Test": "a" } }),
    apiRequest("/groups", { headers: { "X-Test": "b" } }),
    apiRequest("/words/1", { method: "PATCH" }),
    apiRequest("/words/1", { method: "PATCH" }),
  ]);
  assert.equal(fetch.mock.calls.length, 5);
});

test("equivalent read options merge regardless of property or header order", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json([]));
  await Promise.all([
    apiRequest("/groups", { cache: "no-store", credentials: "same-origin", headers: { "X-A": "a", "X-B": "b" } }),
    apiRequest("/groups", { headers: { "x-b": "b", "x-a": "a" }, credentials: "same-origin", cache: "no-store", method: "GET" }),
  ]);
  assert.equal(fetch.mock.calls.length, 1);
});

test("refresh after a write never joins a read started before the write", async (t) => {
  const old = Promise.withResolvers();
  let reads = 0;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    if (init?.method === "PATCH") return Response.json({ id: 1 });
    reads++;
    return reads === 1 ? old.promise : Response.json({ total: 2 });
  });
  const before = apiRequest("/groups");
  await new Promise((resolve) => setImmediate(resolve));
  await apiRequest("/words/1", { method: "PATCH" });
  assert.deepEqual(await apiRequest("/groups"), { total: 2 });
  old.resolve(Response.json({ total: 1 }));
  assert.deepEqual(await before, { total: 1 });
  assert.equal(reads, 2);
});

test("API helper reads JSON and forwards the request method and abort signal", async (t) => {
  const controller = new AbortController();
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ id: 1 }),
  );
  assert.deepEqual(
    await apiRequest("/words/1", {
      method: "PATCH",
      signal: controller.signal,
    }),
    { id: 1 },
  );
  assert.equal(fetch.mock.calls[0].arguments[0], "/api/words/1");
  assert.equal(fetch.mock.calls[0].arguments[1].signal, controller.signal);
});

test("DELETE success does not try to parse an empty response", async (t) => {
  t.mock.method(
    globalThis,
    "fetch",
    async () => new Response(null, { status: 204 }),
  );
  assert.equal(await apiRequest("/words/1", { method: "DELETE" }), undefined);
});

test("API helper shows validation messages and preserves server error details", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json(
      { detail: [{ msg: "Meaning is required" }] },
      { status: 422 },
    ),
  );
  await assert.rejects(apiRequest("/words/1"), /Meaning is required/);
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "Word already exists" }, { status: 409 }),
  );
  await assert.rejects(apiRequest("/words/1"), /Word already exists/);
});

test("API helper handles unavailable servers and malformed success responses", async (t) => {
  const fetch = t.mock.method(
    globalThis,
    "fetch",
    async () => new Response("Service unavailable", { status: 503 }),
  );
  await assert.rejects(
    apiRequest("/dictionary/lookup", undefined, "Lookup unavailable"),
    /Lookup unavailable/,
  );
  fetch.mock.mockImplementation(async () => new Response("not json"));
  await assert.rejects(apiRequest("/words"), /invalid response/);
});


test("mutations include the origin guard header and preserve JSON headers", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ id: 1 }));
  await apiRequest("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "learner" }),
  });
  const headers = new Headers(fetch.mock.calls[0].arguments[1].headers);
  assert.equal(headers.get("X-Envocab-Request"), "1");
  assert.equal(headers.get("Content-Type"), "application/json");
  await apiRequest("/auth/me");
  assert.equal(new Headers(fetch.mock.calls[1].arguments[1].headers).has("X-Envocab-Request"), false);
});
