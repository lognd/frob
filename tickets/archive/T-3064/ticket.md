---
id: T-3064
title: 'Break the 182-node import cycle: extract universal value types out of gates._models
  into a leaf module'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
blocked_by:
- T-3066
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- src/frob/findings.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/vet_runner.py
- src/frob/dup/_rules.py
- src/frob/fuzz/_models.py
- src/frob/fuzz/_rules.py
- src/frob/perf/_advisories.py
- src/frob/perf/_dup_spawn.py
- src/frob/perf/_hotpath_smells.py
- src/frob/perf/_loop_effects.py
- src/frob/perf/_ratchet.py
- src/frob/perf/_recursion.py
- src/frob/perf/_redundancy.py
- src/frob/perf/_rules.py
- src/frob/policy/__init__.py
- src/frob/telemetry/__init__.py
- src/frob/testing/_coverage_cache.py
- src/frob/vet/_ecosystem.py
- src/frob/vet/_models.py
- src/frob/vet/_scan.py
- src/frob/vet/_scan_violations.py
- src/frob/vet/_supplychain.py
- design/frob.strata
evidence_scope:
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/findings.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/vet_runner.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/dup/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/fuzz/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/fuzz/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_advisories.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_dup_spawn.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_hotpath_smells.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_loop_effects.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_ratchet.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_recursion.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_redundancy.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/policy/__init__.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/telemetry/__init__.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/testing/_coverage_cache.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_ecosystem.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_scan.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_scan_violations.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: design/frob.strata
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/findings.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/vet_runner.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/dup/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/fuzz/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/fuzz/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_advisories.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_dup_spawn.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_hotpath_smells.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_loop_effects.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_ratchet.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_recursion.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_redundancy.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/perf/_rules.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/policy/__init__.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/telemetry/__init__.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/testing/_coverage_cache.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_ecosystem.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_models.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_scan.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_scan_violations.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
- op: add
  glob: design/frob.strata
  reason: T-3064 extract universal value types from gates._models into leaf module;
    excludes _land_cmd.py held by T-3061 live lease
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: 'T-3087 acceptance: disposition note for the falsely-closed ticket that
    motivated the reopen verb'
  actor: logan
  at: '2026-08-27'
  old_length: 4459
  new_length: 4945
evidence:
- tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9d78e63b561f6ba3e7c9b56b46ee1ed9bbf792ab
---
MEASURED 2026-08-26 via `frob cycle`: a single strongly-connected component of
**182 nodes** spanning `tickets/`, `gates/`, `strata/`, `app/`, `serve/`,
`verify/`, `deploy/`, `release/`, `refactor/`, `testing/`, `registry/`, `vet/`
and `__main__.py`. That is effectively the whole codebase in one SCC. (Nine
small 1-3 node cycles also exist and are separate, minor, and not this ticket.)

GOOD NEWS FIRST: wrong-direction MODULE-LEVEL imports are rare. A search for
`from frob.app` / `import frob.app` inside `src/frob/gates/` returns exactly ONE
hit, and it is function-local (`_flag_coverage.py:261`), so it does not create an
import-time edge at all. This is not a mess of casual bad imports -- it is a
small number of load-bearing edges welding everything together.

THE CUT I RECOMMEND: `src/frob/gates/_models.py`.

    352 lines, 98 importers across 9 packages:
      gates 77 | perf 8 | vet 5 | app 3 | testing 1 | telemetry 1
      policy 1 | fuzz 1 | dup 1

It contains TWO DIFFERENT KINDS OF THING:

  UNIVERSAL VALUE TYPES -- `Severity`, `Violation`, `WaiverRef`, `DebtEntry`
  (and arguably `DeprecatedEntry`). A finding has a severity and a location.
  `vet`, `perf`, `dup`, `fuzz` and `policy` all need these and have nothing to
  do with gate machinery.

  GATE MACHINERY -- `GateStats`, `GateReport`, `GateConfig`, `PreworkSweep`,
  `SystemSpec`. These genuinely belong to gates.

TWENTY-ONE importers OUTSIDE `gates` reach into the gates package to obtain a
value type. That is what forces layer-3 analysis code (`vet`, `strata`, `perf`,
`dup`) to depend on layer-4 checking code, and it is a principal weld in the SCC.

Representative edges:
    src/frob/vet/_ecosystem.py:18  from frob.gates._models import Severity, Violation
    src/frob/vet/_models.py:20     from frob.gates._models import Violation
    src/frob/vet/_scan.py:19       from frob.gates._models import Severity, Violation

THE CHANGE: extract the universal value types into a LEAF module (`frob.findings`
or `frob.diagnostics` -- name it deliberately) that imports nothing from frob
except primitives. `gates/_models.py` keeps the gate machinery and imports the
leaf. Every other package imports the leaf directly and stops depending on
`gates`.

WHY THIS EDGE RATHER THAN ANOTHER:
  - It is MECHANICAL. No behaviour change, no semantic judgement -- four types
    relocate.
  - The tooling for it landed today. `frob refactor move` / `move-module`
    (T-2990) has typed operands, symbolic (never lexical) rewriting, and handles
    the non-Python reference surface: `.strata` `code=` globs, ticket `scope`
    globs, `frob:doc`/`frob:tests` path citations. USE IT rather than hand-editing
    imports -- that is the owner's standing instruction and this is a good real
    exercise of the new verb.
  - It is MEASURABLE: re-run `frob cycle` afterwards and the SCC either drops
    substantially or it does not.
  - It is REVERTIBLE: one extraction, one land.

METHOD -- ONE CUT, THEN RE-MEASURE. Do NOT attempt to plan the whole
decomposition from the 182-node list. The SCC certainly has several independent
chords; two other candidates already visible are
`strata/_effects.py -> gates/_waive.py` and
`gates/_tickets_gate.py -> tickets/_draft_finalize.py`. Make THIS cut, re-run
`frob cycle`, and let the new output name the next cut. File that next cut as a
sibling ticket rather than doing it here.

HONEST EXPECTATION: this will probably not take 182 to zero. It should
substantially reduce it, and it will make the remaining structure legible.
Report the before and after node counts either way -- a smaller-than-hoped
reduction is a useful measurement, not a failure.

DO NOT chase `gates/_flag_coverage.py:261`'s function-local `frob.app` import as
part of this. A deferred import inside a function body does not create an
import-time cycle, so fixing it would feel productive and change nothing
measurable.

ACCEPTANCE
- The universal value types live in a leaf module importing nothing from frob
  but primitives; `gates/_models.py` imports it and keeps the gate machinery.
- The 21 non-gates importers import the leaf, not `frob.gates._models`.
- The extraction was performed with `frob refactor`, not hand-edited imports --
  state the exact command in the Done report.
- `frob cycle` SCC node count reported before and after.
- No behaviour change: existing tests pass unchanged.
- The next cut is filed as a sibling ticket, named from the re-measured cycle.

## Reopen log

- 2026-08-27: Left CLOSED (not reopened) per T-3087's disposition. T-3086 ("Break the 182-node import cycle (redo)") already exists, queued, and re-declares the same scope this ticket was meant to touch. Reopening this ticket now would create two active tickets racing the same scope/lease -- worse than leaving it closed with this note. See T-3086 for the real work; see T-3087 for the close-time blocked_by guard and `frob ticket reopen` verb this incident motivated.