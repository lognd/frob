+++
id = "01M4HYH9CDNJSYEZQGKRZA7WX2"
title = "CAP: open(path, 'w') counts only as fs.read; mode-aware detection and Rust Path method receivers are not covered"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-10T03:43:31Z"
updated = "2026-10-10T03:43:31Z"
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-model/src/atoms.rs"]

[[acceptance]]
text = "Given open(p, 'w') in a node granting only fs.read, when CAP rules run, then CAP001 fs.write fires; a non-literal mode reports an Unresolved"
bound = false
+++

found while working ~2T7C4A9. Callee-text detection cannot see the open mode argument, so a write open satisfies a fs.read grant alone. Also Rust method calls on Path/PathBuf receivers (.exists, .read_dir, .metadata) are not in the vocabulary. Acceptance: open with a w/a/x/+ mode literal is fs.write; a non-literal mode is a May fs.write.
