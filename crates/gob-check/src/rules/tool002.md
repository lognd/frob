<!-- mdtest: rule=TOOL002 -->
# TOOL002 tool-finding-unmapped

A bound tool reported a finding that no frob rule id covers.

## What it does

A bound tool reported a finding that no frob rule id covers.

## Why it matters

A finding with no rule id would otherwise be dropped; the advisory keeps it visible until the tool id is mapped.

## Remedy

The message starts with `tool/id` (for example `zizmor/self-repository`). Map the tool id to a rule through the stage's `id_map`, or accept the finding with `frob:accept TOOL002`. Always Advisory.

## Examples

### Fires case 1

```toml expect=fire file=frob.toml
[[check.tool]]
name = "zizmor"
parser = "zizmor-json-v1"
# a finding with an id absent from id_map reports TOOL002
```

### Clean case 1

```toml expect=clean file=frob.toml
[[check.tool]]
name = "zizmor"
parser = "zizmor-json-v1"
id_map = { "self-repository" = "CI001" }
```
