---
id: T-3514
title: 'frob-dup: triage the src/ renamed-duplicate residue (non-test family)'
state: dropped
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: triage/decision record ticket (mirrors T-2955's pattern)
  -- names candidate files but does not commit to editing them here
scope_changes:
- op: remove
  glob: src/frob/**
  reason: triage/decision record ticket (mirrors T-2955's pattern) -- names candidate
    files but does not commit to editing them here
  actor: logan
  at: '2026-08-30'
triage_changes:
- field: parent
  old_value: null
  new_value: T-0969
  reason: child of the WARN-tier burn-down epic, sibling of T-2378/T-2955/T-2970
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: set
  reason: record the src/ frob-dup triage findings from T-2957 and the detector-scope
    question found while trying to burn the family to zero
  actor: logan
  at: '2026-08-30'
  old_length: 0
  new_length: 4079
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while working T-2957 (frob-dup: burn the family to zero and promote
WARN to ERROR).

Measured (unscoped, uv run frob check --only dup --json, 2026-08-30 against
main): 158 frob-dup diagnostics (135 warning, 23 note/already-waived). The
tests/-only cluster T-2955/T-2970 triaged and narrowed is not the dominant
share any more -- most residue now spans src/frob/** (roughly 85 of the 135
warnings) plus a smaller tests/ tail that survived T-2970's narrowing.

T-2957 spot-checked a representative sample of the src/ residue (gates/
_walk_lint.py Violation-builders, tickets/_land_git_ops.py's already-
factored waive-deletion wrappers, deploy/_generate_windows.py's install/
uninstall PowerShell block pairs, tickets/_store.py's v2 path accessors,
_cli_parsers/_misc.py's per-subcommand argparse registrars) and found the
SAME shape T-2955 found in tests/: functions the R1/R2 renamed-duplicate
detector flags as near-identical because they share a control-flow/AST
shape, but whose CONTENT (rule-specific violation messages, per-verb
argparse help text, install-vs-uninstall command verbs, per-field path
suffixes) is genuinely distinct and load-bearing -- collapsing them into
one parameterized function would trade a named, individually-documented
symbol for a dispatch table, which is a worse readability trade for
marginal duplication savings.

T-2957 DID land one genuine extraction: src/frob/tickets/_setters.py's
`set_priority`/`set_tier`/`set_component` had a byte-identical 4-line
"reason required, else delegate to _set_ticket_field" guard, factored into
a new `_set_reasoned_field` helper. That measurably removed the flagged
20-line code duplicate at _setters.py:217/333 -- but the total frob-dup
count did NOT drop, because the detector's next-largest match in the same
file became the two functions' near-identical DOCSTRING template (both
follow the file's own established "T-2353: reason is now REQUIRED ..."
paragraph). Trimming that paragraph to a cross-reference reduced literal
duplication but the detector still flags a smaller renamed-similar span
between set_priority/set_tier's (docstring pointer + one-line delegate
call) shape. This is a real detector-scope gap worth raising explicitly
(see disposition below), not something further docstring-wordsmithing can
chase to zero without hurting documentation quality.

DISPOSITION (recommended, not implemented here -- real triage/detector
work, following T-2955/T-2970's precedent rather than forcing either a
mechanical mass-extraction or a blanket waive):

1. Per-file/per-cluster triage of the remaining src/ residue (~85
   warnings), same method T-2955 used for tests/: spot-check each
   sub-cluster, extract the genuine shared-logic cases (this ticket found
   one: _setters.py), and record a DETECTOR-NARROWING or
   deliberate-repetition verdict for the rest with real reasoning per
   group, decomposed into further children as needed.

2. A frob-dup detector question raised directly by this ticket's own
   whack-a-mole above: should the renamed-duplicate detector's block
   comparison exclude docstring/comment text (or weight it far below
   code-body tokens) when computing similarity? Two functions with
   different logic but the same file's documentation TEMPLATE (a
   deliberate, repo-wide convention this codebase leans on heavily) get
   flagged as duplicates purely on shared prose shape -- fixing the CODE
   duplication does not fix the finding, it just relocates it to the next-
   largest shared span, which is frequently the docstring. Needs the same
   positive-control discipline T-2970 used (confirm a narrowed/code-only
   comparison still catches a planted real code duplicate) before landing
   any change to the comparison.

3. Only once both (1) and (2) are resolved is the family's WARN->ERROR
   promotion (T-2957's other stated goal) safe to attempt without redding
   main on repeat detector noise.

Re-measure via: uv run frob check --only dup --json (unscoped), filter
tool=="frob-dup", partition by whether every fragment path starts with
"tests/" vs not.

## Failure log
- 2026-08-31 attempt 2: Measured: frob-dup's docstring-inflation is real, but the correct fix requires either a repo-wide RawSymbol.body_tokens semantic change (call-graph/digest/perf consumers all depend on it verbatim) or new dup-local node-at-span infrastructure frob.lang does not expose yet -- infeasible-in-one-pass without a dedicated repo-wide regression pass; see ticket body for the full measurement.

## Drop reason
- 2026-08-31: Infeasible in one pass (measured by series CC): the docstring-inflation lives in R4's near-miss hash over RawSymbol.body_tokens, a repo-wide shared primitive (call-graph, digests, perf checks consume it verbatim); a correct fix needs dup-local node-at-span infrastructure frob.lang does not expose. Refile as a designed campaign when that infrastructure exists.
