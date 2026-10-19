<!-- mdtest: rule=PATH003 -->
# PATH003 path-in-command-line

A path interpolated into one command-line string instead of passed as its own argument.

## What it does

Fires when a path-derived string is interpolated into one command-line string: a `format!` into a shell command, an `sh -c` body, a git config value that git runs, a `.ps1` body. A language whose adapter has no path-conversion roles is Unresolved, never clean.

## Why it matters

A path with a space, a backslash or a drive letter is split or unescaped by the shell, and quoting differs between hosts.

## Remedy

Pass each path as its own argument; where one string is unavoidable, use the platform's quoting helper.

## Examples

### Fires case 1

```rust expect=fire file=src/lib.rs
use std::path::Path;
use std::process::Command;

fn install(repo: &Path, exe: &Path) {
    let driver = format!("{} merge %O %A %B", exe.display());
    Command::new("git").arg("config").arg(driver).current_dir(repo);
}
```

### Clean case 2

```rust expect=clean file=src/lib.rs
use std::path::Path;
use std::process::Command;

fn install(repo: &Path, exe: &Path) {
    Command::new("git").arg("config").arg(exe).current_dir(repo);
}
```

### Unresolved case 3

```typescript expect=unresolved file=src/a.ts
export function allowed(p: string): boolean {
  return p.startsWith("src/");
}
```
