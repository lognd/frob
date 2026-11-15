<!-- mdtest: rule=TYPING004 -->
# TYPING004 unvalidated-boundary-cast

Network or file data cast to a declared type without validation.

## What it does

Fires in TypeScript and TSX for an `as T` cast whose operand is a `.json()` call (a `fetch` body), a `JSON.parse(..)` call, or a name bound from one of those that no validator call (`schema.parse(x)`, `safeParse`, `parseAsync`, `assert`, `validate`, `decode`) ever receives. Casts to `unknown`, `any` and `const` declare no shape and are not reported. The rule is advisory.

## Why it matters

`as User` is a promise to the compiler, not a check: when the server or the file changes shape, the wrong type flows into the program and fails far from the boundary.

## Remedy

Parse the value with a schema at the boundary, for example `UserSchema.parse(await res.json())`, and use the parsed result.

## Examples

### Fires case 1

```typescript expect=fire file=src/api.ts
export async function load(res: Response) {
  const user = (await res.json()) as User;
  return user;
}
```

### Fires case 2

```typescript expect=fire file=src/config.ts
export function read(raw: string) {
  return JSON.parse(raw) as Config;
}
```

### Clean case 3

```typescript expect=clean file=src/api.ts
export async function load(res: Response) {
  return UserSchema.parse(await res.json());
}
```
