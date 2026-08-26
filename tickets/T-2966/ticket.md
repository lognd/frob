---
id: T-2966
title: 'frob-dup: finish src/frob/gates cluster triage (23 residue groups)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
scope_breadth_ack: true
scope_breadth_ack_reason: genuine epic-scale triage across ~20 groups spanning most
  of src/frob/gates; package glob is the honest scope
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the 23 residue groups this ticket's body lists, when triaged and dispositioned
    (extracted / waived with reason / narrowed), then re-measuring src/frob/gates
    frob-dup unaccounted groups shows 0 (or a further-decomposed residue with counts)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Residue from T-2956's triage: 23 of the 27 unaccounted src/frob/gates
frob-dup groups still need a disposition applied (decision only
sketched here from spot-checks, not all individually verified).

Two confirmed dispositions from T-2956's spot-checks, to guide this
ticket:

1. EXTRACT (genuine, low-risk): `_tracked_gate_files` in
   src/frob/gates/_port_selfcheck.py:212 and
   src/frob/gates/_lexical_selfcheck.py:270 are BYTE-IDENTICAL bodies
   (only the `log_prefix=` string differs) that compose the SAME two
   already-shared helpers (`tracked_python_files_for_gate`,
   `is_detector_package_file`) -- the two files' own docstrings
   explicitly say this composition is "expected to reuse rather than
   re-hardcode." Extract to a single `tracked_gate_files(root,
   log_prefix)` helper (natural home: _detector_scope.py, alongside
   `is_detector_package_file`) and update both call sites. This is the
   34-line group at _port_selfcheck.py:213 / _lexical_selfcheck.py:271.

2. WAIVE (confirmed in-code, not just inferred): the 11-line group at
   _exhaustive_handling.py:141 / arch/_mayraise.py:265 /
   arch/_exceptions.py:76 / dup/_rules.py:36, and its sibling the
   10-line group at _exhaustive_handling.py:197 /
   arch/_mayraise.py:340 -- _exhaustive_handling.py's own docstring on
   `_nearest_preceding_catch` says explicitly this is "a narrow local
   duplicate of frob.arch._mayraise._nearest_preceding_catch ... not
   importing a private name across modules, is the intended shape
   here."

Remaining ~19 groups follow the same "sibling rule-builder/violation-
builder idiom" shape seen repeatedly across src/frob/gates (each
rule's `_unresolved`/`_violation` builder pair looks structurally
alike -- docstring, Violation(...) call, f-string message -- while
encoding a different rule code and different domain content) -- likely
mostly WAIVE, but each needs the same code-level verification T-2956
gave the schema family and the two groups above before waiving, not a
blanket assumption. Includes: _pii_structural/_python_fields.py vs
_keywords.py (48-line, PII010 -- check whether these two ARE the same
gate's shared logic before waiving, this one is less clear-cut than
the others); _port_selfcheck.py internal (39-line, 25-line);
_port_selfcheck.py vs _pii_structural/_crosslang.py (39-line, shared
fragment); __init__.py internal (33-line, REL001 land-note family,
docstring already states "mirrors ... shape/message convention
exactly"); _docstatus.py internal (31-line, DOC010/DOC011 builders);
_waive.py vs lang/_common.py (30-line); _docptr.py internal + __init__
(27-line); _dup_graph_schema.py internal x2 (25-line, 22-line) +
__init__ (25-line); _root_asset_dirs.py vs _port_selfcheck.py
(25-line); the 22-line 9-file cross-package block (doctor.py,
_bug_repro.py, _mutation_evidence.py, strata/_waive.py,
deploy/_generate.py, scaffold/_managed.py, dup/_rules.py,
app/ticket_runner/_close_cmd.py -- spot-checked two of these,
doctor.py's `_global_binary_skew_remediation` and
_close_cmd.py's `_hint_missing_evidence`: coincidental structural
resemblance only, remediation-hint functions in 8 unrelated
subsystems, no shared domain -- likely WAIVE but verify the rest
before waiving all 9); _coverage.py vs _baseline.py (20-line);
_deprecated_baseline.py cross-package (17-line); _doclink_docanchor.py
internal + vet/_scan* (16-line, 9-line); _walk_lint.py/_render_lint.py
+ pii_structural/_env_access.py (15-line); _inv.py internal (12-line);
_registry_exhaustiveness.py internal (10-line); _docptr.py vs
_fix_engine.py (8-line); _docblocks_shared.py vs perf/_redundancy.py
vs perf/_sketch_store.py (6-line).

Re-measure via: uv run frob check --json --only static, filter
tool=="frob-dup", filter messages containing "src/frob/gates" and not
already "[waived".

Apply DUP001 frob:waive directives (full-fragment coverage required --
see frob.check._python._dup_group_covering_waivers) for the WAIVE
dispositions, do the extraction for the confirmed EXTRACT case, and
leave a follow-up for anything spot-checking turns up as its own
genuine extract candidate.
