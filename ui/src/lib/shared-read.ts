type PendingRead = {
  controller: AbortController;
  promise: Promise<unknown>;
  users: number;
  settled: boolean;
  abortTimer?: ReturnType<typeof setTimeout>;
};

const pending = new Map<string, PendingRead>();

// A read started before a write must not be reused by the subsequent refresh.
export function invalidatePendingReads() {
  pending.clear();
}

export function sharedRead<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
  signal?: AbortSignal | null,
): Promise<T> {
  if (signal?.aborted) return Promise.reject(signal.reason);
  let entry = pending.get(key);
  if (!entry) {
    const controller = new AbortController();
    entry = {
      controller,
      users: 0,
      settled: false,
      promise: Promise.resolve().then(() => {
        controller.signal.throwIfAborted();
        return load(controller.signal);
      }),
    };
    pending.set(key, entry);
    const current = entry;
    const settle = () => {
      current.settled = true;
      clearTimeout(current.abortTimer);
      if (pending.get(key) === current) pending.delete(key);
    };
    current.promise.then(settle, settle);
  }
  const current = entry;
  clearTimeout(current.abortTimer);
  current.users += 1;

  return new Promise<T>((resolve, reject) => {
    let finished = false;
    const release = () => {
      finished = true;
      signal?.removeEventListener("abort", abort);
      current.users -= 1;
    };
    const abort = () => {
      if (finished) return;
      release();
      reject(signal?.reason);
      if (current.users === 0 && !current.settled) {
        // React's development cleanup/setup cycle can resubscribe this turn.
        current.abortTimer = setTimeout(() => {
          if (current.users !== 0 || current.settled) return;
          if (pending.get(key) === current) pending.delete(key);
          current.controller.abort();
        }, 0);
      }
    };
    signal?.addEventListener("abort", abort, { once: true });
    current.promise.then(
      (value) => {
        if (finished) return;
        release();
        resolve(value as T);
      },
      (error: unknown) => {
        if (finished) return;
        release();
        reject(error);
      },
    );
  });
}
