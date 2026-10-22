<!-- mdtest: rule=COMP008 -->
# COMP008 code-props-mismatch

A code mapping that lists props lists exactly the component's props.

## What it does

Fires for a `[[code]]` entry whose `props` names a prop the spec lacks or omits one the spec declares.

## Why it matters

Spec and code that disagree on props have drifted apart.

## Remedy

Bring the code props and the `[[props]]` back in line.

## Examples

### An extra code prop fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[props]]
name = "label"
kind = "text"

[[code]]
framework = "react"
path = "src/Button.tsx"
export = "Button"
props = ["label", "icon"]
```

### Matching props are clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[props]]
name = "label"
kind = "text"

[[code]]
framework = "react"
path = "src/Button.tsx"
export = "Button"
props = ["label"]
```
