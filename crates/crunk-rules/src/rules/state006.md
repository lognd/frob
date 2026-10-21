<!-- mdtest: rule=STATE006 -->
# STATE006 game-states-missing

A screen declared `game` declares menu-default, pause, disconnect, low-hull and death states. Each block is one screen file under `design/screens/` of a default-preset project.

## What it does

Fires for each screen file whose `kinds` lists `game` and whose `[[states]]` omit any of menu-default, pause, disconnect, low-hull and death. Screens that do not list the kind, and projects with no screen files, are not judged.

## Why it matters

Game screens that skip pause, disconnect, low-hull or death states leave the moments that matter most unstyled.

## Remedy

Add the missing states to the screen file, drop the kind if it does not apply, or waive the rule with a reason.

## Examples

### A missing state fires

```toml expect=fire file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["game"]

[[states]]
id = "menu-default"

[[states]]
id = "pause"

[[states]]
id = "disconnect"

[[states]]
id = "low-hull"
```

### Every state declared is clean

```toml expect=clean file=design/screens/home.screen.toml
id = "home"
entry = "/"
kinds = ["game"]

[[states]]
id = "menu-default"

[[states]]
id = "pause"

[[states]]
id = "disconnect"

[[states]]
id = "low-hull"

[[states]]
id = "death"
```
