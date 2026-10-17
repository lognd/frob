<!-- mdtest: rule=TOOL001 -->
# TOOL001 tool-stage-failed

A configured tool stage (`[[check.tool]]`) exited nonzero, timed out or could not start.

## What it does

A configured tool stage (`[[check.tool]]`) exited nonzero, timed out or could not start.

## Why it matters

A failed stage means the tool's checks did not run to completion, so its findings cannot be trusted as a clean result.

## Remedy

The finding names the stage and its exit status. Run the stage's command by hand to see its output, fix what it reports, or set `fail_on_nonzero` to false when the stage is advisory.

## Examples

### Fires case 1

```toml expect=fire file=frob.toml
[[check.tool]]
name = "lint"
command = ["false"]
```

### Clean case 1

```toml expect=clean file=frob.toml
[[check.tool]]
name = "lint"
command = ["true"]
```
