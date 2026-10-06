export const GREETING = "hello";

/** Builds a greeting. */
export function helper(name: string): string {
  return `${GREETING} ${name}`;
}
