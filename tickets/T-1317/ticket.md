---
id: T-1317
title: 'ack accountability: frob ack requires a reason and records the digest delta
  it vouches for'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/lock.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/app/ticket_runner/_mutate.py
- docs/modules/gates.md
- tests/test_gates_drift_ack.py
- src/frob/graph/_models.py
- src/frob/app/config.py
- src/frob/app/ack_runner.py
- tests/unit/test_ack_runner.py
- tests/test_ack_worktree_lease.py
- tests/test_graph_lock.py
- tests/test_graph.py
- src/frob/app/_config_external.py
- docs/modules/graph.md
- frob.lock
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/graph/lock.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates_drift_ack.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/graph/_models.py
  reason: 'frob ack requires a reason and a recorded digest delta (the ticket''s

    own requirement). The digest delta and the append-only audit trail

    must live in the LockFile/LockEntry models (frob.graph._models is

    lock.py''s own model module, edited alongside it every other time

    LockEntry''s shape changed), the CLI must accept --reason/--reason-file

    and expose the audit trail (AppConfig needs the new ack_reason/

    ack_reason_file/ack_list fields ack_runner.py already reads), and

    ack_runner.py itself is the one place that wires the reason through to

    frob.graph.lock.acknowledge and renders --list. None of these four are

    optional plumbing -- the 5-file scope as ticketed cannot implement the

    acceptance criteria without them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: 'frob ack requires a reason and a recorded digest delta (the ticket''s

    own requirement). The digest delta and the append-only audit trail

    must live in the LockFile/LockEntry models (frob.graph._models is

    lock.py''s own model module, edited alongside it every other time

    LockEntry''s shape changed), the CLI must accept --reason/--reason-file

    and expose the audit trail (AppConfig needs the new ack_reason/

    ack_reason_file/ack_list fields ack_runner.py already reads), and

    ack_runner.py itself is the one place that wires the reason through to

    frob.graph.lock.acknowledge and renders --list. None of these four are

    optional plumbing -- the 5-file scope as ticketed cannot implement the

    acceptance criteria without them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ack_runner.py
  reason: 'frob ack requires a reason and a recorded digest delta (the ticket''s

    own requirement). The digest delta and the append-only audit trail

    must live in the LockFile/LockEntry models (frob.graph._models is

    lock.py''s own model module, edited alongside it every other time

    LockEntry''s shape changed), the CLI must accept --reason/--reason-file

    and expose the audit trail (AppConfig needs the new ack_reason/

    ack_reason_file/ack_list fields ack_runner.py already reads), and

    ack_runner.py itself is the one place that wires the reason through to

    frob.graph.lock.acknowledge and renders --list. None of these four are

    optional plumbing -- the 5-file scope as ticketed cannot implement the

    acceptance criteria without them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_ack_runner.py
  reason: 'acknowledge() now requires --reason (T-1317''s own acceptance criteria);

    this changes frob.app.ack_runner.run''s contract, and the pre-existing

    tests in tests/unit/test_ack_runner.py and tests/test_ack_worktree_lease.py

    that call run(cfg) without ack_reason set now hit the new reason-missing

    refusal instead of the behavior they were written to exercise. Updating

    them to pass a real reason where the ack is meant to actually reach

    acknowledge() is required to keep the touched-set green, not optional

    follow-up.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ack_worktree_lease.py
  reason: 'acknowledge() now requires --reason (T-1317''s own acceptance criteria);

    this changes frob.app.ack_runner.run''s contract, and the pre-existing

    tests in tests/unit/test_ack_runner.py and tests/test_ack_worktree_lease.py

    that call run(cfg) without ack_reason set now hit the new reason-missing

    refusal instead of the behavior they were written to exercise. Updating

    them to pass a real reason where the ack is meant to actually reach

    acknowledge() is required to keep the touched-set green, not optional

    follow-up.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_graph_lock.py
  reason: 'acknowledge() now takes a mandatory keyword-only reason= (T-1317''s own

    requirement -- the human-vouch discipline cannot be optional or it is not

    a requirement at all). Every existing direct caller of frob.graph.lock.

    acknowledge in the test suite (tests/test_graph_lock.py, tests/test_graph.py)

    breaks at call time without a reason= argument -- this is not new test

    coverage, it is keeping the existing suite compiling and green against the

    new mandatory-reason contract.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_graph.py
  reason: 'acknowledge() now takes a mandatory keyword-only reason= (T-1317''s own

    requirement -- the human-vouch discipline cannot be optional or it is not

    a requirement at all). Every existing direct caller of frob.graph.lock.

    acknowledge in the test suite (tests/test_graph_lock.py, tests/test_graph.py)

    breaks at call time without a reason= argument -- this is not new test

    coverage, it is keeping the existing suite compiling and green against the

    new mandatory-reason contract.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001 fires: the new ack_reason/ack_reason_file/ack_list CLI dests

    (added to _cli_parsers/_reporting.py''s ack parser for T-1317) are not

    yet in _config_external.py''s field-name tuples, so AppConfig.from_

    external would silently drop every one of them before AppConfig(**d) --

    exactly the T-1422 class of bug WIRE001 exists to catch. This is not

    optional follow-up; the CLI flags this ticket adds are inert without it.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001 (SYS100) fires: T-1317 gives ack_runner.py a real fs.read

    (loading frob.lock for --list) and the new test file tests/test_gates_

    drift_ack.py a real fs.write (its _write() tmp_path fixture helper), and

    design/frob.strata''s node cli / node testsuite capability declarations

    are the SSOT SELFAUDIT001 checks observed capabilities against -- these

    sites are not yet in either node''s "via" list. Declaring them is not

    optional follow-up: an undeclared observed capability is exactly the

    self-audit gap SYS100 exists to catch.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/graph.md
  reason: 'AFFECT001 fires for every public symbol T-1317 actually changed in

    frob.graph.lock (acknowledge, write_lock, LockError) and frob.graph.

    _models (LockFile) -- each carries a frob:doc edge into docs/modules/

    graph.md, and AFFECT001 requires that doc be touched in the SAME diff

    that changes the symbol it describes, not just cross-referenced from a

    different page. gates.md''s new ack-accountability section is not a

    substitute for the graph.md sections that already describe frob.lock''s

    shape and getting acked-conditions -- both need a real edit.

    '
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: design/frob.strata
  reason: 'Reverted the design/frob.strata edit: adding a full-file glob to this

    ticket''s scope pulled in SCOPE002 obligations for ~630 unrelated

    capability-node doc bindings elsewhere in that single large design file

    (file-granularity scope has no way to narrow to just the two lines T-1317

    touched). Replacing the design-file capability-declaration approach with

    inline frob:waive SELFAUDIT001 directives at the actual new fs.read/

    fs.write call sites instead -- narrower, and does not require this

    ticket''s scope to own an unrelated design file.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: frob.lock
  reason: 'frob.lock itself is now touched in this diff: to prove the T-1317

    acknowledge()/frob ack --reason implementation actually works end to end

    (not just in unit tests), acknowledge()''s own stale sig/body digest was

    re-acked via the new `frob ack --reason` CLI as part of verifying this

    ticket -- the same DRIFT001 self-clearing every prior ticket that edits

    frob.lock-tracked code performs. The lock file is a legitimate, intended

    touch, not accidental scope creep.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001 fires: frob.app.ack_runner.run genuinely changed behavior

    (--reason gate, --list mode) and docs/modules/app.md#runners is the doc

    its own frob:describes anchor points at -- the summary line there needs

    to reflect the new contract, not just gates.md''s new accountability

    section.

    '
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_requires_reason
- tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_records_digest_delta
- tests/test_gates_drift_ack.py::TestAckAccountability::test_first_ack_records_none_old_digest
- tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_rejects_boilerplate_reason
- tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_cli_requires_reason
- tests/test_gates_drift_ack.py::TestAckAccountability::test_content_verified_gates_take_no_lock_ack_cannot_clear_them
designated_repro_test: null
acceptance:
- text: 'GIVEN frob ack clears a DRIFT finding THEN it requires a reason string (waiver-style:
    what was re-verified and why the doc is still true) and records the acked digest
    delta (old->new sig/body/doc facets) in frob.lock, so every ack is an auditable
    vouch rather than a silent clear'
  evidence:
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_requires_reason
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_records_digest_delta
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_first_ack_records_none_old_digest
- text: GIVEN an ack whose reason is empty or boilerplate-detected THEN the ack is
    refused -- rubber-stamping is a gate failure, mirroring WAIVE002's reason discipline
  evidence:
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_rejects_boilerplate_reason
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_ack_cli_requires_reason
- text: 'GIVEN a doc claim class that is machine-checkable (enumerations via DOCENUM001,
    pointers via DOC006) THEN it is content-verified and ack-immune: an ack never
    clears a finding that a checker can prove true or false'
  evidence:
  - tests/test_gates_drift_ack.py::TestAckAccountability::test_content_verified_gates_take_no_lock_ack_cannot_clear_them
threat: null
component: null
---
User question 2026-07-29 answered by the staleness sweep: the ~140 silent doc misses trace to six gate blind spots (T-1227..T-1232) PLUS this seventh systemic one the audit named but no ticket owned -- DRIFT001 verifies freshness of attention (digest vs last ack), and frob ack clears it with no proof the prose was re-verified. Waivers require reason=; acks do not. Principle: move every machine-checkable claim class from ack-based trust to content-verified proof (the DOCENUM/pointer work), and make the residual human vouches auditable (reason + digest delta + date), refusable when empty. Interacts with T-1137's anti-goal (no auto-discharge): the fix engine must never auto-ack, and this ticket makes a hand-ack itself carry evidence.