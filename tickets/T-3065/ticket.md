---
id: T-3065
title: Quarantine finding identities are keyed by literal string equality on a path
  whose shape varies by caller; normalize at write time
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_quarantine.py
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- tests/unit/verify/test_quarantine.py
- tests/unit/verify/test_verify_runner.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/_cli_parsers/_verify.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc closure for touched public symbols
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc anchor collapses whole shared module doc; out of scope for this bugfix
  actor: logan
  at: '2026-08-26'
- op: add
  glob: frob.lock
  reason: frob ack writes digest acknowledgements to frob.lock for the two symbols
    this ticket touches
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: frob.lock
  reason: PRE001 scope-digest instability with frob.lock in scope; frob.lock changes
    from frob ack are not code-graph-tracked content anyway
  actor: logan
  at: '2026-08-27'
- op: add
  glob: frob.lock
  reason: restore scope for the frob ack write
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: author plan + fresh field evidence widening scope
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 4800
evidence:
- tests/unit/verify/test_verify_runner.py::TestDispose::test_dismiss_with_relative_path_matches_a_finding_stored_absolute
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_absolute_and_relative_resolve_identical
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_empty_file_passes_through
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_unresolvable_path_falls_back_verbatim
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_normalizes_an_absolute_file_to_root_relative_at_write_time
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_already_relative_file_is_left_as_is
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f451ba87465f520d70cb08a2e31477b98d6c0607
---
## Description

Quarantine finding identity (`(rule_id, file, line)`) is compared by
literal string equality on `file`. The stored `file` reflects whatever
shape the ORIGINAL caller happened to pass to `raise_quarantine`
(absolute or relative), while a human addressing it via
`frob verify dispose --dismiss RULE:FILE:LINE=REASON` naturally writes
the path in whatever shape is convenient (usually relative, since that
is what `frob check`/ruff/etc print). A shape mismatch fails identically
to a genuinely wrong key -- this is the same absolute-vs-relative
identity-matching defect class that separately voided 116 `frob:waive`
directives (see repo memory: path-shape-mismatch-silently-voids-...).

`_path_shape_hint` (T-2312) already diagnoses this case AFTER the fact
(logs a hint pointing at the shape mismatch), but the underlying
identity is still never normalized -- the fix belongs at write time (and
symmetrically at dispose-lookup time), not as a better error message
after the fact.

## 2026-08-26 field evidence (widens this ticket)

Hit today, working an unrelated task, all three below on the SAME
finding:

(a) A finding recorded with an ABSOLUTE path
    (`/home/logan/projects/frob/src/frob/narrative/_cli.py`) could not be
    addressed by a `--dismiss RULE:FILE:LINE=REASON` written with the
    relative shape. This is the ticket's own defect, confirmed live.

(b) The SAME finding's `line` was `None` (an E501 finding with no
    resolvable line). A finding with a real `rule_id`/`file` but
    `line=None` IS addressable through the existing `RULE:FILE=REASON`
    (2-part, no trailing `:LINE`) grammar -- `_parse_finding_arg` already
    leaves `line=None` in that case, so this is NOT a second grammar gap
    on its own. It compounds with (a) though: normalizing `file` alone
    is necessary but callers must still know to omit `:LINE` (or write
    `RULE:FILE:=REASON`) for a `None`-line finding, and a rule that
    legitimately fires more than once on the same file with no resolvable
    line would collide under this identity (two `None`-line findings for
    the same `(rule_id, file)` are indistinguishable). No incident of
    that specific collision was observed; recorded here as a known
    residual limitation of the `(rule_id, file, line)` identity shape,
    not fixed by this ticket.

(c) SEPARATE, ARGUABLY WORSE: `.frob/quarantine.json` PERSISTS ON DISK
    after quarantine is cleared (by design -- `clear_quarantine`'s own
    docstring: a cleared record is kept as the audit trail, never
    deleted). Reading the raw file is therefore NOT a read of "is
    quarantine raised" -- a stale cleared record is byte-identical in
    shape to a live one and only `is_quarantined`/`frob verify status`
    (which check `cleared_at is None`) distinguish them. Investigated as
    part of this ticket and NOT fixed here: dozens of existing tests
    (`tests/unit/test_rapid_sweep.py`, `tests/unit/verify/
    test_verify_runner.py`) assert `load_quarantine` returns the cleared
    record (with `cleared_at`/`cleared_reason`/`cleared_by` populated)
    immediately after `clear_quarantine` -- i.e. "the file keeps existing
    and stays readable after clear" is itself a tested contract multiple
    call sites depend on. Making the file's bare existence truthful
    (e.g. delete `.frob/quarantine.json` on clear and move the record to
    a separate history file) is a real fix but touches that whole
    surface -- not a small change riding on this bugfix. Filed as a
    sibling ticket instead of left silently undone (see Done report).

## Plan

1. Add `normalize_finding_path(root, file) -> str` to
   `frob.verify._quarantine` -- the single normalization both write
   (`raise_quarantine`) and dispose-lookup (`verify_runner`
   `_collect_dispositions`/`_retire_unidentifiable_dispose`) paths run
   through, so identity comparison is symbolic (resolved filesystem
   path, relative-to-root POSIX form) rather than a literal string
   match. Falls back to the input verbatim when it cannot be resolved.
2. Normalize every finding's `file` in `raise_quarantine` before the
   existing identity-less/trivial filters run and before persisting.
3. Normalize the `file` component parsed out of `--file-ticket`/
   `--dismiss`/CLI dispose keys against the same function before
   building the `dispositions` dict, so a caller-given absolute path
   matches a stored relative one (or vice versa) directly, with no hint
   needed.
4. Regression test (BUG002, fails at parent commit): a finding raised
   with an absolute `file` is dispose-able via a relative
   `--dismiss`/`--file-ticket` key, and vice versa.
5. Keep `_path_shape_hint` as a defense-in-depth diagnostic for legacy
   on-disk records written before this fix (never renormalized
   retroactively).