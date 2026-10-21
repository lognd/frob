<!-- mdtest: rule=STATE001 -->
# STATE001 interactive-states-missing

A screen declared `interactive` declares default, hover, focus-visible, active and disabled states. Each block is one screen file under `design/screens/` of a default-preset project.

## What it does

Fires for each screen file whose `kinds` lists `interactive` and whose `[[states]]` omit any of default, hover, focus-visible, active and disabled. Screens that do not list the kind, and projects with no screen files, are not judged.

## Why it matters

Interactive components need every interaction state designed; an undeclared state is shipped as the browser default or not at all.

## Remedy

Add the missing states to the screen file, drop the kind if it does not apply, or waive the rule with a reason.

## Examples

### A missing state fires

```toml expect=fire file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["interactive"]

[[states]]
id = "default"

[[states]]
id = "hover"

[[states]]
id = "focus-visible"

[[states]]
id = "active"
```

### Every state declared is clean

```toml expect=clean file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["interactive"]

[[states]]
id = "default"

[[states]]
id = "hover"

[[states]]
id = "focus-visible"

[[states]]
id = "active"

[[states]]
id = "disabled"
```
