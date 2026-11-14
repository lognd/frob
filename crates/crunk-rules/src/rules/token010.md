<!-- mdtest: rule=TOKEN010 -->
# TOKEN010 token-duration-too-long

Duration tokens stay within the configured bound. Each block is one source file in a project whose `crunk.toml` is the default preset, plus `[tokens] max_duration_ms = 1000` for the `max-duration` config.

## What it does

A duration token (`ms` or `s`) longer than `[tokens] max_duration_ms`, in its default or any mode value, fires. Without the key there is no bound.

## Why it matters

Motion past a second reads as lag, and a bound in one place keeps every animation inside it.

## Remedy

Shorten the duration or raise `max_duration_ms` on purpose.

## Examples

### A 4000ms duration over a 1000ms bound fires

```toml expect=fire config=max-duration file=design/tokens/motion.toml
[motion.slow]
value = "4000ms"
```

### A 200ms duration is clean

```toml expect=clean config=max-duration file=design/tokens/motion.toml
[motion.fast]
value = "200ms"
```
