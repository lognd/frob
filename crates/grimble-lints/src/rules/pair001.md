<!-- mdtest: rule=PAIR001 -->
# PAIR001 acquire-without-release

An acquire (timer, listener, request, observer, subscription) with no release on the teardown path.

## What it does

Fires in TypeScript, TSX, JavaScript and JSX for a `useEffect`, `useLayoutEffect` or `useInsertionEffect` that starts a timer (`setInterval`, `setTimeout`, `requestAnimationFrame`), an event listener, a `fetch`, a `subscribe` or `addListener`, or an observer or socket (`IntersectionObserver`, `ResizeObserver`, `MutationObserver`, `WebSocket`, `EventSource`) and returns no cleanup that undoes it. A cleanup that releases a different handle, event type or handler does not pair the acquire, a `return` inside a nested function is not the effect's cleanup, and an `async` effect callback returns a promise, never a cleanup. A cleanup returned only under a branch, or a returned value the scan cannot read (an imported function), reports the rule Unresolved, never a guessed Warn. Other languages are not judged by this rule yet.

## Why it matters

An effect that starts work and never stops it leaks on every unmount and re-run: intervals keep firing against an unmounted component, listeners pile up, and a late response writes stale state.

## Remedy

Return a cleanup from the effect that undoes each acquire: `clearInterval(id)`, `removeEventListener` with the same type and handler, `controller.abort()` for a `fetch` given `controller.signal`, `unsubscribe()`, or `disconnect()` or `close()`.

## Examples

### Fires case 1

```tsx expect=fire file=src/Ticker.tsx
import { useEffect } from "react";

export function Ticker({ tick }: { tick: () => void }) {
  useEffect(() => {
    const id = setInterval(tick, 1000);
  }, [tick]);
  return null;
}
```

### Fires case 2

```jsx expect=fire file=src/Size.jsx
export function Size({ onResize }) {
  useEffect(() => {
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("scroll", onResize);
  }, [onResize]);
  return null;
}
```

### Clean case 3

```tsx expect=clean file=src/Ticker.tsx
import { useEffect } from "react";

export function Ticker({ tick }: { tick: () => void }) {
  useEffect(() => {
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [tick]);
  return null;
}
```

### Clean case 4

```tsx expect=clean file=src/Plain.tsx
export function helper() {
  const id = 1;
  return id;
}
```

### Unresolved case 5

```tsx expect=unresolved file=src/Ticker.tsx
import { stop } from "./stop";

export function Ticker({ tick }: { tick: () => void }) {
  useEffect(() => {
    setInterval(tick, 1000);
    return stop;
  }, [tick]);
  return null;
}
```
