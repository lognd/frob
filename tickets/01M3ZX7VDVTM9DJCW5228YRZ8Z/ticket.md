+++
id = "01M3ZX7VDVTM9DJCW5228YRZ8Z"
title = "trust prompt: TTY only, host-derived facts, no --yes"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-19T07:49:16Z"
idempotency_key = "m2-sec-trust-prompt"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/prompt.rs", "crates/frob/src/trust_cmd.rs", "crates/gob-trust/src/lib.rs", "crates/gob-trust/tests/prompt.rs", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/frob/tests/trust_cmd.rs", "docs/design/security.md", "changelog.d/01M3ZX7VDVTM9DJCW5228YRZ8Z.added.md", "crates/frob/tests/it/trust.rs", "crates/frob/tests/it/main.rs", "crates/frob/Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7V0XP3BYTWDHXN20Z79R"

[[acceptance]]
text = "Given a non-TTY stdin, when `trust` runs, then it exits 3 and prints nothing a script could confirm; `--yes` is an unknown flag"
bound = true

[[acceptance]]
text = "Given a pack widening an effect, when the prompt renders, then the widening is shown first and in full and pack-supplied prose does not appear"
bound = false
+++

Implements security.md section 2.3 (the prompt).

Refuses unless stdin and stdout are a TTY (exit 3); no --yes and no --all; JSON remedy for untrusted carries requires_human=true; shows only host-derived facts (tree digest, effects with delta, binary sizes, on-protected-branch, reproduced, signed, last git author); widening an effect or trusting subprocess needs typing the pack name.
