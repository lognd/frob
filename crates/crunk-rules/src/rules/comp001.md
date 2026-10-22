<!-- mdtest: rule=COMP001 -->
# COMP001 props-invalid

A component prop is named once, an enum lists its values, and a default is one of them. Each block is one component file under `design/components/`.

## What it does

Fires for each `[[props]]` entry that has a blank or repeated name, an enum with no or repeated values or a default outside them, values or `axis` on a non-enum, or a slot whose `min` exceeds its `max`.

## Why it matters

A prop the code cannot honour makes the spec and the implementation disagree before a line is written.

## Remedy

Name every prop once, list the enum values, and pick the default from them.

## Examples

### A default outside the values fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[props]]
name = "size"
kind = "enum"
values = ["sm", "lg"]
default = "md"
```

### A well-formed enum is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[props]]
name = "size"
kind = "enum"
values = ["sm", "lg"]
default = "sm"
```
