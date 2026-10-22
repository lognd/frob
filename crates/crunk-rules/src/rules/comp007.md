<!-- mdtest: rule=COMP007 -->
# COMP007 code-mapping-missing

A component that is ready or completed maps to the code that implements it.

## What it does

Fires for a `ready` or `completed` component with no `[[code]]` entry, and for a mapping with a blank framework, path or export.

## Why it matters

A locked design with no implementation named cannot be checked against the code.

## Remedy

Add a `[[code]]` entry naming the framework, file and export.

## Examples

### A locked component without code fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
status = "ready"
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
