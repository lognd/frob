<!-- mdtest: rule=TICK005 -->
# TICK005 private-term

A ledger file or changelog fragment holds a term the local privacy rules forbid.

## What it does

Private terms are defined only in local files (the user config `frob/privacy.toml` and `frob/privacy.toml` under the git common dir), never in a committed file. Neither file is created by frob (`frob init` and `frob doctor` only name them); an existing file is never overwritten. Each file holds `[[rule]]` tables:

```toml
[[rule]]
pattern = "hush-term"   # the text or regex to forbid
replace = "codename"    # the label a match becomes; findings name this, never the term
regex = false           # default false
case_sensitive = true   # default true
```

The rule is local-only: it runs where those rules exist and reports nothing where they do not. A finding names the rule's replace label and a hash of its pattern, never the term.

## Why it matters

A committed private term is published to everyone who clones the repository.

## Remedy

`frob ticket doctor --fix` replaces the term in one forward commit (history is never rewritten).

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
