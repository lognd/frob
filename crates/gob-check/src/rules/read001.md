<!-- mdtest: rule=READ001 -->
# READ001 unreadable-file

A walked file could not be read, so no rule examined it.

## What it does

Raised as a required Unresolved finding for every file the walk includes but the analysis cannot read: content that is not UTF-8, a permission failure or any other read error, or a file over `[check] size_cap`. Such a file must never look clean. Fix the encoding or permissions, raise `size_cap`, or list the file under `[check] exclude` when it is binary or generated; an excluded file is never walked, read or reported.

## Why it matters

A file no rule read would otherwise look clean, hiding every finding it might carry.

## Remedy

Follow the guidance above.

## Examples

### Fires case 1

```text expect=fire file=data/blob.bin
not utf-8: \xff\xfe
```

### Clean case 1

```text expect=clean file=data/blob.bin
plain utf-8 text
```
