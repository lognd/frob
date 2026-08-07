## Done report

ref_gate's reference tokenizer (_candidate_tokens) now recognizes BACKTICK-
wrapped path mentions (new _BACKTICK_RE), so a `` `docs/rework.md` `` in
docs/index.md counts as a real inbound reference. Deliberately restricted to
PATH-shaped content (must contain `/`), so a bare-basename backtick prose
mention (`` `manifest.yaml` ``) does NOT count -- guarded by two pre-existing
regression tests that still pass. This cleared the ~12 legit-linked .md docs
that were false-positive REF001 orphans.

REF001 before/after: 12 -> 0 (verified). Evidence (2 tests):
backtick-wrapped-path-counts-as-reference,
backtick-wrapped-bare-identifier-not-treated-as-reference. Landed with T-0466
in one worktree; coordinator inline-reviewed, landed via 3-way.
