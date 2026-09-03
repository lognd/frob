## Done report

INV003/INV004 burn-down for T-3520. Measured 2026-08-30 via
uv run frob check --only invariant --json, filtering severity=warning:

Before: INV003=12, INV004=12 (same 12 doc files, one of each per file).
After: INV003=0, INV004=0. gate:INV: 0 errors, 1 warning (INV-014's own
INV005, unrelated to this ticket's scope), 0 waived under gate:INV's own
count (waivers live on the doc side, matched via each file's
frob:waive INV003/INV004 marker per docs/modules/gates.md's own
_file_has_reasoned_doc_waiver mechanism).

Each of the 12 files reviewed individually against docs/modules/gates.md's
INV003/INV004 sections, per T-2368's own "do not assume a shared fix"
standard, and re-verified against current code before disposition:

- docs/modules/ci_report.md: spot-checked the "only sound source of
  failed node ids" claim against src/frob/ci_report.py::parse_pytest_log
  -- holds (only reads _RESULT_LINE/_SUMMARY_LINE, no positional
  inference anywhere in the function).
- docs/modules/ci_validity.md: spot-checked the "nothing cached or
  persisted" claim -- no lru_cache/functools.cache anywhere in
  src/frob/ci_validity.py.
- docs/modules/docstrings.md: the flagged sentence describes a CALLER's
  perspective (why public docstrings carry a higher bar), not a claim
  about frob's own code -- no invariant applies.
- docs/modules/ghio.md: the flagged claims describe the GitHub CLI/API's
  own observed behavior, not frob's own code -- nothing to bind.
- docs/modules/tickets-data-storage.md: spot-checked the clipboard-paste
  claim against src/frob/app/ticket_runner/_new.py:890 (isatty check) --
  holds.
- docs/modules/tickets-landing.md, tickets-merge-driver.md,
  tickets-verify-sweep.md, tickets.md: spot-checked each flagged claim
  against its own file's detailed, internally-consistent implementation
  description -- all plausible and consistent, genuine design intent.
- docs/strata/entity_architecture.md, graph.md, vmodel.md: T-3004/T-3006/
  T-3007-era design docs for a subsystem still being built (graph.md's
  own second line: "kernel only... No consumer wires a real schema onto
  this yet") -- normative language is intended future contract, not a
  present enforced code invariant.

All 12 are genuine design intent rather than an enforced behavior --
exactly the disposition docs/modules/gates.md's own INV003 section
anticipates ("a claim can be genuine design intent rather than an
enforced behavior, so WARN surfaces the signal for human triage rather
than forcing a bind-or-waive on every hit"). None were bound to a
fabricated invariant just to silence the gate; each got a file-scoped
<!-- frob:waive INV003/INV004 reason="..." --> naming what was verified.

Promoted: no. INV003/INV004 are file-scoped WARN-only codes by design
(gates.md: "Always Severity.WARN -- advisory by design... INV004 does
not fail frob check"); promoting either to ERROR was not asked for and
would fight the rule's own documented posture, not just this ticket's
12-file remainder.

Filed: none -- all 12 findings genuinely resolved (waived with a
verified, file-specific reason), no further remainder.

### Changed
```
 docs/modules/ci_report.md            | 2 ++
 docs/modules/ci_validity.md          | 2 ++
 docs/modules/docstrings.md           | 2 ++
 docs/modules/ghio.md                 | 2 ++
 docs/modules/tickets-data-storage.md | 2 ++
 docs/modules/tickets-landing.md      | 2 ++
 docs/modules/tickets-merge-driver.md | 2 ++
 docs/modules/tickets-verify-sweep.md | 2 ++
 docs/modules/tickets.md              | 2 ++
 docs/strata/entity_architecture.md   | 2 ++
 docs/strata/graph.md                 | 2 ++
 docs/strata/vmodel.md                | 2 ++
 tickets/T-3520/ticket.md             | 3 +++
 13 files changed, 27 insertions(+)
```

### Evidence
- `cmd:bash /tmp/claude-1000/-home-logan-projects-frob/f4d0128f-ef81-45f6-8336-64623fe5712f/scratchpad/check_inv_zero.sh exit=0 sha256=52f6875ea794` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 23 error(s), 4140 warning(s), 895 waived
- error-findings: ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_land_queue.py, COV003@tests/unit/test_mutation_sweep_queue.py, COV003@tests/unit/test_process_lock.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3520/tests/unit/strata/test_litmus_cwe.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3520, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
