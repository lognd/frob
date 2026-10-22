<!-- mdtest: rule=COMP009 -->
# COMP009 component-hash-stale

A component that is ready or completed records the hash of its content and the token values it binds.

## What it does

Fires for a `ready` or `completed` component whose `content_hash` is missing or differs from the hash of its content and its bound tokens. The finding gives the expected hash.

## Why it matters

The hash is how a locked component notices that it, or a token under it, changed.

## Remedy

Record the expected hash, or set the status to `changed` while the component is being revised.

## Examples

### A missing hash fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
status = "ready"
```

### A draft needs no hash

```toml expect=clean file=design/components/button.component.toml
name = "button"
```
