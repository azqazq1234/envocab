import assert from "node:assert/strict";
import test from "node:test";
import { invalidatePendingReads, sharedRead } from "./shared-read.ts";

const flush = () => new Promise((resolve) => setImmediate(resolve));

function deferred() {
  return Promise.withResolvers();
}

test("simultaneous readers share one load and cancel independently", async () => {
  const work = deferred();
  let calls = 0;
  let networkSignal;
  const load = (signal) => {
    calls++;
    networkSignal = signal;
    return work.promise;
  };
  const first = new AbortController();
  const second = new AbortController();
  const a = sharedRead("independent", load, first.signal);
  const rejected = assert.rejects(a, { name: "AbortError" });
  const b = sharedRead("independent", load, second.signal);
  await flush();
  first.abort();
  await rejected;
  assert.equal(networkSignal.aborted, false);
  work.resolve({ total: 2 });
  assert.deepEqual(await b, { total: 2 });
  assert.equal(calls, 1);
});

test("development cleanup and immediate remount reuse the pending read", async () => {
  const work = deferred();
  let calls = 0;
  const load = () => { calls++; return work.promise; };
  const controller = new AbortController();
  const first = sharedRead("remount", load, controller.signal);
  const rejected = assert.rejects(first, { name: "AbortError" });
  controller.abort();
  const second = sharedRead("remount", load);
  await rejected;
  await flush();
  work.resolve(42);
  assert.equal(await second, 42);
  assert.equal(calls, 1);
});

test("last reader leaving aborts the network and permits a fresh request", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const work = deferred();
  const controller = new AbortController();
  let networkSignal;
  const read = sharedRead("leave", (signal) => {
    networkSignal = signal;
    return work.promise;
  }, controller.signal);
  const rejected = assert.rejects(read, { name: "AbortError" });
  await flush();
  controller.abort();
  await rejected;
  t.mock.timers.tick(0);
  assert.equal(networkSignal.aborted, true);
  const fresh = sharedRead("leave", async () => "fresh");
  work.reject(new DOMException("Aborted", "AbortError"));
  assert.equal(await fresh, "fresh");
});

test("completed reads and failures are not cached", async () => {
  let count = 0;
  const load = async () => ++count;
  assert.equal(await sharedRead("fresh", load), 1);
  assert.equal(await sharedRead("fresh", load), 2);
  await assert.rejects(sharedRead("fresh", async () => { throw new Error("offline"); }), /offline/);
  assert.equal(await sharedRead("fresh", load), 3);
});

test("invalidated old reads cannot replace or remove newer pending reads", async () => {
  const old = deferred();
  const fresh = deferred();
  const first = sharedRead("write", () => old.promise);
  invalidatePendingReads();
  const second = sharedRead("write", () => fresh.promise);
  old.resolve("old");
  assert.equal(await first, "old");
  const third = sharedRead("write", () => { throw new Error("must reuse new read"); });
  fresh.resolve("new");
  assert.deepEqual(await Promise.all([second, third]), ["new", "new"]);
});

test("already aborted subscribers do not start a network request", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(sharedRead("aborted", () => { throw new Error("must not run"); }, controller.signal), { name: "AbortError" });
});
