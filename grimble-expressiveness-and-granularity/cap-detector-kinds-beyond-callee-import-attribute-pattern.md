+++
id = "01M5XNNJHXH8FFQ9JHJP21FHB9"
title = "CAP detector kinds beyond callee: import, attribute, pattern (GRL) and query rows"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:09Z"
updated = "2026-10-28T12:55:58Z"
idempotency_key = "grimble-expr-detkinds-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness", "no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-model/src/model.rs", "crates/gob-pattern/**", "crates/gob-packs/src/tier1/**"]

[[acceptance]]
text = "a pack can declare an attribute detector that makes Rust unsafe blocks an unsafe-atom use, and an import detector for Python ctypes"
bound = false

[[acceptance]]
text = "a pack can declare a GRL pattern detector (for example subprocess.run with shell=True as process.spawn.shell) with firing and clean examples"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. DetectorKind (registry.rs:15-30) lists Callee, Import, Attribute, Macro, Pattern, Lexical, NotApplicable, but observe() only implements callee vocabularies and PackDetectorKind (grimble-model/src/model.rs:30-37) is only Callee/None/Impossible. So unsafe blocks, extern "C" / #[no_mangle] FFI, `import ctypes`, eval/exec/compile, pickle.loads, macros such as println!, and argument-shaped uses (subprocess with shell=True) cannot be atoms. gob-pattern already has a structural matcher and grammar-level patterns; let a pack detector row be a GRL pattern or a U query (packs.md 2 kind = query) and an import row.

no-story: internal engineering task in grimble-bind; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
