import assert from "node:assert/strict";
import test from "node:test";
import {
  createDictionaryLookup,
  checkWordAvailability,
} from "./dictionary-lookup.ts";

const entry = (term) => ({
  term,
  phonetic: "",
  source: "ECDICT",
  meanings: [],
});
const flush = () => new Promise((resolve) => setImmediate(resolve));

function setup(t, lookup, checkAvailability) {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"], now: 0 });
  const states = [];
  const calls = [];
  const controller = createDictionaryLookup(
    (state) => states.push(state),
    lookup ??
      ((word, signal) => {
        calls.push({ word, signal, at: Date.now() });
        return Promise.resolve(entry(word));
      }),
    checkAvailability,
  );
  t.after(() => controller.dispose());
  return { controller, calls, states };
}

test("does not query empty or invalid input", async (t) => {
  const { controller, calls } = setup(t);
  for (const value of ["", ".", "123", "word?", "x".repeat(101)]) {
    controller.search(value);
    t.mock.timers.tick(2000);
  }
  await flush();
  assert.equal(calls.length, 0);
});

test("waits 1500ms for single-letter queries and reuses cached results", async (t) => {
  const { controller, calls, states } = setup(t);
  for (const value of [" I ", "a", "b", "b."]) {
    const previousCalls = calls.length;
    controller.search(value);
    t.mock.timers.tick(1499);
    assert.equal(calls.length, previousCalls);
    t.mock.timers.tick(1);
    await flush();
    assert.equal(calls.length, previousCalls + 1);
    assert.equal(states.at(-1).entry.term, value.trim());
  }
  controller.search("I");
  assert.equal(states.at(-1).entry.term, "I");
  t.mock.timers.tick(2000);
  await flush();
  assert.equal(calls.length, 4);
});

test("typing beyond one letter cancels its lookup and uses the 500ms delay", async (t) => {
  const { controller, calls } = setup(t);
  controller.search("i");
  t.mock.timers.tick(1000);
  controller.search("in");
  t.mock.timers.tick(499);
  assert.equal(calls.length, 0);
  t.mock.timers.tick(1);
  await flush();
  assert.deepEqual(calls.map((call) => call.word), ["in"]);
  t.mock.timers.tick(2000);
  await flush();
  assert.equal(calls.length, 1);
});

test("queries abbreviations with periods intact", async (t) => {
  const { controller, calls, states } = setup(t);
  for (const value of [" A.M. ", "p.m."]) {
    controller.search(value);
    t.mock.timers.tick(800);
    await flush();
    assert.equal(states.at(-1).entry.term, value.trim());
  }
  assert.deepEqual(calls.map((call) => call.word), ["A.M.", "p.m."]);
});

test("debounces typing for 500ms and sends the latest word", async (t) => {
  const { controller, calls, states } = setup(t);
  controller.search("bo");
  t.mock.timers.tick(300);
  controller.search("book");
  t.mock.timers.tick(499);
  assert.equal(calls.length, 0);
  t.mock.timers.tick(1);
  await flush();
  assert.deepEqual(
    calls.map((call) => call.word),
    ["book"],
  );
  assert.equal(states.at(-1).entry.term, "book");
});

test("throttles request starts to at least 800ms apart", async (t) => {
  const { controller, calls } = setup(t);
  controller.search("book");
  t.mock.timers.tick(500);
  await flush();
  controller.search("read");
  t.mock.timers.tick(799);
  assert.equal(calls.length, 1);
  t.mock.timers.tick(1);
  await flush();
  assert.equal(calls.length, 2);
  assert.equal(calls[1].at - calls[0].at, 800);
});

test("reuses successful results across whitespace changes", async (t) => {
  const { controller, calls, states } = setup(t);
  controller.search("book");
  t.mock.timers.tick(500);
  await flush();
  controller.search(" book ");
  assert.equal(states.at(-1).entry.term, "book");
  t.mock.timers.tick(2000);
  await flush();
  assert.equal(calls.length, 1);
});

