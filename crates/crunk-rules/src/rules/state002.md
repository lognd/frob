<!-- mdtest: rule=STATE002 -->
# STATE002 data-states-missing

A screen declared `data_bound` declares loading, empty, error and partial states. Each block is one screen file under `design/screens/` of a default-preset project.

## What it does

Fires for each screen file whose `kinds` lists `data_bound` and whose `[[states]]` omit any of loading, empty, error and partial. Screens that do not list the kind, and projects with no screen files, are not judged.

## Why it matters

A screen fed by data spends most of its life outside the happy path; an undesigned loading, empty, error or partial state is what users meet first.

## Remedy

Add the missing states to the screen file, drop the kind if it does not apply, or waive the rule with a reason.

## Examples

### A missing state fires

```toml expect=fire file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["data_bound"]

[[states]]
id = "loading"

[[states]]
id = "empty"

[[states]]
id = "error"
```

### Every state declared is clean

```toml expect=clean file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["data_bound"]

[[states]]
id = "loading"

[[states]]
id = "empty"

[[states]]
id = "error"

[[states]]
id = "partial"
```
