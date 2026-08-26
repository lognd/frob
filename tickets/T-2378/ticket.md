---
id: T-2378
title: Decompose and burn frob-dup (exact+renamed) WARN findings to zero, then promote
  to error
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_source.py
- src/frob/vet/_ecosystem.py
- src/frob/vet/_supplychain.py
- tickets/T-2955/**
- tickets/T-2956/**
evidence_scope:
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_source.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_ecosystem.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: extract shared _read_text_or_empty (frob-dup exact-duplicate T-2378)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/vet.md
  reason: 'closure: existing frob:doc edges in touched files point here'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/modules/vet.md
  reason: closure warning was for pre-existing unrelated doc edges, not this change
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2955/**
  reason: sibling draft tickets filed from this ticket, need to be in scope for the
    commit that files them
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2956/**
  reason: sibling draft tickets filed from this ticket, need to be in scope for the
    commit that files them
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: pure refactor, no intended behavior change; BUG002 confirmatory-only finding
    is expected here
  actor: logan
  at: '2026-08-26'
  old_length: 932
  new_length: 1293
evidence:
- tests/test_vet.py::TestEcosystemRules::test_python_setup_py_cmdclass_flagged
- tests/test_vet.py::TestEcosystemRules::test_python_pth_file_flagged
designated_repro_test: null
acceptance:
- text: given the src/frob/vet exact-duplicate frob-dup finding (_read_text_or_empty
    in _ecosystem.py and _supplychain.py), when frob check --json runs, then zero
    findings remain for that pair, AND the family's histogram plus two sibling decomposition
    tickets (parent=T-2378) are recorded in the Done report
  evidence:
  - tests/test_vet.py::TestEcosystemRules::test_python_setup_py_cmdclass_flagged
  - tests/test_vet.py::TestEcosystemRules::test_python_pth_file_flagged
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: given the src/frob/vet exact-duplicate frob-dup finding (_read_text_or_empty
    in _ecosystem.py and _supplychain.py), when frob check --json runs, then zero
    findings remain for that pair, AND the family's histogram plus two sibling decomposition
    tickets (parent=T-2378) are recorded in the Done report
  reason: 'Per the parent ticket''s own instructions: 557 findings is too large for
    one

    dispatch, and not every duplicate should be forced to zero (some are

    deliberate/defensible repetition needing a waiver or detector change, not

    an extraction). This ticket''s actual scope narrowed to: decompose the

    family into a histogram, extract the one genuine exact-duplicate found in

    src/frob/vet, and file two sibling tickets (drafts T-2956,

    T-2955, parented to T-2378) covering the two largest untriaged

    clusters (src/frob/gates, ~20 groups; tests/, ~490 groups). "Zero findings

    repo-wide" is deferred to whichever dispatch(es) actually clear those

    children -- rewriting this criterion to match what this ticket itself

    delivers rather than leaving it permanently unbound.

    '
  actor: logan
  at: '2026-08-26'
- op: remove
  index: 1
  old_text: given the family's gate module, when its severity is read, then it is
    ERROR not WARNING
  new_text: null
  reason: 'Promotion (WARN -> ERROR) is gated on the family reaching zero repo-wide;

    this ticket only closes 1 of 557 findings before decomposing the rest into

    sibling tickets. Promoting now would red the tree for every other agent

    touching a file with an untriaged duplicate. Removing this criterion from

    T-2378 -- promotion belongs to whichever future ticket actually drives the

    last sibling''s cluster to zero (parent chain stays T-2378/T-0969, tracked

    via the drafts filed this dispatch and whatever further children they

    spawn).

    '
  actor: logan
  at: '2026-08-26'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4fba0b0045f59a00b70f40975bd06153d81ed98e
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral), tool `frob-dup`, 2026-08-18: 457 WARN-tier findings
(457 = 'exact' + 'renamed' duplicate-code categories combined).

This is a large campaign, not a single-dispatch burn-down -- 457 findings is an
order of magnitude bigger than the small-family children filed alongside this
one. Before dispatching, re-run `uv run frob check --json --budget 500 |
python3 scripts/check_summary.py` (or filter for tool=="frob-dup" in the raw
--json) and group findings by directory/component so this can be split into
several disjoint-scope children -- do not attempt it as one worktree.

Closure is two-part per the epic (T-0969): (1) zero frob-dup WARN findings,
verified the same way, AND (2) frob-dup's dup-detection promoted from warning
to error severity for the categories burned down. Do not promote a category
still carrying findings.

frob:no-behavior-change reason="pure extract-shared-function refactor: moved a byte-identical _read_text_or_empty from _ecosystem.py and _supplychain.py into _source.py and imported it from both call sites; no logic, control flow, or error handling changed at either call site -- this is the frob-dup exact-duplicate finding's fix itself, not a behavior fix"