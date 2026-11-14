<!-- mdtest: rule=COMP007 -->
# COMP007 code-mapping-missing

A component that is ready or completed maps to the code that implements it.

## What it does

Fires for a `ready` or `completed` component with no `[[code]]` entry, for a mapping with a blank framework, path or export, and for a mapping whose path does not exist on disk (resolved against the project root).

## Why it matters

A locked design with no implementation named cannot be checked against the code.

## Remedy

Add a `[[code]]` entry naming the framework, file and export, and make sure the file exists.

## Examples

### A locked component without code fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
status = "ready"
```

### A mapping to a path that does not exist fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
status = "ready"

[[code]]
framework = "react"
path = "src/Missing.tsx"
export = "Button"
```

### A mapped component is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"
status = "ready"

[[code]]
framework = "react"
path = "src/Button.tsx"
export = "Button"
```

```tsx file=src/Button.tsx
export function Button() {
  return <button />;
}
```
