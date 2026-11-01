import assert from "node:assert/strict";
import test from "node:test";
import { fittingPageSize } from "./vocabulary-layout.ts";

test("advances when capacity exceeds the lower tier by more than one row", () => {
  for (const [size, nextSize] of [[10, 20], [20, 50], [50, 100]]) {
    assert.equal(fittingPageSize(40 + (size + 1) * 49, 40, 49), size);
    assert.equal(fittingPageSize(40 + (size + 2) * 49 - 1, 40, 49), size);
    assert.equal(fittingPageSize(40 + (size + 2) * 49, 40, 49), nextSize);
  }
});

test("keeps ten as the minimum and one hundred as the maximum", () => {
  assert.equal(fittingPageSize(300, 40, 49), 10);
  assert.equal(fittingPageSize(10000, 40, 49), 100);
  assert.equal(fittingPageSize(0, 40, 49), 10);
  assert.equal(fittingPageSize(1000, 40, 0), 10);
});