test("case pairs use separate lookups, availability checks, and cache entries", async (t) => {
  const checked = [];
  const { controller, calls, states } = setup(t, undefined, async (word) => {
    checked.push(word);
    return word !== "China";
  });
  controller.search("China");
  t.mock.timers.tick(500);
  await flush();
  assert.equal(states.at(-1).entry.term, "China");
  assert.equal(states.at(-1).duplicate, true);
  controller.search("china");
  t.mock.timers.tick(800);
  await flush();
  assert.equal(states.at(-1).entry.term, "china");
  assert.equal(states.at(-1).duplicate, false);
  controller.search("China");
  t.mock.timers.tick(800);
  await flush();
  assert.deepEqual(calls.map((call) => call.word), ["China", "china"]);
  assert.deepEqual(checked, ["China", "china", "China"]);
});

test("aborts obsolete requests and ignores late results", async (t) => {
  const requests = [];
  const { controller, states } = setup(
    t,
    (word, signal) =>
      new Promise((resolve) => requests.push({ word, signal, resolve })),
  );
  controller.search("book");
  t.mock.timers.tick(500);
  controller.search("read");
  assert.equal(requests[0].signal.aborted, true);
  t.mock.timers.tick(800);
  requests[1].resolve(entry("read"));
  await flush();
  requests[0].resolve(entry("book"));
  await flush();
  assert.equal(states.at(-1).entry.term, "read");
});

test("closing cancels pending and active lookups", async (t) => {
  const requests = [];
  const { controller, states } = setup(
    t,
    (word, signal) =>
      new Promise((resolve) => requests.push({ signal, resolve })),
  );
  controller.search("book");
  controller.reset();
  t.mock.timers.tick(1000);
  assert.equal(requests.length, 0);
  controller.search("read");
  t.mock.timers.tick(500);
  controller.reset();
  assert.equal(requests[0].signal.aborted, true);
  requests[0].resolve(entry("read"));
  await flush();
  assert.equal(states.at(-1).entry, null);
  assert.equal(states.at(-1).error, "");
});

test("times out and reports an error without retaining a loading state", async (t) => {
  const { controller, states } = setup(
    t,
    (_word, signal) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        );
      }),
  );
  controller.search("book");
  t.mock.timers.tick(500);
  t.mock.timers.tick(15000);
  await flush();
  assert.match(states.at(-1).error, /timed out/);
  assert.equal(states.at(-1).loading, false);
});

test("cached dictionary entries are checked again after a word is saved", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"], now: 0 });
  const states = [];
  let exists = false;
  let lookups = 0;
  let checks = 0;
  const controller = createDictionaryLookup(
    (state) => states.push(state),
    async (word) => {
      lookups++;
      return entry(word);
    },
    async () => {
      checks++;
      return !exists;
    },
  );
  t.after(() => controller.dispose());
  controller.search("book");
  t.mock.timers.tick(500);
  await flush();
  assert.equal(states.at(-1).entry.term, "book");
  assert.equal(states.at(-1).duplicate, false);
  exists = true;
  controller.reset();
  controller.search(" book ");
  assert.equal(states.at(-1).entry, null);
  t.mock.timers.tick(800);
  await flush();
  assert.equal(lookups, 1);
  assert.equal(checks, 2);
  assert.equal(states.at(-1).entry.term, "book");
  assert.equal(states.at(-1).duplicate, true);
  assert.equal(states.at(-1).error, "");
  controller.search("read");
  assert.equal(states.at(-1).duplicate, false);
});

test("database check failures prevent adding even when dictionary lookup succeeds", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"], now: 0 });
  const states = [];
  const controller = createDictionaryLookup(
    (state) => states.push(state),
    async (word) => entry(word),
    async () => {
      throw new Error("Unable to check existing words.");
    },
  );
  t.after(() => controller.dispose());
  controller.search("book");
  t.mock.timers.tick(500);
  await flush();
  assert.equal(states.at(-1).entry, null);
  assert.equal(states.at(-1).loading, false);
  assert.match(states.at(-1).error, /Unable to check/);
});

test("availability checks use the current group, bypass HTTP cache, and forward cancellation", async (t) => {
  const signal = new AbortController().signal;
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ exists: true }),
  );
  assert.equal(await checkWordAvailability("junior", "book", signal), false);
  const [url, options] = fetch.mock.calls[0].arguments;
  assert.equal(url, "/api/words/exists?group=junior&term=book");
  assert.equal(options.cache, "no-store");
  assert.ok(options.signal instanceof AbortSignal);
  assert.equal(options.signal.aborted, false);
});
