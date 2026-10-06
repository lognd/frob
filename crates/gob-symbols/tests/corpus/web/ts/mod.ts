import { readFileSync } from "node:fs";
import { helper } from "./util";

export interface User {
  id: number;
}

/** Greets a user. */
export function greet(name: string): string {
  return helper(name);
}

export class Store {
  get(id: number): User {
    readFileSync("users.json");
    return { id };
  }
}
