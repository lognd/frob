import { test, expect } from "vitest";
import { fetchUser } from "./client";

test("fetchUser returns the id", () => {
  expect(fetchUser(7).id).toBe(7);
});
