+++
id = "01M3ZX7VDVTM9DJCW5228YRZ8Z"
title = "trust prompt: TTY only, host-derived facts, no --yes"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-03T03:34:34Z"
idempotency_key = "m2-sec-trust-prompt"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/prompt.rs", "crates/frob/src/trust_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7V0XP3BYTWDHXN20Z79R"

[[acceptance]]
text = "Given a non-TTY stdin, when `trust` runs, then it exits 3 and prints nothing a script could confirm; `--yes` is an unknown flag"
bound = false

[[acceptance]]
text = "Given a pack widening an effect, when the prompt renders, then the widening is shown first and in full and pack-supplied prose does not appear"
bound = false
+++

Implements security.md section 2.3 (the prompt).

Refuses unless stdin and stdout are a TTY (exit 3); no --yes and no --all; JSON remedy for untrusted carries requires_human=true; shows only host-derived facts (tree digest, effects with delta, binary sizes, on-protected-branch, reproduced, signed, last git author); widening an effect or trusting subprocess needs typing the pack name.
