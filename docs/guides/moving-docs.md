# Moving docs without breaking references

Status: current
Owner: frob
Decisions: none

When a document, heading or section moves, record it in `docs/MOVED.toml` and let frob rewrite the
references.

```toml
[moved]
"docs/old.md" = "docs/new.md"
"docs/old.md#intro" = "docs/new.md#overview"
```

A row maps an old file or anchor to its new place. A merged heading maps onto the surviving one; a
removed or archived one maps to its archive path or a reason.

## Remapping

`frob doc remap` rewrites markdown links, `frob:doc` and `frob:describes` targets, `.grmb` refs and
`x.md section N` citations under `crates/` and `docs/`. Nothing under `notes/` changes.
Pass `--dry-run` to list the files without writing.

Every row's target must be a heading of the new file at HEAD. Otherwise the command refuses with exit 3,
names the row, and writes nothing.

## Before you remap

DOC002 and DRIFT002 name the new location when they fire on an old anchor listed in the map, so a
broken link tells you where it went.
