<!-- mdtest: rule=COMP003 -->
# COMP003 states-invalid

A component declares at least one state, each with a distinct id.

## What it does

Fires for a component with no `[[states]]`, and for a state whose id is blank or repeated.

## Why it matters

The state list is what STATE001 and its siblings judge; an empty or ambiguous list judges nothing.

## Remedy

Declare the states of the component, each once.

## Examples

### No states fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
```

### A repeated state fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[states]]
id = "default"

[[states]]
id = "default"
```

### Distinct states are clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[states]]
id = "default"

[[states]]
id = "hover"
```
