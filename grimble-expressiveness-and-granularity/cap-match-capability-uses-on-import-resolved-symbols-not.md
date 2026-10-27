+++
id = "01M5XNNHJ0ES2PB6ZKAD36SRKP"
title = "CAP: match capability uses on import-resolved symbols, not callee spelling (aliases, from-imports, fn values, name collisions)"
type = "security"
category = "todo"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-27T03:15:08Z"
idempotency_key = "grimble-expr-alias-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/gob-symbols/src/**", "crates/grimble-bind/tests/**"]

[[acceptance]]
text = "fixtures for each repro above fire CAP001 (or Unresolved for the dynamic getattr/import_module forms), with negative fixtures for a shadowed local name, a string and a comment"
bound = false

[[acceptance]]
text = "a repository-local type named Command does not hide std::process::Command::new or tokio::process::Command::new"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. observe() (caps.rs:422-505) only considers Calls edges with to=None and matches the callee TEXT against vocab spellings (names_callee caps.rs:99-110). Repros, all zero CAP001: Rust `use std::fs::read_to_string as slurp; slurp(..)`, `use std::process::Command as Cmd; Cmd::new(..)`, `let f: fn(&str)->_ = std::fs::remove_file; f(..)`; Python `import subprocess as sp; sp.run`, `from subprocess import run; run`, `getattr(os, 'system')`, `importlib.import_module('subprocess').run`. Name collision: when the repo defines any `Command::new`, `std::process::Command::new("sh")` resolves by name to the local item (to is Some) and the spawn disappears. Truncated callee text (caps.rs:455-458) drops the qualifier. The Rust adapter already has 'lexical+imports' resolve_ref (docs/reference/languages.md); use it to canonicalise the callee to a fully qualified path before vocab matching, treat function-valued references as uses, and make dynamic dispatch through getattr/import_module an Unresolved May use.
